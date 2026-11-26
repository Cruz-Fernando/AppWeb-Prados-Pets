"""
Arma el reporte completo de un periodo (día, semana o mes): cifras,
tendencia, pronóstico, análisis y gráficas.

Se guarda en caché para que abrir el PDF justo después de ver la pantalla no
repita las ~25 consultas a la base. Un periodo en curso (hoy, el mes actual o
la semana el sábado en que se publica) se refresca seguido porque todavía
entran datos; uno que ya cerró dura más.
"""

from django.core.cache import cache
from django.utils import timezone

from apps.clinico.recordatorios import calcular_recordatorios

from . import analista, calculos, graficas, periodos
from .periodos import DIA, MES, SEMANA, como_periodo
from .pronostico import pronosticar

CACHE_EN_CURSO = 120          # segundos
CACHE_CERRADO = 30 * 60

# Cómo se nombran los puntos de la gráfica de tendencia en el tooltip y la tabla.
PUNTOS_TENDENCIA = {
    DIA: ("Día", "Pronóstico para el"),
    SEMANA: ("Semana que cerró el", "Pronóstico para la semana que cierra el"),
    MES: ("Mes de", "Pronóstico para"),
}


def _clave(periodo):
    return f"reportes:v2:{periodo.clave}"


def generar(periodo, ahora=None, usar_cache=True):
    """`periodo`: periodos.Periodo, o el sábado de una semana (como antes de PB-20)."""
    periodo = como_periodo(periodo)
    ahora = ahora or timezone.now()
    hoy = timezone.localdate(ahora)
    if usar_cache:
        guardado = cache.get(_clave(periodo))
        if guardado is not None:
            return guardado

    t = periodo.textos
    cifras = calculos.calcular(periodo, ahora=ahora)
    serie = calculos.serie(periodo)
    variacion = calculos.variaciones(cifras, serie[-2]) if len(serie) >= 2 else {"ingresos": None, "atenciones": None}
    p_ingresos = pronosticar([s["ingresos"] for s in serie])
    p_atenciones = pronosticar([s["atenciones"] for s in serie])

    # Los recordatorios pendientes son de hoy: solo tienen sentido en el reporte más reciente.
    pendientes = None
    if periodo == periodos.ultimo_valido(periodo.tipo, hoy):
        pendientes = len(calcular_recordatorios()["pendientes"])

    analisis = analista.analizar(cifras, serie, variacion, p_ingresos, p_atenciones, pendientes, periodo=periodo)

    tope_i = max((x["ingresos"] for x in serie), default=0)
    tope_a = max((x["atenciones"] for x in serie), default=0)
    for x in serie:   # anchos relativos para las barras del PDF
        x["ancho_ingresos"] = calculos._porcentaje(x["ingresos"], tope_i)
        x["ancho_atenciones"] = calculos._porcentaje(x["atenciones"], tope_a)

    desglose = cifras["desglose"]
    # Las horas no caben completas bajo las barras: «7a», «3p» en el eje, «7 a. m.» en el tooltip.
    # En el mes, 30 números seguidos se pegan: el eje muestra el 1 y cada 5 días.
    etiquetas = [d["corto"] if periodo.tipo == SEMANA else d["nombre"] for d in desglose]
    if periodo.tipo == DIA:
        eje = [d["corto"] for d in desglose]
    elif periodo.tipo == MES:
        eje = [d["corto"] if d["fecha"].day == 1 or d["fecha"].day % 5 == 0 else "" for d in desglose]
    else:
        eje = None
    etiquetas_tendencia = [s["corto"] for s in serie]
    texto_punto, texto_futuro = PUNTOS_TENDENCIA[periodo.tipo]

    reporte = {
        "cifras": cifras,
        "periodo": periodo,
        "serie": serie,
        "variacion": variacion,
        "pronostico_ingresos": p_ingresos,
        "pronostico_atenciones": p_atenciones,
        "recordatorios_pendientes": pendientes,
        "analisis": analisis,
        "graficas": {
            "ingresos_dia": graficas.columnas(
                etiquetas, [d["ingresos"] for d in desglose],
                graficas.pesos, graficas.compacto_pesos, f"Ingresos cobrados {t['por_tramo']}", etiquetas_eje=eje),
            "atenciones_dia": graficas.columnas_apiladas(
                etiquetas,
                [("Consultas", "consulta", [d["consultas"] for d in desglose]),
                 ("Peluquería", "peluqueria", [d["peluquerias"] for d in desglose])],
                f"Consultas atendidas y servicios de peluquería realizados {t['por_tramo']}", etiquetas_eje=eje),
            "tendencia_ingresos": graficas.linea_con_pronostico(
                etiquetas_tendencia, [s["ingresos"] for s in serie], p_ingresos,
                graficas.pesos, graficas.compacto_pesos, f"Ingresos cobrados por {t['nombre']}",
                periodo.siguiente().corto, texto_punto=texto_punto, texto_futuro=texto_futuro),
            "tendencia_atenciones": graficas.linea_con_pronostico(
                etiquetas_tendencia, [s["atenciones"] for s in serie], p_atenciones,
                lambda v: f"{round(float(v))}", lambda v: f"{int(v)}", f"Atenciones por {t['nombre']}",
                periodo.siguiente().corto, entero=True, texto_punto=texto_punto, texto_futuro=texto_futuro),
        },
        "generado": ahora,
    }
    cache.set(_clave(periodo), reporte, CACHE_EN_CURSO if periodo.en_curso(hoy) else CACHE_CERRADO)
    return reporte
