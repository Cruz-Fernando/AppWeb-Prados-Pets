from django import template

from apps.reportes.analista import pesos as _pesos

register = template.Library()


@register.filter
def pesos(valor):
    """1234567 → $1.234.567"""
    return _pesos(valor)


@register.filter
def variacion(valor):
    """12 → «+12 %», -8 → «−8 %», None → «»."""
    if valor is None:
        return ""
    if valor > 0:
        return f"+{valor} %"
    if valor < 0:
        return f"−{abs(valor)} %"
    return "0 %"
