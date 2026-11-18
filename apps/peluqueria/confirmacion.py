"""
Confirmación de la cita de peluquería para el cliente (dueño de la mascota).

- El PDF se abre con un enlace firmado (no se puede adivinar ni cambiar el
  número de la cita) y no pide iniciar sesión, para que el cliente lo abra
  desde WhatsApp. Deja de funcionar DIAS_TRAS_LA_CITA días después de la cita.
- WhatsApp no permite adjuntar archivos desde un enlace wa.me, así que se
  envía un mensaje ya escrito con ese enlace.
- El PDF del cliente no muestra datos internos: ni observaciones del
  personal, ni comisión, ni teléfono o dirección del propietario.
"""

from datetime import timedelta

from django.core import signing
from django.urls import reverse
from django.utils import dateformat, timezone

from config.whatsapp import enlace_whatsapp

SALT = "peluqueria.confirmacion-cliente"
DIAS_TRAS_LA_CITA = 30

ANTES_DE_VENIR = [
    "Sácala a pasear antes para que haga sus necesidades.",
    "Evita darle comida abundante en las 2 horas previas.",
    "Tráela con correa o en guacal/transportadora.",
    "Cuéntanos si tiene piel sensible, alergias, heridas o algo que la estrese.",
]


def token_para(cita):
    # Sin fecha de creación: el enlace de una cita es siempre el mismo y
    # su vencimiento se cuenta desde la cita (enlace_vencido).
    return signing.Signer(salt=SALT).sign(str(cita.pk))


def cita_desde_token(token):
    """Número de la cita. Lanza signing.BadSignature si el enlace fue alterado."""
    valor = signing.Signer(salt=SALT).unsign(token)
    if not valor.isdigit():
        raise signing.BadSignature("Número de cita no válido")
    return int(valor)


def enlace_vencido(cita):
    return timezone.now() > cita.fecha_hora + timedelta(days=DIAS_TRAS_LA_CITA)


def url_publica(request, cita):
    return request.build_absolute_uri(reverse("peluqueria:confirmacion_cliente", args=[token_para(cita)]))


def codigo_reserva(cita):
    return f"PP-{cita.pk:05d}"


def nombre_corto(nombre):
    partes = (nombre or "").split()
    return partes[0] if partes else ""


def mensaje_whatsapp(cita, url, precio):
    mascota = cita.mascota.nombre if cita.mascota else cita.nombre_mascota
    dueno = cita.mascota.id_dueno.nombre_completo if cita.mascota else ""
    inicio = timezone.localtime(cita.fecha_hora)
    cuando = (f"{dateformat.format(inicio, 'l').capitalize()} {inicio.day} de "
              f"{dateformat.format(inicio, 'F').lower()} a las {dateformat.format(inicio, 'g:i a')}")
    saludo = f"¡Hola, {nombre_corto(dueno)}!" if nombre_corto(dueno) else "¡Hola!"
    return (
        f"{saludo} Te saludamos de Prados Pets 🐾\n\n"
        f"La cita de peluquería de *{mascota}* quedó confirmada:\n"
        f"📅 {cuando}\n"
        f"✂️ {cita.get_servicio_display()}\n"
        f"💳 Costo total: {precio}\n"
        f"🔖 Reserva {codigo_reserva(cita)}\n\n"
        f"Aquí puedes ver y descargar tu confirmación:\n{url}\n\n"
        "Si necesitas cambiar la hora, respóndenos por este chat. ¡Te esperamos!"
    )


def precio_texto(valor):
    """50000 → '$50.000 COP'."""
    if not valor:
        return "Por confirmar"
    return "$" + f"{valor:,.0f}".replace(",", ".") + " COP"


def enlace_whatsapp_cita(request, cita, precio=None):
    """Enlace wa.me al dueño con el mensaje y el PDF. '' si no hay teléfono."""
    if not cita.mascota or not cita.mascota.id_dueno.telefono:
        return ""
    precio = precio or precio_texto(cita.precio)
    return enlace_whatsapp(
        cita.mascota.id_dueno.telefono,
        mensaje_whatsapp(cita, url_publica(request, cita), precio),
    )


def proximo_bano(cita):
    """Fecha sugerida del siguiente baño (la misma regla de los recordatorios)."""
    if cita.servicio != "BANO" or not cita.intervalo_recordatorio_dias:
        return None
    return timezone.localdate(cita.fecha_hora) + timedelta(days=cita.intervalo_recordatorio_dias)
