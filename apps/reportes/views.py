"""
Reportes (PB-20 / RF14): por día, semana y mes.

    /reportes/?periodo=dia|semana|mes&fecha=AAAA-MM-DD
    /reportes/?semana=AAAA-MM-DD        (enlaces de antes: la semana de ese sábado)

Sin periodo se muestra la semana, como antes. Un periodo que todavía no se
puede ver (futuro, o la semana antes de su sábado) muestra el más reciente
de ese tipo. Solo el administrador los ve: tienen ingresos, gastos y comisiones.
"""

from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.usuarios.permissions import rol_requerido
from config.pdf import render_pdf

from . import periodos, reporte, semanas
from .periodos import SEMANA, Periodo


def _fecha(texto):
    try:
        return date.fromisoformat(texto or "")
    except ValueError:
        return None


def _sabado_pedido(request, hoy):
    """El sábado de ?semana=AAAA-MM-DD si es un sábado ya publicado; si no, el más reciente."""
    pedido = _fecha(request.GET.get("semana"))
    if pedido and semanas.es_publicado(pedido, hoy):
        return pedido
    return semanas.ultimo_publicado(hoy)


def _periodo_pedido(request, hoy):
    if "semana" in request.GET and "periodo" not in request.GET:
        return Periodo.de(SEMANA, _sabado_pedido(request, hoy))
    tipo = request.GET.get("periodo", SEMANA)
    if tipo not in periodos.TIPOS:
        tipo = SEMANA
    fecha = _fecha(request.GET.get("fecha"))
    if fecha is None:
        return periodos.ultimo_valido(tipo, hoy)
    periodo = Periodo.de(tipo, fecha)
    return periodo if periodo.es_valido(hoy) else periodos.ultimo_valido(tipo, hoy)


def _contexto(request):
    hoy = timezone.localdate()
    periodo = _periodo_pedido(request, hoy)
    siguiente = periodo.siguiente()
    # Fecha de referencia al cambiar de pestaña (Día / Semana / Mes): el último
    # día del periodo actual que ya pasó.
    referencia = min(periodo.hasta, hoy)
    return {
        **reporte.generar(periodo),
        "hoy": hoy,
        "sabado": periodo.sabado,
        "en_curso": periodo.en_curso(hoy),
        "es_hoy": periodo.tipo == SEMANA and periodo.hasta == hoy,
        "es_ultimo": periodo == periodos.ultimo_valido(periodo.tipo, hoy),
        "proximo_reporte": semanas.proximo_reporte(hoy),
        "anterior": periodo.anterior(),
        "siguiente": siguiente if siguiente.es_valido(hoy) else None,
        "pestanas": [{"tipo": tipo, "nombre": periodos.TEXTOS[tipo]["pestana"], "activa": tipo == periodo.tipo}
                     for tipo in periodos.TIPOS],
        "referencia": referencia,
    }


@login_required
@rol_requerido("administrador")
def semanal(request):
    """Pantalla del reporte (conserva el nombre de antes de PB-20 para no romper enlaces)."""
    return render(request, "reportes/reporte.html", _contexto(request))


@login_required
@rol_requerido("administrador")
def semanal_pdf(request):
    contexto = _contexto(request)
    return render_pdf(request, "reportes/reporte_pdf.html", contexto, contexto["periodo"].nombre_archivo)
