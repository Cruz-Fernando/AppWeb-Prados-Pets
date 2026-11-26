"""
Cifras del reporte semanal (PB-20 / RF14).

Todo sale de lo que ya registra el sistema:
  - Ingresos: facturas cobradas en la semana (estado «pagada», por fecha de cobro).
  - Caja: movimientos de la semana. Separa los gastos reales de las anulaciones
    de facturas, que la caja registra como egreso de la categoría FACTURA.
  - Atenciones: consultas «atendida» y peluquerías «Realizada».
  - Inventario: salidas de la semana (rotación) y el estado actual del stock.

Cada bloque hace pocas consultas agrupadas: la base está en Supabase y cada
ida y vuelta cuesta ~150 ms.
"""

from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import F, Sum
from django.utils import timezone

from apps.agendamiento.models import Cita
from apps.clinico.models import AvisoRecordatorio, Hospitalizacion
from apps.directorio.models import Dueno, Mascota
from apps.facturacion import ganancias
from apps.facturacion.models import Factura, ItemFactura, MovimientoCaja
from apps.inventario.models import MovimientoInventario, Producto
from apps.peluqueria.models import CitaPeluqueria

from . import semanas

CERO = Decimal("0")
HORAS = list(range(7, 20))  # franja del mapa de calor: 7 a. m. a 7 p. m.

LINEAS = [
    (ItemFactura.CONSULTA, "Consultas y servicios clínicos", "consulta"),
    (ItemFactura.PELUQUERIA, "Peluquería", "peluqueria"),
    (ItemFactura.PRODUCTO, "Productos", "producto"),
]

TIPOS_CITA = dict(Cita.TIPO_SERVICIO_CHOICES)
SERVICIOS_PELUQUERIA = dict(CitaPeluqueria.SERVICIO_CHOICES)
CATEGORIAS_CAJA = dict(MovimientoCaja.CATEGORIAS)
SALIDAS = ("SALIDA_VENTA", "SALIDA_CLINICA", "SALIDA_PELUQUERIA")


def _porcentaje(parte, total):
    return round(float(parte) * 100 / float(total)) if total else 0


def _variacion(actual, anterior):
    """Cambio porcentual frente a la semana anterior; None si no hay base para comparar."""
    if not anterior:
        return None
    return round((float(actual) - float(anterior)) * 100 / float(anterior))


def _concepto(item):
    """Nombre corto de lo que se cobró, para agrupar «lo que más dinero dejó»."""
    if item["tipo"] == ItemFactura.PELUQUERIA:
        servicio = SERVICIOS_PELUQUERIA.get(item["cita_peluqueria__servicio"])
        return f"Peluquería: {servicio}" if servicio else "Peluquería"
    if item["tipo"] == ItemFactura.PRODUCTO:
        return item["producto__nombre"] or item["descripcion"].split(" · ")[0]
    if item["cita__tipo_servicio"]:
        return TIPOS_CITA.get(item["cita__tipo_servicio"], "Consulta")
    return item["servicio__nombre"] or item["descripcion"].split(" · ")[0]


def _ranking(contador, limite):
    """Lista ordenada de mayor a menor con el porcentaje frente al primero (para las barras)."""
    filas = sorted(contador.items(), key=lambda par: (-par[1], par[0]))[:limite]
    tope = filas[0][1] if filas else 0
    return [{"nombre": n, "valor": v, "ancho": _porcentaje(v, tope)} for n, v in filas]


# ---------------------------------------------------------------------------
# Semana
# ---------------------------------------------------------------------------

def calcular(sabado, ahora=None):
    """Todas las cifras de la semana que termina en `sabado` (domingo a sábado)."""
    ahora = ahora or timezone.now()
    hoy = timezone.localdate(ahora)
    desde, hasta = semanas.domingo_de(sabado), sabado
    inicio, fin = semanas.limites(desde, hasta)
    fechas = semanas.dias_de(sabado)
    dias = {
        f: {"fecha": f, "corto": semanas.DIAS_CORTOS[f.weekday()], "nombre": semanas.DIAS[f.weekday()],
            "ingresos": CERO, "consultas": 0, "peluquerias": 0}
        for f in fechas
    }

    # --- Facturas cobradas -------------------------------------------------
    facturas = list(Factura.objects.filter(estado=Factura.PAGADA, fecha__gte=inicio, fecha__lt=fin)
                    .values("pk", "fecha", "total", "descuento"))
    ingresos = sum((f["total"] for f in facturas), CERO)
    descuentos = sum((f["descuento"] for f in facturas), CERO)
    for f in facturas:
        dias[timezone.localdate(f["fecha"])]["ingresos"] += f["total"]

    items = list(ItemFactura.objects.filter(factura_id__in=[f["pk"] for f in facturas], vigente=True)
                 .values("tipo", "subtotal", "descripcion", "cita__tipo_servicio",
                         "cita_peluqueria__servicio", "producto__nombre", "servicio__nombre"))
    por_tipo = defaultdict(lambda: CERO)
    por_concepto = Counter()
    for item in items:
        por_tipo[item["tipo"]] += item["subtotal"]
        por_concepto[_concepto(item)] += float(item["subtotal"])
    bruto = sum(por_tipo.values(), CERO)
    lineas = [{"clave": clave, "nombre": nombre, "css": css, "monto": por_tipo[clave],
               "porcentaje": _porcentaje(por_tipo[clave], bruto)} for clave, nombre, css in LINEAS]

    # --- Caja --------------------------------------------------------------
    caja = {"ingresos": CERO, "anulaciones": CERO, "gastos": CERO, "por_categoria": defaultdict(lambda: CERO)}
    for m in MovimientoCaja.objects.filter(fecha__range=(desde, hasta)).values("tipo", "categoria", "monto"):
        if m["tipo"] == MovimientoCaja.INGRESO:
            caja["ingresos"] += m["monto"]
        elif m["categoria"] == "FACTURA":
            caja["anulaciones"] += m["monto"]
        else:
            caja["gastos"] += m["monto"]
            caja["por_categoria"][m["categoria"]] += m["monto"]
    caja["salidas"] = caja["anulaciones"] + caja["gastos"]
    caja["balance"] = caja["ingresos"] - caja["salidas"]
    caja["gastos_detalle"] = sorted(
        ({"nombre": CATEGORIAS_CAJA.get(k, k), "monto": v} for k, v in caja["por_categoria"].items()),
        key=lambda g: -g["monto"])
    del caja["por_categoria"]

    # --- Agenda: consultas y peluquería --------------------------------------
    calor = defaultdict(int)
    pedidos = Counter()
    atendidos = set()
    canceladas = por_cerrar = programadas = 0

    for c in Cita.objects.filter(fecha__range=(desde, hasta)).values(
            "fecha", "hora_inicio", "estado", "tipo_servicio", "mascota__id_dueno_id"):
        programadas += 1
        if c["estado"] == "cancelada":
            canceladas += 1
            continue
        pedidos[TIPOS_CITA.get(c["tipo_servicio"], "Otro")] += 1
        if c["hora_inicio"]:
            calor[(c["fecha"], c["hora_inicio"].hour)] += 1
        if c["estado"] == "atendida":
            dias[c["fecha"]]["consultas"] += 1
            atendidos.add(c["mascota__id_dueno_id"])
        elif c["fecha"] < hoy:
            por_cerrar += 1

    for p in CitaPeluqueria.objects.filter(fecha_hora__gte=inicio, fecha_hora__lt=fin).values(
            "fecha_hora", "estado", "servicio", "mascota__id_dueno_id"):
        programadas += 1
        if p["estado"] == "Cancelada":
            canceladas += 1
            continue
        local = timezone.localtime(p["fecha_hora"])
        pedidos[f"Peluquería: {SERVICIOS_PELUQUERIA.get(p['servicio'], 'Otro')}"] += 1
        calor[(local.date(), local.hour)] += 1
        if p["estado"] == "Realizada":
            dias[local.date()]["peluquerias"] += 1
            if p["mascota__id_dueno_id"]:
                atendidos.add(p["mascota__id_dueno_id"])
        elif p["fecha_hora"] < ahora:
            por_cerrar += 1

    for d in dias.values():
        d["atenciones"] = d["consultas"] + d["peluquerias"]
    lista_dias = [dias[f] for f in fechas]
    consultas = sum(d["consultas"] for d in lista_dias)
    peluquerias = sum(d["peluquerias"] for d in lista_dias)

    tope_calor = max(calor.values(), default=0)
    mapa = []
    for f in fechas:
        fila = []
        for h in HORAS:
            n = calor.get((f, h), 0)
            nivel = 0 if not n else min(4, 1 + (n - 1) * 4 // max(tope_calor, 1))
            fila.append({"hora": h, "citas": n, "nivel": nivel})
        mapa.append({"dia": dias[f], "celdas": fila})
    por_hora = Counter()
    for (_, h), n in calor.items():
        por_hora[h] += n
    hora_pico = max(por_hora.items(), key=lambda par: (par[1], -par[0]))[0] if por_hora else None

    resumen_groomers = ganancias.resumen(desde, hasta, ahora=ahora)

    # --- Inventario ----------------------------------------------------------
    salidas = Counter()
    for s in (MovimientoInventario.objects.filter(fecha__gte=inicio, fecha__lt=fin, tipo__in=SALIDAS)
              .values("producto__nombre").annotate(total=Sum("cantidad"))):
        salidas[s["producto__nombre"]] += s["total"]
    merma = (MovimientoInventario.objects.filter(fecha__gte=inicio, fecha__lt=fin, tipo="AJUSTE_MERMA")
             .aggregate(t=Sum("monto_total"))["t"] or CERO)

    activos = Producto.objects.filter(activo=True)
    stock_bajo = list(activos.filter(stock_actual__lte=F("stock_minimo"))
                      .order_by("stock_actual", "nombre").values("nombre", "stock_actual", "stock_minimo")[:12])
    por_vencer = list(activos.filter(stock_actual__gt=0, fecha_vencimiento__range=(hoy, hoy + timedelta(days=30)))
                      .order_by("fecha_vencimiento").values("nombre", "stock_actual", "fecha_vencimiento")[:12])
    vencidos = list(activos.filter(stock_actual__gt=0, fecha_vencimiento__lt=hoy)
                    .order_by("fecha_vencimiento").values("nombre", "stock_actual", "fecha_vencimiento")[:12])

    # --- Clientes y clínica --------------------------------------------------
    duenos_nuevos = Dueno.objects.filter(fecha_registro__range=(desde, hasta)).count()
    mascotas_nuevas = Mascota.objects.filter(fecha_registro__range=(desde, hasta)).count()
    atendidos.discard(None)
    recurrentes = Dueno.objects.filter(pk__in=atendidos, fecha_registro__lt=desde).count() if atendidos else 0
    avisados = AvisoRecordatorio.objects.filter(avisado_en__gte=inicio, avisado_en__lt=fin).count()
    hosp_ingresos = Hospitalizacion.objects.filter(fecha_ingreso__gte=inicio, fecha_ingreso__lt=fin).count()
    hosp_altas = Hospitalizacion.objects.filter(fecha_alta__gte=inicio, fecha_alta__lt=fin).count()

    sig_desde, sig_hasta = hasta + timedelta(days=1), hasta + timedelta(days=7)
    sig_inicio, sig_fin = semanas.limites(sig_desde, sig_hasta)
    agenda_siguiente = (
        Cita.objects.filter(fecha__range=(sig_desde, sig_hasta)).exclude(estado="cancelada").count()
        + CitaPeluqueria.objects.filter(fecha_hora__gte=sig_inicio, fecha_hora__lt=sig_fin)
        .exclude(estado="Cancelada").count()
    )

    tope_ingreso_dia = max((d["ingresos"] for d in lista_dias), default=CERO)
    tope_atencion_dia = max((d["atenciones"] for d in lista_dias), default=0)
    for d in lista_dias:   # anchos relativos para las barras del PDF
        d["ancho_ingresos"] = _porcentaje(d["ingresos"], tope_ingreso_dia)
        d["ancho_atenciones"] = _porcentaje(d["atenciones"], tope_atencion_dia)
    return {
        "sabado": sabado,
        "desde": desde,
        "hasta": hasta,
        "dias": lista_dias,
        "dia_mas_ingresos": max(lista_dias, key=lambda d: d["ingresos"]) if tope_ingreso_dia else None,
        "dia_mas_atenciones": max(lista_dias, key=lambda d: d["atenciones"]) if tope_atencion_dia else None,
        "ingresos": ingresos,
        "facturas": len(facturas),
        "ticket_promedio": (ingresos / len(facturas)).quantize(Decimal("1")) if facturas else CERO,
        "descuentos": descuentos,
        "lineas": lineas,
        "mas_vendido": _ranking(por_concepto, 6),
        "caja": caja,
        "consultas": consultas,
        "peluquerias": peluquerias,
        "atenciones": consultas + peluquerias,
        "programadas": programadas,
        "canceladas": canceladas,
        "tasa_cancelacion": _porcentaje(canceladas, programadas),
        "por_cerrar": por_cerrar,
        "servicios_pedidos": _ranking(pedidos, 8),
        "mapa_calor": mapa,
        "horas": HORAS,
        "hora_pico": hora_pico,
        "hora_pico_texto": semanas.hora_texto(hora_pico) if hora_pico is not None else "",
        "groomers": resumen_groomers,
        "rotacion": _ranking(salidas, 8),
        "merma": merma,
        "stock_bajo": stock_bajo,
        "agotados": sum(1 for p in stock_bajo if p["stock_actual"] == 0),
        "por_vencer": por_vencer,
        "vencidos": vencidos,
        "duenos_nuevos": duenos_nuevos,
        "mascotas_nuevas": mascotas_nuevas,
        "clientes_atendidos": len(atendidos),
        "clientes_recurrentes": recurrentes,
        "recordatorios_avisados": avisados,
        "hosp_ingresos": hosp_ingresos,
        "hosp_altas": hosp_altas,
        "agenda_siguiente": agenda_siguiente,
    }


# ---------------------------------------------------------------------------
# Serie de las últimas semanas (tendencia y pronóstico)
# ---------------------------------------------------------------------------

def serie(sabado, cantidad=8):
    """Ingresos y atenciones de las `cantidad` semanas que terminan en `sabado` (de la más antigua a la última)."""
    sabados = [sabado - timedelta(weeks=i) for i in reversed(range(cantidad))]
    filas = {s: {"sabado": s, "ingresos": CERO, "atenciones": 0} for s in sabados}
    desde = semanas.domingo_de(sabados[0])
    inicio, fin = semanas.limites(desde, sabado)

    for f in Factura.objects.filter(estado=Factura.PAGADA, fecha__gte=inicio, fecha__lt=fin).values("fecha", "total"):
        filas[semanas.sabado_de(timezone.localdate(f["fecha"]))]["ingresos"] += f["total"]
    for fecha in Cita.objects.filter(estado="atendida", fecha__range=(desde, sabado)).values_list("fecha", flat=True):
        filas[semanas.sabado_de(fecha)]["atenciones"] += 1
    for momento in (CitaPeluqueria.objects.filter(estado="Realizada", fecha_hora__gte=inicio, fecha_hora__lt=fin)
                    .values_list("fecha_hora", flat=True)):
        filas[semanas.sabado_de(timezone.localdate(momento))]["atenciones"] += 1
    return [filas[s] for s in sabados]


def variaciones(semana, anterior):
    """Cambios frente a la semana anterior para las tarjetas de resumen."""
    return {
        "ingresos": _variacion(semana["ingresos"], anterior["ingresos"]),
        "atenciones": _variacion(semana["atenciones"], anterior["atenciones"]),
    }
