"""
Catálogo de tipos de registro clínico.

Es la ÚNICA fuente de verdad de qué datos pide cada tipo de atención
(vacunación, cirugía, eutanasia...). A partir de aquí se construyen:
  - el formulario (forms.RegistroClinicoForm),
  - la vista de detalle y la línea de tiempo,
  - el PDF.

Los campos comunes (motivo, constantes vitales, diagnóstico, tratamiento...)
son columnas reales de RegistroClinico. Los campos propios de cada tipo se
guardan en RegistroClinico.detalle (JSON) con las claves definidas aquí.

Para agregar un dato nuevo a un tipo basta con añadir un Campo a su lista.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Campo:
    nombre: str
    etiqueta: str
    tipo: str = "text"          # text | textarea | int | decimal | date | time | choice | bool
    requerido: bool = False
    opciones: tuple = ()
    ayuda: str = ""
    ancho: str = "half"         # full | half | third
    grupo: str = ""             # subtítulo dentro de la sección propia del tipo
    placeholder: str = ""


@dataclass(frozen=True)
class TipoRegistro:
    clave: str
    nombre: str
    descripcion: str
    color: str                  # clase de color para la UI (ver clinico.css)
    icono: str                  # nombre de ícono (ver _iconos.html)
    campos: tuple = field(default_factory=tuple)
    usa_evaluacion: bool = True     # anamnesis / examen / diagnóstico / tratamiento
    titulo_motivo: str = "Motivo de la atención"


ASA = (
    ("I", "ASA I · Paciente sano"),
    ("II", "ASA II · Enfermedad sistémica leve"),
    ("III", "ASA III · Enfermedad sistémica grave"),
    ("IV", "ASA IV · Riesgo vital constante"),
    ("V", "ASA V · Moribundo"),
)

VIAS = (
    ("SC", "Subcutánea (SC)"),
    ("IM", "Intramuscular (IM)"),
    ("IV", "Intravenosa (IV)"),
    ("VO", "Oral (VO)"),
    ("IN", "Intranasal"),
    ("TOP", "Tópica / Spot-on"),
)


TIPOS = (
    TipoRegistro(
        clave="consulta_general",
        nombre="Consulta General",
        descripcion="Anamnesis, examen físico por sistemas, diagnóstico y plan.",
        color="violet",
        icono="estetoscopio",
        titulo_motivo="Motivo de consulta",
        campos=(
            Campo("examen_general", "Examen general / actitud", "textarea", ancho="full",
                  grupo="Examen físico por sistemas",
                  placeholder="Alerta, responsivo, hidratado..."),
            Campo("sistema_tegumentario", "Piel y anexos", "textarea", grupo="Examen físico por sistemas"),
            Campo("sistema_cardiovascular", "Cardiovascular", "textarea", grupo="Examen físico por sistemas"),
            Campo("sistema_respiratorio", "Respiratorio", "textarea", grupo="Examen físico por sistemas"),
            Campo("sistema_digestivo", "Digestivo", "textarea", grupo="Examen físico por sistemas"),
            Campo("sistema_genitourinario", "Genitourinario", "textarea", grupo="Examen físico por sistemas"),
            Campo("sistema_musculoesqueletico", "Musculoesquelético", "textarea", grupo="Examen físico por sistemas"),
            Campo("sistema_nervioso", "Nervioso", "textarea", grupo="Examen físico por sistemas"),
            Campo("ojos_oidos", "Ojos y oídos", "textarea", grupo="Examen físico por sistemas"),
            Campo("ganglios", "Ganglios linfáticos", "textarea", grupo="Examen físico por sistemas"),
            Campo("examenes_solicitados", "Exámenes complementarios solicitados", "textarea",
                  ancho="full", grupo="Plan diagnóstico",
                  placeholder="Hemograma, química sanguínea, coprológico, radiografía..."),
            Campo("pronostico", "Pronóstico", "choice", grupo="Plan diagnóstico", opciones=(
                ("favorable", "Favorable"), ("reservado", "Reservado"),
                ("desfavorable", "Desfavorable"), ("grave", "Grave"),
            )),
        ),
    ),
    TipoRegistro(
        clave="vacunacion",
        nombre="Vacunación",
        descripcion="Biológico aplicado, lote, vía y próxima dosis.",
        color="green",
        icono="jeringa",
        titulo_motivo="Motivo / plan vacunal",
        usa_evaluacion=False,
        campos=(
            Campo("vacuna", "Vacuna / biológico", requerido=True, ancho="full",
                  placeholder="Ej: Polivalente DHPPi+L, Antirrábica, Triple felina"),
            Campo("laboratorio", "Laboratorio", placeholder="Ej: Zoetis, MSD, Virbac"),
            Campo("lote", "Lote", requerido=True),
            Campo("vencimiento_lote", "Vencimiento del lote", "date"),
            Campo("dosis", "Dosis del esquema", "choice", requerido=True, opciones=(
                ("1", "1.ª dosis"), ("2", "2.ª dosis"), ("3", "3.ª dosis"),
                ("refuerzo", "Refuerzo anual"), ("unica", "Dosis única"),
            )),
            Campo("via", "Vía de aplicación", "choice", requerido=True, opciones=VIAS[:5]),
            Campo("sitio_aplicacion", "Sitio de aplicación", placeholder="Ej: región interescapular"),
            Campo("proxima_dosis", "Próxima dosis", "date",
                  ayuda="Se mostrará como recordatorio en la historia."),
            Campo("examen_previo_apto", "Examen previo: paciente apto para vacunar", "bool"),
            Campo("reacciones", "Reacciones adversas observadas", "textarea", ancho="full",
                  placeholder="Ninguna / edema local / letargia..."),
        ),
    ),
    TipoRegistro(
        clave="desparasitacion",
        nombre="Desparasitación",
        descripcion="Antiparasitario interno o externo, dosis y próxima aplicación.",
        color="amber",
        icono="escudo",
        titulo_motivo="Motivo / plan de desparasitación",
        usa_evaluacion=False,
        campos=(
            Campo("tipo_desparasitacion", "Tipo", "choice", requerido=True, opciones=(
                ("interna", "Interna"), ("externa", "Externa"), ("ambas", "Interna y externa"),
            )),
            Campo("producto", "Producto comercial", requerido=True,
                  placeholder="Ej: Drontal Plus, NexGard, Bravecto"),
            Campo("principio_activo", "Principio activo",
                  placeholder="Ej: Praziquantel + Pirantel + Febantel"),
            Campo("laboratorio", "Laboratorio"),
            Campo("lote", "Lote"),
            Campo("dosis", "Dosis administrada", requerido=True,
                  placeholder="Ej: 1 tableta (10 kg) · 2,5 mg/kg"),
            Campo("via", "Vía", "choice", requerido=True, opciones=(
                ("VO", "Oral"), ("TOP", "Tópica / Spot-on"), ("SC", "Subcutánea"),
                ("collar", "Collar"),
            )),
            Campo("proxima_aplicacion", "Próxima aplicación", "date"),
            Campo("peso_dosificacion", "Peso usado para dosificar (kg)", "decimal",
                  ayuda="Si difiere del peso registrado en constantes."),
        ),
    ),
    TipoRegistro(
        clave="sedacion",
        nombre="Sedación",
        descripcion="Protocolo farmacológico, monitoreo y recuperación.",
        color="sky",
        icono="luna",
        titulo_motivo="Procedimiento que requiere sedación",
        campos=(
            Campo("asa", "Riesgo anestésico (ASA)", "choice", requerido=True, opciones=ASA,
                  grupo="Valoración pre-sedación"),
            Campo("ayuno_horas", "Horas de ayuno", "int", grupo="Valoración pre-sedación"),
            Campo("consentimiento_firmado", "Consentimiento informado firmado", "bool",
                  grupo="Valoración pre-sedación"),
            Campo("protocolo", "Protocolo farmacológico", "textarea", requerido=True, ancho="full",
                  grupo="Protocolo",
                  placeholder="Fármaco – dosis (mg/kg) – vía – hora\nEj: Dexmedetomidina 5 µg/kg IM 10:05"),
            Campo("hora_inicio", "Hora de inicio", "time", grupo="Protocolo"),
            Campo("hora_fin", "Hora de recuperación", "time", grupo="Protocolo"),
            Campo("monitoreo", "Monitoreo intra-procedimiento", "textarea", ancho="full",
                  grupo="Protocolo", placeholder="FC, FR, SpO₂, temperatura, reflejos..."),
            Campo("reversion", "Reversión", grupo="Recuperación",
                  placeholder="Ej: Atipamezol 50 µg/kg IM"),
            Campo("recuperacion", "Calidad de la recuperación", "choice", grupo="Recuperación",
                  opciones=(("normal", "Sin complicaciones"), ("prolongada", "Prolongada"),
                            ("complicada", "Con complicaciones"))),
            Campo("complicaciones", "Complicaciones", "textarea", ancho="full", grupo="Recuperación"),
        ),
    ),
    TipoRegistro(
        clave="cirugia",
        nombre="Cirugía",
        descripcion="Reporte quirúrgico: anestesia, técnica, hallazgos y postoperatorio.",
        color="rose",
        icono="bisturi",
        titulo_motivo="Indicación quirúrgica",
        campos=(
            Campo("procedimiento", "Procedimiento quirúrgico", requerido=True, ancho="full",
                  grupo="Datos de la cirugía", placeholder="Ej: Ovariohisterectomía"),
            Campo("caracter", "Carácter", "choice", requerido=True, grupo="Datos de la cirugía",
                  opciones=(("electiva", "Electiva"), ("urgencia", "Urgencia"))),
            Campo("asa", "Riesgo anestésico (ASA)", "choice", requerido=True, opciones=ASA,
                  grupo="Datos de la cirugía"),
            Campo("cirujano", "Cirujano principal", grupo="Equipo"),
            Campo("ayudante", "Ayudante / anestesista", grupo="Equipo"),
            Campo("ayuno_horas", "Horas de ayuno", "int", grupo="Equipo"),
            Campo("consentimiento_firmado", "Consentimiento informado firmado", "bool",
                  requerido=True, grupo="Equipo",
                  ayuda="Obligatorio para registrar una cirugía."),
            Campo("premedicacion", "Premedicación", "textarea", grupo="Anestesia"),
            Campo("induccion", "Inducción", "textarea", grupo="Anestesia"),
            Campo("mantenimiento", "Mantenimiento", "choice", grupo="Anestesia", opciones=(
                ("inhalatoria", "Inhalatoria (isoflurano/sevoflurano)"),
                ("tiva", "Intravenosa total (TIVA)"),
                ("local", "Local / regional"),
            )),
            Campo("hora_inicio", "Hora de inicio", "time", grupo="Anestesia"),
            Campo("hora_fin", "Hora de finalización", "time", grupo="Anestesia"),
            Campo("tecnica", "Técnica quirúrgica y hallazgos", "textarea", requerido=True,
                  ancho="full", grupo="Reporte quirúrgico"),
            Campo("sutura", "Material de sutura", grupo="Reporte quirúrgico",
                  placeholder="Ej: Poliglactina 2-0, Nylon 3-0"),
            Campo("muestras", "Muestras enviadas a patología", grupo="Reporte quirúrgico"),
            Campo("complicaciones", "Complicaciones", "textarea", ancho="full",
                  grupo="Reporte quirúrgico"),
            Campo("analgesia_postop", "Analgesia y cuidados postoperatorios", "textarea",
                  ancho="full", grupo="Postoperatorio"),
            Campo("retiro_puntos", "Fecha estimada de retiro de puntos", "date", grupo="Postoperatorio"),
        ),
    ),
    TipoRegistro(
        clave="eutanasia",
        nombre="Eutanasia",
        descripcion="Autorización del propietario, protocolo y disposición del cuerpo.",
        color="slate",
        icono="corazon",
        titulo_motivo="Justificación clínica",
        usa_evaluacion=False,
        campos=(
            Campo("diagnostico_base", "Diagnóstico que fundamenta la decisión", "textarea",
                  requerido=True, ancho="full", grupo="Fundamento"),
            Campo("consentimiento_firmado", "Consentimiento de eutanasia firmado por el propietario",
                  "bool", requerido=True, grupo="Autorización",
                  ayuda="Obligatorio. Adjunta el documento firmado."),
            Campo("autorizado_por", "Nombre de quien autoriza", requerido=True, grupo="Autorización"),
            Campo("documento_autorizante", "Documento de identidad", requerido=True, grupo="Autorización"),
            Campo("parentesco", "Relación con el paciente", grupo="Autorización",
                  placeholder="Propietario, familiar autorizado..."),
            Campo("sedacion_previa", "Sedación / anestesia previa", "textarea", requerido=True,
                  grupo="Procedimiento"),
            Campo("agente", "Agente eutanásico, dosis y vía", "textarea", requerido=True,
                  grupo="Procedimiento", placeholder="Ej: Pentobarbital sódico 100 mg/kg IV"),
            Campo("hora_fallecimiento", "Hora de fallecimiento", "time", requerido=True,
                  grupo="Procedimiento"),
            Campo("confirmacion", "Confirmación de muerte", "textarea", requerido=True,
                  grupo="Procedimiento",
                  placeholder="Ausencia de latido a la auscultación, apnea, reflejo corneal ausente..."),
            Campo("disposicion", "Disposición del cuerpo", "choice", requerido=True,
                  grupo="Disposición final", opciones=(
                      ("cremacion_individual", "Cremación individual"),
                      ("cremacion_colectiva", "Cremación colectiva"),
                      ("entrega_propietario", "Entrega al propietario"),
                      ("otro", "Otro"),
                  )),
            Campo("detalle_disposicion", "Detalle (empresa, n.° de orden...)", grupo="Disposición final"),
        ),
    ),
    TipoRegistro(
        clave="control",
        nombre="Control Post-Operatorio",
        descripcion="Evolución de la herida, dolor y retiro de puntos.",
        color="teal",
        icono="check",
        titulo_motivo="Motivo del control",
        campos=(
            Campo("cirugia_relacionada", "Cirugía relacionada", "choice", ancho="full",
                  ayuda="Se listan las cirugías registradas de esta mascota."),
            Campo("dias_postoperatorio", "Días de postoperatorio", "int"),
            Campo("estado_herida", "Estado de la herida", "choice", requerido=True, opciones=(
                ("buena", "Buena cicatrización"), ("eritema", "Eritema"), ("edema", "Edema"),
                ("secrecion", "Secreción / signos de infección"), ("dehiscencia", "Dehiscencia"),
            )),
            Campo("dolor", "Dolor (escala 0–4)", "choice", opciones=(
                ("0", "0 · Sin dolor"), ("1", "1 · Leve"), ("2", "2 · Moderado"),
                ("3", "3 · Severo"), ("4", "4 · Insoportable"),
            )),
            Campo("retiro_puntos", "Se retiraron los puntos", "bool"),
            Campo("evolucion", "Evolución", "choice", requerido=True, opciones=(
                ("favorable", "Favorable"), ("estable", "Estable"), ("desfavorable", "Desfavorable"),
            )),
        ),
    ),
    TipoRegistro(
        clave="otro",
        nombre="Otro procedimiento",
        descripcion="Cualquier atención que no encaje en las anteriores.",
        color="gray",
        icono="mas",
        campos=(
            Campo("procedimiento", "Procedimiento realizado", requerido=True, ancho="full",
                  placeholder="Ej: Limpieza de oídos, curación, toma de muestras..."),
        ),
    ),
)

TIPOS_POR_CLAVE = {t.clave: t for t in TIPOS}
TIPO_CHOICES = [(t.clave, t.nombre) for t in TIPOS]


def obtener_tipo(clave):
    return TIPOS_POR_CLAVE.get(clave)


def grupos_de(tipo):
    """Agrupa los campos de un tipo por su subtítulo, conservando el orden."""
    grupos = []
    indice = {}
    for campo in tipo.campos:
        if campo.grupo not in indice:
            indice[campo.grupo] = len(grupos)
            grupos.append((campo.grupo, []))
        grupos[indice[campo.grupo]][1].append(campo)
    return grupos
