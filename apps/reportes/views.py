"""
Reportes (PB-20 / RF14): el reporte semanal que se genera cada sábado.

Solo el administrador lo ve: tiene ingresos, gastos y comisiones.
"""

from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.usuarios.permissions import rol_requerido
from config.pdf import render_pdf

from . import reporte, semanas


def _sabado_pedido(request, hoy):
    """El sábado de ?semana=AAAA-MM-DD si es un sábado ya publicado; si no, el más reciente."""
    texto = request.GET.get("semana", "")
    try:
        pedido = date.fromisoformat(texto)
    except ValueError:
        return semanas.ultimo_publicado(hoy)
    return pedido if semanas.es_publicado(pedido, hoy) else semanas.ultimo_publicado(hoy)


def _contexto(request):
    hoy = timezone.localdate()
    sabado = _sabado_pedido(request, hoy)
    return {
        **reporte.generar(sabado),
        "sabado": sabado,
        "es_hoy": sabado == hoy,
        "es_ultimo": sabado == semanas.ultimo_publicado(hoy),
        "proximo_reporte": semanas.proximo_reporte(hoy),
        "semanas_disponibles": semanas.disponibles(12, hoy),
    }


@login_required
@rol_requerido("administrador")
def semanal(request):
    return render(request, "reportes/semanal.html", _contexto(request))


@login_required
@rol_requerido("administrador")
def semanal_pdf(request):
    contexto = _contexto(request)
    return render_pdf(request, "reportes/semanal_pdf.html", contexto,
                      f"reporte-semanal-{contexto['sabado'].isoformat()}")
