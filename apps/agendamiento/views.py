from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from apps.directorio.models import Mascota
from apps.peluqueria.models import CitaPeluqueria

from . import calendario as cal
from .forms import CitaForm
from .models import Cita


@login_required
def agendar_cita(request):
    """HU06: Agendar consultas médicas."""
    if request.method == "POST":
        form = CitaForm(request.POST)
        if form.is_valid():
            try:
                cita = form.save()
            except IntegrityError:
                form.add_error(None, "Ya existe una cita para ese veterinario en esa fecha y hora.")
            else:
                messages.success(request, "¡Cita agendada con éxito!")
                return redirect("agendamiento:cita_pdf", pk=cita.pk)
    else:
        form = CitaForm()
    return render(request, "agendamiento/cita_form.html", {"form": form})


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
        from weasyprint import HTML as WP_HTML
        pdf_bytes = WP_HTML(string=html_str, base_url=request.build_absolute_uri("/")).write_pdf()
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="cita_{cita.pk}_{cita.mascota.nombre}.pdf"'
        return response
    except ImportError:
        return HttpResponse(html_str)


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
