"""
Indicaciones que se imprimen en el comprobante según el servicio agendado.
Son pautas generales; el médico puede dar instrucciones distintas en consulta.
"""

GENERALES = [
    "Llega 10 minutos antes de la hora agendada.",
    "Trae a tu mascota con correa o en guacal/transportadora.",
]

POR_SERVICIO = {
    "consulta_general": [
        "Trae el carné de vacunas y la fórmula de los medicamentos que esté tomando.",
        "Anota los síntomas: desde cuándo, cada cuánto y si ha comido normal.",
    ],
    "vacunacion": [
        "Trae el carné de vacunación.",
        "Tu mascota debe estar sana ese día (sin fiebre, vómito ni diarrea).",
        "Evita bañarla durante las 48 horas siguientes a la vacuna.",
    ],
    "desparasitacion": [
        "Trae el carné; allí registramos el producto y la próxima dosis.",
        "Si la pesaste hace poco, cuéntanos su peso: la dosis depende de él.",
    ],
    "sedacion": [
        "Ayuno de comida sólida de 8 horas antes de la cita.",
        "Puede tomar agua hasta 2 horas antes.",
        "Al terminar necesitará reposo y un acompañante para regresar a casa.",
    ],
    "cirugia": [
        "Ayuno de comida sólida de 8 a 12 horas; agua hasta 2 horas antes.",
        "Báñala días antes si lo necesita: después no podrá mojar la herida.",
        "Al ingresar firmarás el consentimiento informado.",
        "Trae una manta o cobija para el regreso.",
    ],
    "control": [
        "Trae la fórmula y los medicamentos que está tomando.",
        "Si usa collar isabelino, que llegue con él puesto.",
    ],
    "eutanasia": [
        "Puedes acompañar a tu mascota durante todo el proceso si lo deseas.",
        "Antes del procedimiento conversaremos contigo y firmarás la autorización.",
        "Pregúntanos por las opciones de cremación o despedida.",
    ],
    "peluqueria": [
        "Sácala a pasear antes para que haga sus necesidades.",
        "Avísanos si tiene piel sensible, alergias o le molesta algún producto.",
    ],
    "otro": [],
}


def recomendaciones_cita(tipo_servicio):
    return POR_SERVICIO.get(tipo_servicio, []) + GENERALES


RECOMENDACIONES_PELUQUERIA = [
    "Sácala a pasear antes de la cita para que haga sus necesidades.",
    "Evita darle comida abundante en las 2 horas previas.",
    "Avísanos si tiene piel sensible, alergias, heridas o le molesta algún producto.",
    "Trae a tu mascota con correa o en guacal/transportadora.",
]
