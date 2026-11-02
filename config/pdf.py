"""Utilidades comunes para generar PDF con xhtml2pdf y la marca de Prados Pets."""

import os
from io import BytesIO

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from .marca import contexto_marca


def link_callback(uri, rel):
    """Convierte /static/... y /media/... en rutas del disco para que xhtml2pdf cargue imágenes."""
    static_url = "/" + settings.STATIC_URL.lstrip("/")
    media_url = "/" + getattr(settings, "MEDIA_URL", "media/").lstrip("/")

    if uri.startswith(static_url):
        relativa = uri[len(static_url):]
        ruta = finders.find(relativa)
        if not ruta and settings.STATIC_ROOT:
            ruta = os.path.join(settings.STATIC_ROOT, relativa)
        return ruta or uri
    if uri.startswith(media_url) and getattr(settings, "MEDIA_ROOT", None):
        return os.path.join(settings.MEDIA_ROOT, uri[len(media_url):])
    return uri


def render_pdf(request, plantilla, contexto, nombre_archivo, descargar=True):
    """
    Renderiza `plantilla` como PDF. Si xhtml2pdf falla, devuelve el HTML
    (que tiene botón de imprimir) para que el usuario no se quede sin comprobante.
    """
    contexto = {**contexto_marca(), "fecha_generacion": timezone.localtime(), **contexto}
    html = render_to_string(plantilla, contexto, request=request)
    try:
        from xhtml2pdf import pisa
    except ImportError:
        return HttpResponse(html)

    buffer = BytesIO()
    resultado = pisa.CreatePDF(html, dest=buffer, encoding="utf-8", link_callback=link_callback)
    if resultado.err:
        return HttpResponse(html)

    respuesta = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    modo = "attachment" if descargar else "inline"
    respuesta["Content-Disposition"] = f'{modo}; filename="{nombre_archivo}.pdf"'
    return respuesta
