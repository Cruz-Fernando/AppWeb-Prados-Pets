"""Enlaces de WhatsApp (wa.me) con el mensaje ya escrito."""

import re
from urllib.parse import quote

from django.conf import settings


def enlace_whatsapp(telefono, mensaje):
    """Enlace wa.me con el mensaje listo. '' si el teléfono no sirve."""
    digitos = re.sub(r"\D", "", telefono or "")
    if len(digitos) < 7:
        return ""
    # Celular local (10 dígitos) → se antepone el indicativo del país.
    if len(digitos) == 10:
        digitos = getattr(settings, "WHATSAPP_INDICATIVO", "57") + digitos
    return f"https://wa.me/{digitos}?text={quote(mensaje)}"
