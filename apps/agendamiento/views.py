from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.directorio.models import Mascota
from apps.peluqueria.models import CitaPeluqueria

from . import calendario as cal
from .forms import CitaForm
from .models import Cita


@login_required
def agendar_cita(request):
    """HU06 / PB-08: Agendar consultas médicas con validación de horario de veterinario."""
    if request.method == "POST":
        form = CitaForm(request.POST)
        if form.is_valid():
            try:
                cita = form.save()
            except IntegrityError:
                form.add_error(None, "Ya existe una cita para ese veterinario en esa fecha y hora.")
            else:
                messages.success(request, "¡Cita agendada con éxito! El comprobante PDF se está descargando.")
                return redirect(f"{reverse('agendamiento:agendar_cita')}?descargar={cita.pk}")
    else:
        form = CitaForm()

    # Tras agendar, la página se recarga (con el mensaje visible) y el
    # navegador descarga el comprobante a partir de este enlace.
    descargar_url = None
    descargar = request.GET.get("descargar", "")
    if request.method == "GET" and descargar.isdigit() and Cita.objects.filter(pk=int(descargar)).exists():
        descargar_url = reverse("agendamiento:cita_pdf", args=[int(descargar)])
    return render(request, "agendamiento/cita_form.html", {"form": form, "descargar_url": descargar_url})


@login_required
def buscar_mascotas_ajax(request):
    q = request.GET.get("q", "").strip()
    resultados = []
    if len(q) >= 2:
        mascotas = Mascota.objects.select_related("id_dueno").filter(
            Q(nombre__icontains=q)
            | Q(id_dueno__nombre_completo__icontains=q)
            | Q(id_dueno__telefono__icontains=q)
            | Q(codigo_mascota__icontains=q)
        )[:10]
        for m in mascotas:
            resultados.append({
                "id": m.id_mascota,
                "nombre_mascota": m.nombre,
                "especie": m.get_especie_display(),
                "raza": m.raza or "-",
                "codigo": m.codigo_mascota,
                "dueno": m.id_dueno.nombre_completo,
                "telefono": m.id_dueno.telefono,
                "label": f"{m.nombre} ({m.codigo_mascota}) — {m.id_dueno.nombre_completo}",
            })
    return JsonResponse({"resultados": resultados})


@login_required
def cita_pdf(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    contexto = {
        "cita": cita,
        "mascota": cita.mascota,
        "dueno": cita.mascota.id_dueno,
        "veterinario": cita.veterinario,
        "tipo_servicio_display": cita.get_tipo_servicio_display(),
        "fecha_generacion": timezone.now(),
    }
    html_str = render_to_string("agendamiento/cita_pdf.html", contexto, request=request)
    try:
        from io import BytesIO
        from xhtml2pdf import pisa
        
        buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_str, dest=buffer)
        if pisa_status.err:
            return HttpResponse(html_str)
            
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="cita_{cita.pk}_{cita.mascota.nombre}.pdf"'
        return response
    except ImportError:
        return HttpResponse(html_str)
    MOTIVO_CANCELACION_MAX = 255


@login_required
@require_POST
def cancelar_cita(request, pk):
    """
    RF05 / PB-11: Cancelación de citas de consulta (solo POST).

    La cita pasa a estado «cancelada» y conserva el motivo. Al quedar fuera
    de la restricción de unicidad y de las validaciones de cruce de horario,
    su franja queda libre para volver a agendarse.
    """
    cita = get_object_or_404(Cita, pk=pk)
    destino = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        destino = f"{reverse('agendamiento:calendario')}?fecha={cita.fecha.isoformat()}"

    motivo = request.POST.get("motivo_cancelacion", "").strip()

    if cita.estado == "cancelada":
        messages.info(request, "Esta cita ya estaba cancelada.")
    elif cita.estado == "atendida":
        messages.error(request, "No se puede cancelar una cita que ya fue atendida.")
    elif not motivo:
        messages.error(request, "Debes indicar el motivo de la cancelación.")
    elif len(motivo) > MOTIVO_CANCELACION_MAX:
        messages.error(
            request,
            f"El motivo no puede superar los {MOTIVO_CANCELACION_MAX} caracteres.",
        )
    else:
        cita.estado = "cancelada"
        cita.motivo_cancelacion = motivo
        cita.save(update_fields=["estado", "motivo_cancelacion"])
        messages.success(
            request,
            f"Cita de {cita.mascota.nombre} cancelada. El horario quedó disponible.",
        )
    return redirect(destino)




@login_required
def calendario(request):
    """HU08: Calendario visual diario y semanal."""
    vista = request.GET.get("vista", "semana")
    if vista not in ("semana", "dia"):
        vista = "semana"

    hoy = timezone.localdate()
    try:
        fecha = date.fromisoformat(request.GET.get("fecha", ""))
    except ValueError:
        fecha = hoy

    if vista == "dia":
        fechas = [fecha]
        paso = timedelta(days=1)
    else:
        lunes = cal.inicio_semana(fecha)
        fechas = [lunes + timedelta(days=i) for i in range(7)]
        paso = timedelta(days=7)

    desde, hasta = fechas[0], fechas[-1]
    citas = Cita.objects.select_related("mascota", "veterinario").filter(fecha__range=(desde, hasta))
    citas_pelu = CitaPeluqueria.objects.filter(fecha_hora__date__range=(desde, hasta))

    eventos = cal.eventos_desde_citas(citas) + cal.eventos_desde_peluqueria(citas_pelu)
    hora_inicio, hora_fin = cal.rango_horas(eventos)
    dias = cal.construir_dias(eventos, fechas, hora_inicio, hora_fin)

    direccion = request.GET.get("dir", "")
    if direccion not in ("prev", "next"):
        direccion = ""

    activos = [e for e in eventos if not e.cancelada]
    contexto = {
        "direccion": direccion,
        "hora_inicio": hora_inicio,
        "hora_fin": hora_fin,
        "total_citas": len(activos),
        "total_canceladas": len(eventos) - len(activos),
        "vista": vista,
        "fecha": fecha,
        "dias": dias,
        "horas": list(range(hora_inicio, hora_fin)),
        "alto_grilla": (hora_fin - hora_inicio) * 64,
        "titulo_rango": cal.titulo_rango(vista, fechas),
        "fecha_anterior": (fecha - paso).isoformat(),
        "fecha_siguiente": (fecha + paso).isoformat(),
        "hoy": hoy.isoformat(),
        "total_consultas": sum(1 for e in activos if e.categoria == cal.CATEGORIA_CONSULTA),
        "total_peluqueria": sum(1 for e in activos if e.categoria == cal.CATEGORIA_PELUQUERIA),
    }
    return render(request, "agendamiento/calendario.html", contexto)
