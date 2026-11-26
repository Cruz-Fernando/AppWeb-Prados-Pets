"""
Geometría de las gráficas del reporte (SVG dibujado en el servidor, sin librerías).

Aquí solo se calculan coordenadas y textos; las plantillas en
templates/reportes/_grafica_*.html dibujan el SVG. Reglas de dibujo: barras
de máximo 24 px con la punta redondeada (4 px) y la base recta, líneas de
2 px, puntos de 8 px con anillo del color del fondo y cuadrícula de 1 px.
"""

from decimal import Decimal
from math import floor, log10

ANCHO = 640
ALTO = 220
MARGEN = {"izq": 60, "der": 16, "arriba": 18, "abajo": 30}
BARRA_MAX = 24
PUNTA = 4


def _paso_bonito(maximo, divisiones=4):
    """Paso de la cuadrícula redondeado a 1, 2, 2.5 o 5 × 10^k."""
    if maximo <= 0:
        return 1
    bruto = maximo / divisiones
    base = 10 ** floor(log10(bruto))
    for m in (1, 2, 2.5, 5, 10):
        if bruto <= m * base:
            return m * base
    return 10 * base


def _escala(maximo, divisiones=4, entero=False):
    paso = _paso_bonito(maximo, divisiones)
    if entero:
        paso = max(1, round(paso))
    tope = paso * max(1, -(-maximo // paso) if maximo else 1)
    return paso, tope


def compacto_pesos(valor):
    """Etiquetas de eje: $0, $800, $50 mil, $1,2 M."""
    valor = float(valor)
    if abs(valor) >= 1_000_000:
        texto = f"{valor / 1_000_000:.1f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"${texto} M"
    if abs(valor) >= 1_000:
        texto = f"{valor / 1000:.1f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"${texto} mil"
    return f"${round(valor)}"


def pesos(valor):
    entero = int(Decimal(valor or 0).quantize(Decimal("1")))
    return f"${entero:,}".replace(",", ".")


def _barra(x, y, ancho, base):
    """Path de una barra con la punta redondeada y la base recta."""
    alto = base - y
    if alto <= 0:
        return ""
    r = min(PUNTA, alto, ancho / 2)
    return (f"M{x:.1f},{base:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
            f"H{x + ancho - r:.1f} Q{x + ancho:.1f},{y:.1f} {x + ancho:.1f},{y + r:.1f} V{base:.1f} Z")


def _marco(maximo, formato, entero=False):
    paso, tope = _escala(maximo, entero=entero)
    alto_util = ALTO - MARGEN["arriba"] - MARGEN["abajo"]
    base = ALTO - MARGEN["abajo"]

    def y_de(v):
        return base - (float(v) / tope) * alto_util if tope else base

    ticks = []
    v = 0
    while v <= tope + 1e-9:
        ticks.append({"y": round(y_de(v), 1), "texto": formato(v)})
        v += paso
    return y_de, base, ticks


def columnas(etiquetas, valores, formato_valor, formato_eje, descripcion, entero=False, etiquetas_eje=None):
    """Columnas de una sola serie (p. ej. ingresos por día). `etiquetas_eje`: textos cortos bajo
    cada barra si las etiquetas completas no caben (p. ej. «7a» para «7 a. m.»)."""
    maximo = max((float(v) for v in valores), default=0)
    y_de, base, ticks = _marco(maximo, formato_eje, entero)
    ancho_util = ANCHO - MARGEN["izq"] - MARGEN["der"]
    hueco = ancho_util / max(len(valores), 1)
    ancho = min(BARRA_MAX, hueco * 0.55)
    barras = []
    for i, (etiqueta, valor) in enumerate(zip(etiquetas, valores)):
        x = MARGEN["izq"] + hueco * i + (hueco - ancho) / 2
        y = y_de(valor)
        barras.append({
            "d": _barra(x, y, ancho, base),
            "x_centro": round(x + ancho / 2, 1),
            "y_valor": round(y - 6, 1),
            "etiqueta": etiqueta,
            "eje": etiquetas_eje[i] if etiquetas_eje else etiqueta,
            "valor": formato_valor(valor),
            "vacio": not float(valor),
            "hit_x": round(MARGEN["izq"] + hueco * i, 1),
            "hit_ancho": round(hueco, 1),
        })
    destacada = max(range(len(valores)), key=lambda i: float(valores[i])) if maximo else None
    if destacada is not None:
        barras[destacada]["destacada"] = True
    return {"ancho": ANCHO, "alto": ALTO, "base": base, "izq": MARGEN["izq"], "der": ANCHO - MARGEN["der"],
            "ticks": ticks, "barras": barras, "descripcion": descripcion, "hit_alto": base - MARGEN["arriba"],
            "hit_y": MARGEN["arriba"], "y_etiqueta": base + 20}


def columnas_apiladas(etiquetas, series, descripcion, etiquetas_eje=None):
    """Columnas apiladas de conteos. `series`: [(nombre, css, [valores])], de abajo hacia arriba."""
    totales = [sum(s[2][i] for s in series) for i in range(len(etiquetas))]
    maximo = max(totales, default=0)
    y_de, base, ticks = _marco(maximo, lambda v: f"{int(v)}", entero=True)
    ancho_util = ANCHO - MARGEN["izq"] - MARGEN["der"]
    hueco = ancho_util / max(len(etiquetas), 1)
    ancho = min(BARRA_MAX, hueco * 0.55)
    grupos = []
    for i, etiqueta in enumerate(etiquetas):
        x = MARGEN["izq"] + hueco * i + (hueco - ancho) / 2
        abajo = base
        acumulado = 0
        segmentos = []
        visibles = [s for s in series if s[2][i]]
        for nombre, css, valores in series:
            v = valores[i]
            if not v:
                continue
            acumulado += v
            arriba = y_de(acumulado)
            # 2 px del color del fondo separan un segmento del de abajo
            piso = abajo - 2 if segmentos else abajo
            if nombre == visibles[-1][0]:
                d = _barra(x, arriba, ancho, piso)
            elif piso > arriba:
                d = f"M{x:.1f},{piso:.1f} V{arriba:.1f} H{x + ancho:.1f} V{piso:.1f} Z"
            else:
                d = ""
            segmentos.append({"d": d, "css": css, "nombre": nombre, "valor": v})
            abajo = arriba
        grupos.append({
            "segmentos": segmentos,
            "x_centro": round(x + ancho / 2, 1),
            "y_total": round(y_de(totales[i]) - 6, 1),
            "total": totales[i],
            "etiqueta": etiqueta,
            "eje": etiquetas_eje[i] if etiquetas_eje else etiqueta,
            "detalle": ", ".join(f"{s['nombre']}: {s['valor']}" for s in segmentos) or "sin atenciones",
            "por_serie": [s[2][i] for s in series],
            "hit_x": round(MARGEN["izq"] + hueco * i, 1),
            "hit_ancho": round(hueco, 1),
        })
    if maximo:
        grupos[max(range(len(totales)), key=lambda i: totales[i])]["destacada"] = True
    return {"ancho": ANCHO, "alto": ALTO, "base": base, "izq": MARGEN["izq"], "der": ANCHO - MARGEN["der"],
            "ticks": ticks, "grupos": grupos, "descripcion": descripcion, "hit_alto": base - MARGEN["arriba"],
            "hit_y": MARGEN["arriba"], "y_etiqueta": base + 20,
            "leyenda": [{"nombre": n, "css": c} for n, c, _ in series]}


def linea_con_pronostico(etiquetas, valores, pronostico, formato_valor, formato_eje, descripcion,
                         etiqueta_pronostico, entero=False, texto_punto="Semana que cerró el",
                         texto_futuro="Pronóstico para la semana que cierra el"):
    """Línea de los últimos periodos y, si hay, el punto pronosticado con su rango.
    texto_punto / texto_futuro: cómo se nombra cada punto en el tooltip y en la tabla."""
    tope_datos = max((float(v) for v in valores), default=0)
    maximo = max(tope_datos, pronostico.alto if pronostico else 0)
    y_de, base, ticks = _marco(maximo, formato_eje, entero)
    n = len(valores) + (1 if pronostico else 0)
    ancho_util = ANCHO - MARGEN["izq"] - MARGEN["der"] - 40   # aire a la derecha para la etiqueta final
    hueco = ancho_util / max(n - 1, 1)

    def x_de(i):
        return MARGEN["izq"] + 12 + hueco * i

    puntos = [{"x": round(x_de(i), 1), "y": round(y_de(v), 1), "valor": formato_valor(v), "etiqueta": e,
               "hit_x": round(x_de(i) - 14, 1)}
              for i, (e, v) in enumerate(zip(etiquetas, valores))]
    camino = " ".join(f"{'M' if i == 0 else 'L'}{p['x']},{p['y']}" for i, p in enumerate(puntos))
    area = (f"{camino} L{puntos[-1]['x']},{base} L{puntos[0]['x']},{base} Z") if puntos else ""

    futuro = None
    if pronostico and puntos:
        x = round(x_de(len(valores)), 1)
        futuro = {
            "x": x,
            "hit_x": round(x - 14, 1),
            "y": round(y_de(pronostico.valor), 1),
            "y_bajo": round(y_de(pronostico.bajo), 1),
            "y_alto": round(y_de(pronostico.alto), 1),
            "valor": formato_valor(pronostico.valor),
            "rango": f"{formato_valor(pronostico.bajo)} a {formato_valor(pronostico.alto)}",
            "etiqueta": etiqueta_pronostico,
            "desde_x": puntos[-1]["x"],
            "desde_y": puntos[-1]["y"],
        }
    return {"ancho": ANCHO, "alto": ALTO, "base": base, "izq": MARGEN["izq"], "der": ANCHO - MARGEN["der"],
            "ticks": ticks, "puntos": puntos, "camino": camino, "area": area, "futuro": futuro,
            "ultimo": puntos[-1] if puntos else None, "descripcion": descripcion, "y_etiqueta": base + 20,
            "hueco": round(hueco, 1), "hit_y": MARGEN["arriba"], "hit_alto": base - MARGEN["arriba"],
            "texto_punto": texto_punto, "texto_futuro": texto_futuro}
