"""
Pronóstico de la semana siguiente.

Método: recta de tendencia (mínimos cuadrados) sobre las últimas semanas.
El rango es ± el error típico de esa recta: cuánto se han alejado las
semanas reales de la tendencia. Con pocos datos no se pronostica, porque
una recta con dos puntos no dice nada.
"""

from dataclasses import dataclass
from math import sqrt

MINIMO_SEMANAS_CON_DATOS = 3


@dataclass
class Pronostico:
    valor: float
    bajo: float
    alto: float
    pendiente: float          # cambio promedio por semana según la tendencia
    semanas_usadas: int

    @property
    def tendencia(self):
        """'sube', 'baja' o 'estable' (cambio menor al 3 % del valor por semana)."""
        if self.valor and abs(self.pendiente) < 0.03 * self.valor:
            return "estable"
        return "sube" if self.pendiente > 0 else "baja"


def pronosticar(valores):
    """`valores`: de la semana más antigua a la más reciente. Devuelve Pronostico o None."""
    valores = [float(v) for v in valores]
    # Las semanas iniciales sin movimiento (antes de usar el sistema) no cuentan.
    while valores and not valores[0]:
        valores.pop(0)
    n = len(valores)
    if n < MINIMO_SEMANAS_CON_DATOS or sum(1 for v in valores if v) < MINIMO_SEMANAS_CON_DATOS:
        return None

    media_x = (n - 1) / 2
    media_y = sum(valores) / n
    sxx = sum((x - media_x) ** 2 for x in range(n))
    pendiente = sum((x - media_x) * (y - media_y) for x, y in enumerate(valores)) / sxx
    corte = media_y - pendiente * media_x

    residuos = [y - (corte + pendiente * x) for x, y in enumerate(valores)]
    error = sqrt(sum(r * r for r in residuos) / (n - 2)) if n > 2 else 0.0

    valor = max(0.0, corte + pendiente * n)
    return Pronostico(
        valor=valor,
        bajo=max(0.0, valor - error),
        alto=valor + error,
        pendiente=pendiente,
        semanas_usadas=n,
    )
