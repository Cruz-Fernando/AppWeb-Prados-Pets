"""
Simulador de IA del reporte semanal.

Lee las cifras de la semana y escribe, como lo haría un asistente:
  - un resumen en palabras de cómo fue la semana, y
  - recomendaciones ordenadas por urgencia.

No es un modelo de lenguaje: son reglas con umbrales fijos (abajo), así que
siempre da la misma respuesta para los mismos datos y no envía información
de la clínica a ningún servicio externo.
"""

from decimal import Decimal

from .semanas import hora_texto

# Umbrales de las reglas
CAIDA_FUERTE = -15          # % de caída de ingresos frente a la semana anterior
SUBIDA_FUERTE = 15          # % de subida para felicitar
CANCELACION_ALTA = 15       # % de citas canceladas
MINIMO_CITAS_CANCELACION = 5
CONCENTRACION = 70          # % de los ingresos en una sola línea
PRODUCTOS_BAJOS = 10        # % de productos dentro de lo facturado
AGENDA_FLOJA = 0.5          # agenda siguiente por debajo de la mitad del promedio semanal

TIPOS = {
    "alerta": {"orden": 0, "etiqueta": "Atender ya"},
    "mejora": {"orden": 1, "etiqueta": "Para mejorar"},
    "oportunidad": {"orden": 2, "etiqueta": "Oportunidad"},
    "logro": {"orden": 3, "etiqueta": "Bien hecho"},
}

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def pesos(valor):
    """1234567.8 → «$1.234.568» (formato colombiano, sin decimales)."""
    entero = int(Decimal(valor or 0).quantize(Decimal("1")))
    signo = "-" if entero < 0 else ""
    return f"{signo}${abs(entero):,}".replace(",", ".")


def fecha_larga(fecha):
    return f"{fecha.day} de {MESES[fecha.month - 1]}"


def rango_semana(desde, hasta):
    """«domingo 15 y el sábado 21 de noviembre» (con el mes en ambos si la semana cruza de mes)."""
    inicio = fecha_larga(desde) if desde.month != hasta.month else str(desde.day)
    return f"domingo {inicio} y el sábado {fecha_larga(hasta)}"


def _n(cantidad, singular, plural):
    """«1 producto agotado», «3 productos agotados»."""
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _lista(nombres):
    nombres = list(nombres)
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


def _reco(tipo, area, titulo, texto):
    return {"tipo": tipo, "etiqueta": TIPOS[tipo]["etiqueta"], "area": area, "titulo": titulo, "texto": texto}


# ---------------------------------------------------------------------------

def analizar(semana, serie, variacion, pronostico_ingresos=None, pronostico_atenciones=None,
             recordatorios_pendientes=None):
    """
    semana: cifras de calculos.calcular()
    serie: últimas semanas de calculos.serie() (la última es esta semana)
    variacion: calculos.variaciones()
    recordatorios_pendientes: cantidad por avisar hoy (solo para el reporte más reciente)
    """
    anterior = serie[-2] if len(serie) >= 2 else None
    previas = [s["atenciones"] for s in serie[:-1] if s["atenciones"]]
    promedio_atenciones = sum(previas) / len(previas) if previas else 0
    lineas = sorted(semana["lineas"], key=lambda l: -l["monto"])
    principal = lineas[0] if lineas and lineas[0]["monto"] else None
    sin_movimiento = not semana["ingresos"] and not semana["atenciones"] and not semana["programadas"]

    return {
        "resumen": _resumen(semana, anterior, variacion, principal, pronostico_ingresos, sin_movimiento),
        "recomendaciones": _recomendaciones(semana, variacion, principal, promedio_atenciones,
                                            pronostico_ingresos, recordatorios_pendientes, sin_movimiento),
    }


def _resumen(semana, anterior, variacion, principal, pronostico, sin_movimiento):
    rango = f"Entre el {rango_semana(semana['desde'], semana['hasta'])}"
    if sin_movimiento:
        return [f"{rango} no se registraron cobros, citas ni servicios en el sistema."]

    frases = []
    if semana["facturas"]:
        frase = (f"{rango} se cobraron {pesos(semana['ingresos'])} en {semana['facturas']} "
                 f"factura{'s' if semana['facturas'] != 1 else ''}, con un ticket promedio de "
                 f"{pesos(semana['ticket_promedio'])}.")
        cambio = variacion["ingresos"]
        if cambio is not None and anterior:
            if cambio > 0:
                frase += f" Es un {cambio} % más que la semana anterior ({pesos(anterior['ingresos'])})."
            elif cambio < 0:
                frase += f" Es un {abs(cambio)} % menos que la semana anterior ({pesos(anterior['ingresos'])})."
            else:
                frase += " Igual que la semana anterior."
        frases.append(frase)
    else:
        frases.append(f"{rango} no se cobró ninguna factura.")

    atenciones = (f"Se atendieron {semana['consultas']} consulta{'s' if semana['consultas'] != 1 else ''} y "
                  f"{semana['peluquerias']} servicio{'s' if semana['peluquerias'] != 1 else ''} de peluquería")
    dia = semana["dia_mas_atenciones"]
    if dia:
        atenciones += f"; el día con más movimiento fue el {dia['nombre']} ({dia['atenciones']} atenciones)"
    frases.append(atenciones + ".")

    if principal:
        frases.append(f"Lo que más ingresos dejó fue {principal['nombre'].lower()}: "
                      f"{pesos(principal['monto'])}, el {principal['porcentaje']} % de lo facturado.")

    caja = semana["caja"]
    if caja["gastos"] or caja["ingresos"]:
        if caja["balance"] >= 0:
            frases.append(f"La caja cerró con un balance positivo de {pesos(caja['balance'])} "
                          f"después de {pesos(caja['gastos'])} en gastos.")
        else:
            frases.append(f"La caja cerró en pérdida ({pesos(caja['balance'])}): los gastos y anulaciones "
                          f"superaron lo que entró.")

    if pronostico:
        frases.append(f"Si se mantiene la tendencia de las últimas {pronostico.semanas_usadas} semanas, la próxima "
                      f"semana se cobrarían unos {pesos(pronostico.valor)} (entre {pesos(pronostico.bajo)} y "
                      f"{pesos(pronostico.alto)}).")
    else:
        frases.append("Todavía no hay suficientes semanas con cobros para pronosticar la siguiente.")
    return frases


def _recomendaciones(semana, variacion, principal, promedio_atenciones, pronostico, pendientes, sin_movimiento):
    recos = []
    caja = semana["caja"]

    if sin_movimiento:
        return [_reco("alerta", "Uso del sistema", "Revisa que se esté registrando la actividad",
                      "Si la clínica atendió esta semana, falta cerrar las citas como atendidas y cobrar las "
                      "facturas en el sistema: sin eso el reporte no puede medir nada.")]

    # --- Dinero -------------------------------------------------------------
    if caja["balance"] < 0:
        recos.append(_reco("alerta", "Caja", "La semana cerró en pérdida",
                           f"Salieron {pesos(caja['gastos'] + caja['anulaciones'])} entre gastos y anulaciones y "
                           f"entraron {pesos(caja['ingresos'])}. Revisa en Caja si algún gasto grande, como el "
                           f"arriendo, cayó esta semana o si hubo anulaciones que se puedan evitar."))

    cambio = variacion["ingresos"]
    if cambio is not None and cambio <= CAIDA_FUERTE:
        recos.append(_reco("alerta", "Ventas", f"Los ingresos bajaron un {abs(cambio)} %",
                           "Llama o escribe a los clientes con recordatorios pendientes y ofrece cupos en los días "
                           "flojos de la próxima semana. Revisa también si quedaron facturas en borrador sin cobrar."))
    elif cambio is not None and cambio >= SUBIDA_FUERTE:
        recos.append(_reco("logro", "Ventas", f"Los ingresos subieron un {cambio} %",
                           "Anota qué fue distinto esta semana (promociones, campañas, días con más personal) "
                           "para repetirlo."))

    # --- Agenda -------------------------------------------------------------
    if semana["programadas"] >= MINIMO_CITAS_CANCELACION and semana["tasa_cancelacion"] >= CANCELACION_ALTA:
        recos.append(_reco("mejora", "Agenda", f"Se canceló el {semana['tasa_cancelacion']} % de las citas",
                           f"Fueron {semana['canceladas']} de {semana['programadas']}. Confirma cada cita por "
                           f"WhatsApp el día anterior y ofrece el cupo liberado a otro cliente."))

    if semana["por_cerrar"]:
        recos.append(_reco("mejora", "Agenda", _n(semana['por_cerrar'], "cita pasada sigue como programada", "citas pasadas siguen como programadas"),
                           "Márcalas como atendidas, realizadas o canceladas. Mientras sigan abiertas no cuentan en "
                           "los ingresos ni en las comisiones de los groomers."))

    dias = [d for d in semana["dias"] if d["corto"] != "Dom"]
    if dias:
        flojo = min(dias, key=lambda d: (d["atenciones"], d["fecha"]))
        fuerte = max(dias, key=lambda d: (d["atenciones"], -d["fecha"].toordinal()))
        if fuerte["atenciones"] >= 4 and fuerte["atenciones"] >= 2 * max(flojo["atenciones"], 1):
            recos.append(_reco("oportunidad", "Agenda", f"El {flojo['nombre']} fue el día más tranquilo",
                               f"Tuvo {flojo['atenciones']} atenciones frente a {fuerte['atenciones']} del "
                               f"{fuerte['nombre']}. Ofrece baños o vacunación con descuento ese día para repartir "
                               f"mejor el trabajo."))

    if semana["hora_pico"] is not None:
        recos.append(_reco("oportunidad", "Personal", f"La hora más pedida fue a las {hora_texto(semana['hora_pico'])}",
                           "Procura que a esa hora haya alguien libre en recepción para recibir mascotas y cobrar."))

    if promedio_atenciones and semana["agenda_siguiente"] < AGENDA_FLOJA * promedio_atenciones:
        recos.append(_reco("mejora", "Agenda", "La agenda de la próxima semana está floja",
                           f"Hay {_n(semana['agenda_siguiente'], 'cita agendada', 'citas agendadas')} y una semana normal tiene unas "
                           f"{round(promedio_atenciones)} atenciones. Escribe a los clientes con vacunas o baños por "
                           f"vencer para llenar los cupos."))

    # --- Clientes -------------------------------------------------------------
    if pendientes:
        recos.append(_reco("oportunidad", "Clientes", _n(pendientes, "recordatorio espera aviso", "recordatorios esperan aviso"),
                           "Son vacunas o baños que ya tocan. Cada aviso por WhatsApp es una cita posible: están en "
                           "el panel con su botón para escribir al dueño."))

    if semana["duenos_nuevos"] == 0 and semana["atenciones"]:
        recos.append(_reco("mejora", "Clientes", "No llegaron clientes nuevos",
                           "Pide a los clientes de esta semana que recomienden la clínica o publica en redes los "
                           "servicios de peluquería con fotos de antes y después."))
    elif semana["duenos_nuevos"] >= 3:
        recos.append(_reco("logro", "Clientes", f"Llegaron {semana['duenos_nuevos']} clientes nuevos",
                           "Agéndales desde ya el siguiente control o baño para que vuelvan."))

    # --- Mezcla de ingresos ---------------------------------------------------
    lineas = {l["clave"]: l for l in semana["lineas"]}
    if principal and principal["porcentaje"] >= CONCENTRACION:
        recos.append(_reco("oportunidad", "Ventas",
                           f"El {principal['porcentaje']} % de los ingresos vino de {principal['nombre'].lower()}",
                           "Depender de una sola línea es riesgoso. Ofrece a esos mismos clientes los otros "
                           "servicios de la clínica."))
    producto = lineas.get("PRODUCTO")
    peluqueria = lineas.get("PELUQUERIA")
    if (producto is not None and peluqueria is not None and peluqueria["monto"]
            and producto["porcentaje"] < PRODUCTOS_BAJOS):
        recos.append(_reco("oportunidad", "Ventas", "Casi no se venden productos",
                           "Al entregar una mascota de peluquería, ofrece el shampoo o el antipulgas que se usó en "
                           "el baño."))

    # --- Inventario -----------------------------------------------------------
    if semana["agotados"]:
        nombres = [p["nombre"] for p in semana["stock_bajo"] if p["stock_actual"] == 0][:3]
        recos.append(_reco("alerta", "Inventario", _n(semana['agotados'], "producto agotado", "productos agotados"),
                           f"Pide reposición de {_lista(nombres)}. Sin stock no se pueden vender ni descontar en "
                           f"consultas y peluquería."))
    elif semana["stock_bajo"]:
        nombres = [p["nombre"] for p in semana["stock_bajo"]][:3]
        recos.append(_reco("mejora", "Inventario", _n(len(semana['stock_bajo']), "producto con stock bajo", "productos con stock bajo"),
                           f"Programa la compra de {_lista(nombres)} antes de que se agoten."))
    if semana["vencidos"]:
        recos.append(_reco("alerta", "Inventario", _n(len(semana['vencidos']), "producto vencido con unidades", "productos vencidos con unidades"),
                           "Retíralos del inventario con un ajuste por vencimiento para que no se usen ni se vendan."))
    if semana["por_vencer"]:
        recos.append(_reco("mejora", "Inventario", _n(len(semana['por_vencer']), "producto vence en 30 días", "productos vencen en 30 días"),
                           "Úsalos primero en consultas y peluquería o promociónalos antes de que se pierdan."))

    # --- Pronóstico -----------------------------------------------------------
    if pronostico and pronostico.tendencia == "baja" and semana["ingresos"]:
        recos.append(_reco("mejora", "Ventas", "La tendencia de ingresos va a la baja",
                           f"Las últimas {pronostico.semanas_usadas} semanas vienen bajando unos "
                           f"{pesos(abs(pronostico.pendiente))} por semana. Planea una campaña antes de que se note "
                           f"más."))
    elif pronostico and pronostico.tendencia == "sube" and semana["ingresos"]:
        recos.append(_reco("logro", "Ventas", "La tendencia de ingresos va al alza",
                           f"Las últimas {pronostico.semanas_usadas} semanas suben unos "
                           f"{pesos(pronostico.pendiente)} por semana."))

    return sorted(recos, key=lambda r: TIPOS[r["tipo"]]["orden"])
