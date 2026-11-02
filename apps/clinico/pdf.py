"""Generación de PDF con xhtml2pdf (misma librería que el comprobante de citas)."""

import os
from io import BytesIO

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify


def _link_callback(uri, rel):
    """Traduce /static/... y /media/... a rutas del disco para que xhtml2pdf las lea."""
    static_url = settings.STATIC_URL if settings.STATIC_URL.startswith("/") else "/" + settings.STATIC_URL
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    media_url = media_url if media_url.startswith("/") else "/" + media_url

    if uri.startswith(static_url):
        ruta = finders.find(uri[len(static_url):])
        if not ruta and settings.STATIC_ROOT:
            ruta = os.path.join(settings.STATIC_ROOT, uri[len(static_url):])
        return ruta or uri
    if uri.startswith(media_url) and getattr(settings, "MEDIA_ROOT", None):
        return os.path.join(settings.MEDIA_ROOT, uri[len(media_url):])
    return uri


def render_pdf(request, plantilla, contexto, nombre_archivo, descargar=True):
    contexto = {**contexto, "fecha_generacion": timezone.localtime(), "generado_por": request.user}
    html = render_to_string(plantilla, contexto, request=request)
    try:
        from xhtml2pdf import pisa
    except ImportError:  # sin la librería: se muestra el HTML imprimible
        return HttpResponse(html)

    buffer = BytesIO()
    resultado = pisa.CreatePDF(html, dest=buffer, encoding="utf-8", link_callback=_link_callback)
    if resultado.err:
        return HttpResponse(html)

    respuesta = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    modo = "attachment" if descargar else "inline"
    respuesta["Content-Disposition"] = f'{modo}; filename="{slugify(nombre_archivo)}.pdf"'
    return respuesta
