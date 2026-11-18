"""
Identidad de marca de Prados Pets: colores y datos de la clínica.

Se usa en los comprobantes PDF (y puede usarse en cualquier plantilla).
Los datos de contacto se leen de variables de entorno para no dejarlos
quemados en el código; si una no está definida, simplemente no se imprime.

    CLINICA_DIRECCION="Calle 10 # 5-23, Barrio X"
    CLINICA_TELEFONO="+57 300 000 0000"
    CLINICA_CORREO="contacto@pradospets.com"
    CLINICA_INSTAGRAM="@pradospets"
    CLINICA_WHATSAPP="+57 300 000 0000"      (si es distinto del teléfono)
    CLINICA_HORARIO="Lunes a sábado, 8:00 a. m. – 6:00 p. m."
    CLINICA_MEDIOS_PAGO="Efectivo, Nequi, Daviplata y transferencia"
"""

import os

# Colores tomados del logo (círculo morado) y del tema de la aplicación.
COLORES = {
    "primario": "#9B3BB8",      # morado del logo
    "primario_oscuro": "#5E1F7A",
    "violeta": "#7C3AED",       # acento de la aplicación
    "suave": "#F5EDFA",         # fondos claros en el PDF
    "borde": "#E4D2EE",
    "texto": "#1F1530",
    "gris": "#6B6280",
    "rosa": "#E2457E",          # acento ("Pets" del logo)
    "verde": "#16A34A",
}

CLINICA = {
    "nombre": "Prados Pets",
    "eslogan": "Clínica Veterinaria",
    "ciudad": os.environ.get("CLINICA_CIUDAD", "Cúcuta, Colombia"),
    "direccion": os.environ.get("CLINICA_DIRECCION", ""),
    "telefono": os.environ.get("CLINICA_TELEFONO", ""),
    "correo": os.environ.get("CLINICA_CORREO", ""),
    "instagram": os.environ.get("CLINICA_INSTAGRAM", ""),
    "whatsapp": os.environ.get("CLINICA_WHATSAPP", "") or os.environ.get("CLINICA_TELEFONO", ""),
    "horario": os.environ.get("CLINICA_HORARIO", ""),
    "medios_pago": os.environ.get("CLINICA_MEDIOS_PAGO", ""),
}


def contexto_marca():
    return {"marca": COLORES, "clinica": CLINICA}
