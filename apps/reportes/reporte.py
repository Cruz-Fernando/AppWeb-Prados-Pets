"""
Arma el reporte semanal completo: cifras, tendencia, pronóstico, análisis y gráficas.

Se guarda en caché unos minutos para que abrir el PDF justo después de ver
la pantalla no repita las ~25 consultas a la base. El reporte del sábado en
curso se refresca más seguido porque ese día todavía entran datos.
"""

from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from apps.clinico.recordatorios import calcular_recordatorios

from . import analista, calculos, graficas, semanas
from .pronostico import pronosticar

SEMANAS_TENDENCIA = 8
CACHE_SABADO_ACTUAL = 120        # segundos
CACHE_SEMANA_CERRADA = 30 * 60


def _clave(sabado):
    return f"reportes:semanal:v1:{sabado.isoformat()}"


def generar(sabado, ahora=None, usar_cache=True):
    ahora = ahora or timezone.now()
    hoy = timezone.localdate(ahora)
    if usar_cache:
        guardado = cache.get(_clave(sabado))
        if guardado is not None:
            return guardado

    semana = calculos.calcular(sabado, ahora=ahora)
    serie = calculos.serie(sabado, SEMANAS_TENDENCIA)
    variacion = calculos.variaciones(semana, serie[-2]) if len(serie) >= 2 else {"ingresos": None, "atenciones": None}
    p_ingresos = pronosticar([s["ingresos"] for s in serie])
    p_atenciones = pronosticar([s["atenciones"] for s in serie])

    # Los recordatorios pendientes son de hoy: solo tienen sentido en el reporte más reciente.
    pendientes = None
    if sabado == semanas.ultimo_publicado(hoy):
        pendientes = len(calcular_recordatorios()["pendientes"])

    analisis = analista.analizar(semana, serie, variacion, p_ingresos, p_atenciones, pendientes)

    tope_i = max((x["ingresos"] for x in serie), default=0)
    tope_a = max((x["atenciones"] for x in serie), default=0)
    for x in serie:   # anchos relativos para las barras del PDF
        x["ancho_ingresos"] = calculos._porcentaje(x["ingresos"], tope_i)
        x["ancho_atenciones"] = calculos._porcentaje(x["atenciones"], tope_a)

    etiquetas_semana = [f"{s['sabado'].day}/{s['sabado'].month}" for s in serie]
    proximo = sabado + timedelta(days=7)
    etiqueta_futuro = f"{proximo.day}/{proximo.month}"

    reporte = {
        "semana": semana,
        "serie": serie,
        "variacion": variacion,
        "pronostico_ingresos": p_ingresos,
        "pronostico_atenciones": p_atenciones,
        "recordatorios_pendientes": pendientes,
        "analisis": analisis,
        "graficas": {
            "ingresos_dia": graficas.columnas(
                [d["corto"] for d in semana["dias"]], [d["ingresos"] for d in semana["dias"]],
                graficas.pesos, graficas.compacto_pesos, "Ingresos cobrados por día"),
            "atenciones_dia": graficas.columnas_apiladas(
                [d["corto"] for d in semana["dias"]],
                [("Consultas", "consulta", [d["consultas"] for d in semana["dias"]]),
                 ("Peluquería", "peluqueria", [d["peluquerias"] for d in semana["dias"]])],
                "Consultas atendidas y servicios de peluquería realizados por día"),
            "tendencia_ingresos": graficas.linea_con_pronostico(
                etiquetas_semana, [s["ingresos"] for s in serie], p_ingresos,
                graficas.pesos, graficas.compacto_pesos, "Ingresos cobrados por semana", etiqueta_futuro),
            "tendencia_atenciones": graficas.linea_con_pronostico(
                etiquetas_semana, [s["atenciones"] for s in serie], p_atenciones,
                lambda v: f"{round(float(v))}", lambda v: f"{int(v)}", "Atenciones por semana",
                etiqueta_futuro, entero=True),
        },
        "generado": ahora,
    }
    cache.set(_clave(sabado), reporte, CACHE_SABADO_ACTUAL if sabado == hoy else CACHE_SEMANA_CERRADA)
    return reporte
