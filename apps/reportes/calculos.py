"""
Cifras del reporte (PB-20 / RF14) para un periodo: día, semana o mes.

Todo sale de lo que ya registra el sistema:
  - Ingresos: facturas cobradas en el periodo (estado «pagada», por fecha de cobro).
  - Caja: movimientos del periodo. Separa los gastos reales de las anulaciones
    de facturas, que la caja registra como egreso de la categoría FACTURA.
  - Atenciones: consultas «atendida» y peluquerías «Realizada».
  - Inventario: salidas del periodo (rotación) y el estado actual del stock.

El desglose cambia con el periodo: el día se parte por hora (7 a. m. a 7 p. m.),
la semana y el mes por día; el mes trae además un resumen por semana y las
comisiones de cada semana por groomer.

Cada bloque hace pocas consultas agrupadas: la base está en Supabase y cada
ida y vuelta cuesta ~150 ms. Un periodo más largo NO hace más consultas.
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

from . import periodos, semanas
from .periodos import DIA, MES, SEMANA, Periodo, como_periodo

CERO = Decimal("0")
HORAS = list(range(7, 20))  # franja del mapa de calor y del reporte diario: 7 a. m. a 7 p. m.

# Orden de las filas del mapa de calor del mes (date.weekday(): lunes 0 … domingo 6)
DOMINGO_A_SABADO = [6, 0, 1, 2, 3, 4, 5]
DIAS_PLURAL = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábados", "domingos"]

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
    """Cambio porcentual frente al periodo anterior; None si no hay base para comparar."""
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


def hora_corta(h):
    """Eje de las gráficas por hora: 7 → «7a», 12 → «12m», 15 → «3p»."""
    if h == 12:
        return "12m"
    return f"{h - 12}p" if h > 12 else f"{h}a"


# ---------------------------------------------------------------------------
# Desglose del periodo
# ---------------------------------------------------------------------------

def _tramos(periodo):
    """
    Partes en que se desglosa el periodo, en orden: {clave: tramo}.
    Día → una por hora de HORAS (la clave es la hora); semana y mes → una
    por día (la clave es la fecha).
    """
    vacio = {"ingresos": CERO, "consultas": 0, "peluquerias": 0}
    if periodo.tipo == DIA:
        return {h: {"clave": h, "fecha": periodo.desde, "hora": h, "corto": hora_corta(h),
                    "nombre": semanas.hora_texto(h), "rotulo": semanas.hora_texto(h), **vacio} for h in HORAS}
    tramos = {}
    for f in periodo.dias:
        if periodo.tipo == SEMANA:
            corto, nombre = semanas.DIAS_CORTOS[f.weekday()], semanas.DIAS[f.weekday()]
        else:
            corto, nombre = str(f.day), f"{semanas.DIAS[f.weekday()]} {f.day}"
        tramos[f] = {"clave": f, "fecha": f, "hora": None, "corto": corto, "nombre": nombre,
                     "rotulo": f"{semanas.DIAS_CORTOS[f.weekday()]} {f.day}", **vacio}
    return tramos


def _clave_tramo(periodo, fecha, hora):
    """Tramo al que va un movimiento. En el día, lo de antes de las 7 a. m. o después de
    las 7 p. m. se suma a la primera o a la última hora, para que el desglose cuadre con el total."""
    if periodo.tipo == DIA:
        return min(max(hora if hora is not None else HORAS[0], HORAS[0]), HORAS[-1])
    return fecha


def _fila_calor(periodo, fecha):
    """Fila del mapa de calor: la fecha (semana) o el día de la semana (mes: «los lunes»)."""
    return fecha.weekday() if periodo.tipo == MES else fecha


def _indice_semanas(lista_semanas):
    """{fecha: posición de su semana} para repartir movimientos del mes por semana."""
    indice = {}
    for i, s in enumerate(lista_semanas):
        dia = s["desde"]
        while dia <= s["hasta"]:
            indice[dia] = i
            dia += timedelta(days=1)
    return indice


def _comisiones_semanales(resumen, lista_semanas):
    """
    Comisiones de cada groomer en cada semana del mes (el acta pide «comisiones
    semanales»). Sale de las mismas citas de ganancias.resumen(): no consulta la base.
    Solo cuentan los servicios ganados (realizados), igual que en el resumen.
    """
    indice = _indice_semanas(lista_semanas)
    nombres = {(f.groomer.pk if f.groomer else 0): f.nombre for f in resumen.filas}
    filas = {}
    for cita in resumen.citas:
        if cita.estado_cobro != "ganado":
            continue
        i = indice.get(timezone.localdate(cita.fecha_hora))
        if i is None:
            continue
        clave = cita.groomer_id or 0
        fila = filas.setdefault(clave, {
            "nombre": nombres.get(clave, "Sin groomer asignado"),
            "sin_groomer": clave == 0,
            "celdas": [{"comision": CERO, "servicios": 0} for _ in lista_semanas],
            "comision": CERO,
            "servicios": 0,
        })
        fila["celdas"][i]["comision"] += cita.comision_calculada
        fila["celdas"][i]["servicios"] += 1
        fila["comision"] += cita.comision_calculada
        fila["servicios"] += 1
    ordenadas = sorted(filas.values(), key=lambda f: (f["sin_groomer"], -f["comision"], f["nombre"].lower()))
    totales = [sum((f["celdas"][i]["comision"] for f in ordenadas), CERO) for i in range(len(lista_semanas))]
    return {"semanas": lista_semanas, "filas": ordenadas, "totales": totales, "total": sum(totales, CERO)}


# ---------------------------------------------------------------------------
# Periodo
# ---------------------------------------------------------------------------

def calcular(periodo, ahora=None):
    """
    Todas las cifras del periodo. `periodo` es un periodos.Periodo; si llega
    una fecha, es el sábado de una semana (como antes de PB-20).
    """
    periodo = como_periodo(periodo)
    ahora = ahora or timezone.now()
    hoy = timezone.localdate(ahora)
    desde, hasta = periodo.desde, periodo.hasta
    inicio, fin = semanas.limites(desde, hasta)
    tramos = _tramos(periodo)
    lista_semanas = periodo.semanas() if periodo.tipo == MES else []
    indice_semana = _indice_semanas(lista_semanas)

    # --- Facturas cobradas -------------------------------------------------
    facturas = list(Factura.objects.filter(estado=Factura.PAGADA, fecha__gte=inicio, fecha__lt=fin)
                    .values("pk", "fecha", "total", "descuento"))
    ingresos = sum((f["total"] for f in facturas), CERO)
    descuentos = sum((f["descuento"] for f in facturas), CERO)
    for f in facturas:
        local = timezone.localtime(f["fecha"])
        tramos[_clave_tramo(periodo, local.date(), local.hour)]["ingresos"] += f["total"]

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
    caja_semana = [{"ingresos": CERO, "salidas": CERO} for _ in lista_semanas]
    for m in MovimientoCaja.objects.filter(fecha__range=(desde, hasta)).values("tipo", "categoria", "monto", "fecha"):
        if m["tipo"] == MovimientoCaja.INGRESO:
            caja["ingresos"] += m["monto"]
        elif m["categoria"] == "FACTURA":
            caja["anulaciones"] += m["monto"]
        else:
            caja["gastos"] += m["monto"]
            caja["por_categoria"][m["categoria"]] += m["monto"]
        if lista_semanas:
            lado = "ingresos" if m["tipo"] == MovimientoCaja.INGRESO else "salidas"
            caja_semana[indice_semana[m["fecha"]]][lado] += m["monto"]
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
        hora = c["hora_inicio"].hour if c["hora_inicio"] else None
        pedidos[TIPOS_CITA.get(c["tipo_servicio"], "Otro")] += 1
        if hora is not None:
            calor[(_fila_calor(periodo, c["fecha"]), hora)] += 1
        if c["estado"] == "atendida":
            tramos[_clave_tramo(periodo, c["fecha"], hora)]["consultas"] += 1
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
        calor[(_fila_calor(periodo, local.date()), local.hour)] += 1
        if p["estado"] == "Realizada":
            tramos[_clave_tramo(periodo, local.date(), local.hour)]["peluquerias"] += 1
            if p["mascota__id_dueno_id"]:
                atendidos.add(p["mascota__id_dueno_id"])
        elif p["fecha_hora"] < ahora:
            por_cerrar += 1

    desglose = list(tramos.values())
    for t in desglose:
        t["atenciones"] = t["consultas"] + t["peluquerias"]
    consultas = sum(t["consultas"] for t in desglose)
    peluquerias = sum(t["peluquerias"] for t in desglose)

    # Mapa de calor: semana → un renglón por día; mes → uno por día de la
    # semana («los lunes»); día → no hace falta, el desglose ya es por hora.
    if periodo.tipo == SEMANA:
        filas_calor = [(f, tramos[f]) for f in periodo.dias]
    elif periodo.tipo == MES:
        filas_calor = [(d, {"corto": semanas.DIAS_CORTOS[d], "nombre": DIAS_PLURAL[d]}) for d in DOMINGO_A_SABADO]
    else:
        filas_calor = []
    tope_calor = max(calor.values(), default=0)
    mapa = []
    for clave, dia in filas_calor:
        fila = []
        for h in HORAS:
            n = calor.get((clave, h), 0)
            nivel = 0 if not n else min(4, 1 + (n - 1) * 4 // max(tope_calor, 1))
            fila.append({"hora": h, "citas": n, "nivel": nivel})
        mapa.append({"dia": dia, "celdas": fila})
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

    # Lo que ya está agendado para el periodo siguiente (mañana, la próxima semana o el próximo mes)
    siguiente = periodo.siguiente()
    sig_inicio, sig_fin = semanas.limites(siguiente.desde, siguiente.hasta)
    agenda_siguiente = (
        Cita.objects.filter(fecha__range=(siguiente.desde, siguiente.hasta)).exclude(estado="cancelada").count()
        + CitaPeluqueria.objects.filter(fecha_hora__gte=sig_inicio, fecha_hora__lt=sig_fin)
        .exclude(estado="Cancelada").count()
    )

    tope_ingreso = max((t["ingresos"] for t in desglose), default=CERO)
    tope_atencion = max((t["atenciones"] for t in desglose), default=0)
    for t in desglose:   # anchos relativos para las barras del PDF
        t["ancho_ingresos"] = _porcentaje(t["ingresos"], tope_ingreso)
        t["ancho_atenciones"] = _porcentaje(t["atenciones"], tope_atencion)

    # En el día el desglose es por hora: «el día con más…» no aplica.
    por_dias = periodo.tipo != DIA
    cifras = {
        "periodo": periodo,
        "tipo": periodo.tipo,
        "sabado": periodo.sabado,
        "desde": desde,
        "hasta": hasta,
        "desglose": desglose,
        "dias": desglose if por_dias else [],
        "dia_mas_ingresos": max(desglose, key=lambda t: t["ingresos"]) if por_dias and tope_ingreso else None,
        "dia_mas_atenciones": max(desglose, key=lambda t: t["atenciones"]) if por_dias and tope_atencion else None,
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
        # Solo en el mes:
        "semanas_del_mes": [],
        "comisiones_semanales": None,
        "por_dia_semana": [],
    }
    if periodo.tipo == MES:
        cifras.update(_extras_del_mes(desglose, lista_semanas, caja_semana, resumen_groomers))
    return cifras


def _extras_del_mes(desglose, lista_semanas, caja_semana, resumen_groomers):
    """Resumen por semana, comisiones semanales y atenciones por día de la semana."""
    comisiones = _comisiones_semanales(resumen_groomers, lista_semanas)
    resumen = []
    for i, s in enumerate(lista_semanas):
        dias = [t for t in desglose if s["desde"] <= t["fecha"] <= s["hasta"]]
        resumen.append({
            **s,
            "ingresos": sum((t["ingresos"] for t in dias), CERO),
            "consultas": sum(t["consultas"] for t in dias),
            "peluquerias": sum(t["peluquerias"] for t in dias),
            "atenciones": sum(t["atenciones"] for t in dias),
            "caja_ingresos": caja_semana[i]["ingresos"],
            "caja_salidas": caja_semana[i]["salidas"],
            "balance": caja_semana[i]["ingresos"] - caja_semana[i]["salidas"],
            "comision": comisiones["totales"][i],
        })

    por_dia_semana = []
    for d in DOMINGO_A_SABADO:
        dias = [t for t in desglose if t["fecha"].weekday() == d]
        por_dia_semana.append({"orden": d, "corto": semanas.DIAS_CORTOS[d], "nombre": DIAS_PLURAL[d],
                               "atenciones": sum(t["atenciones"] for t in dias)})
    return {"semanas_del_mes": resumen, "comisiones_semanales": comisiones, "por_dia_semana": por_dia_semana}


# ---------------------------------------------------------------------------
# Serie de los últimos periodos (tendencia y pronóstico)
# ---------------------------------------------------------------------------

def serie(periodo, cantidad=None):
    """
    Ingresos y atenciones de los últimos `cantidad` periodos del mismo tipo que
    terminan en `periodo` (del más antiguo al último): 14 días, 8 semanas o 6
    meses si no se indica. Tres consultas en total, sin importar cuántos sean.
    Si llega una fecha, es el sábado de una semana (como antes de PB-20).
    """
    periodo = como_periodo(periodo)
    cantidad = cantidad or periodos.TENDENCIA[periodo.tipo]
    lista = [periodo]
    while len(lista) < cantidad:
        lista.insert(0, lista[0].anterior())
    filas = {p.desde: {"periodo": p, "desde": p.desde, "hasta": p.hasta, "sabado": p.sabado, "corto": p.corto,
                       "ingresos": CERO, "atenciones": 0} for p in lista}
    desde, hasta = lista[0].desde, periodo.hasta
    inicio, fin = semanas.limites(desde, hasta)

    def fila(fecha):
        return filas[Periodo.de(periodo.tipo, fecha).desde]

    for f in Factura.objects.filter(estado=Factura.PAGADA, fecha__gte=inicio, fecha__lt=fin).values("fecha", "total"):
        fila(timezone.localdate(f["fecha"]))["ingresos"] += f["total"]
    for fecha in Cita.objects.filter(estado="atendida", fecha__range=(desde, hasta)).values_list("fecha", flat=True):
        fila(fecha)["atenciones"] += 1
    for momento in (CitaPeluqueria.objects.filter(estado="Realizada", fecha_hora__gte=inicio, fecha_hora__lt=fin)
                    .values_list("fecha_hora", flat=True)):
        fila(timezone.localdate(momento))["atenciones"] += 1
    return [filas[p.desde] for p in lista]


def variaciones(actual, anterior):
    """Cambios frente al periodo anterior para las tarjetas de resumen."""
    return {
        "ingresos": _variacion(actual["ingresos"], anterior["ingresos"]),
        "atenciones": _variacion(actual["atenciones"], anterior["atenciones"]),
    }
