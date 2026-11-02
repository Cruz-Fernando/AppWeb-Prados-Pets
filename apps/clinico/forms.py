from datetime import date, time
from decimal import Decimal

from django import forms
from django.utils import timezone

from apps.directorio.models import Mascota

from .models import (
    ConsultaMedica,
    EvolucionHospitalaria,
    Hospitalizacion,
    RegistroClinico,
)
from .registros import grupos_de

INPUT = "cl-input"


def _estilizar(form):
    """Aplica la clase visual del módulo a todos los widgets."""
    for f in form.fields.values():
        # Opción vacía en español y uniforme en todos los selects
        if isinstance(f, forms.ChoiceField) and not isinstance(f, forms.ModelChoiceField):
            opciones = [c for c in f.choices if c[0] not in ("", None)]
            if not f.required or any(c[0] in ("", None) for c in f.choices):
                f.choices = [("", "Seleccionar…")] + opciones
        w = f.widget
        if isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault("class", "cl-check")
        else:
            w.attrs["class"] = (w.attrs.get("class", "") + " " + INPUT).strip()
        if isinstance(w, (forms.DateInput, forms.DateTimeInput, forms.TimeInput)):
            w.attrs.setdefault("style", "color-scheme: dark;")


class ConsultaMedicaForm(forms.ModelForm):
    """Formulario del formato anterior de consulta (se conserva por compatibilidad)."""

    class Meta:
        model = ConsultaMedica
        fields = [
            "anamnesis", "peso", "temperatura", "frecuencia_cardiaca", "frecuencia_respiratoria",
            "examen_general", "sistema_tegumentario", "sistema_cardiovascular",
            "sistema_respiratorio", "sistema_digestivo", "sistema_genitourinario",
            "sistema_musculoesqueletico", "sistema_nervioso", "sistema_linfatico",
        ]


# ---------------------------------------------------------------------------
# Registro clínico (todos los tipos)
# ---------------------------------------------------------------------------

CAMPOS_EVALUACION = [
    "anamnesis", "diagnostico_presuntivo", "diagnostico_definitivo",
    "tratamiento", "prescripcion",
]


class RegistroClinicoForm(forms.ModelForm):
    PREFIJO = "d_"

    class Meta:
        model = RegistroClinico
        fields = [
            "fecha_atencion", "hospitalizacion", "motivo", "anamnesis",
            "peso", "temperatura", "frecuencia_cardiaca", "frecuencia_respiratoria",
            "tllc", "mucosas", "condicion_corporal", "hidratacion",
            "diagnostico_presuntivo", "diagnostico_definitivo", "tratamiento",
            "prescripcion", "recomendaciones", "proximo_control", "observaciones",
            "adjunto",
        ]
        widgets = {
            "fecha_atencion": forms.DateTimeInput(attrs={"type": "datetime-local"},
                                                  format="%Y-%m-%dT%H:%M"),
            "proximo_control": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "anamnesis": forms.Textarea(attrs={"rows": 3, "placeholder":
                                               "Evolución, antecedentes, alimentación, vacunas previas..."}),
            "peso": forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "placeholder": "kg"}),
            "temperatura": forms.NumberInput(attrs={"step": "0.1", "min": "30", "max": "45",
                                                    "placeholder": "°C"}),
            "frecuencia_cardiaca": forms.NumberInput(attrs={"min": "0", "placeholder": "lpm"}),
            "frecuencia_respiratoria": forms.NumberInput(attrs={"min": "0", "placeholder": "rpm"}),
            "tllc": forms.NumberInput(attrs={"step": "0.5", "min": "0", "placeholder": "seg"}),
            "diagnostico_presuntivo": forms.Textarea(attrs={"rows": 2}),
            "diagnostico_definitivo": forms.Textarea(attrs={"rows": 2}),
            "tratamiento": forms.Textarea(attrs={"rows": 3, "placeholder":
                                                 "Procedimientos y medicamentos aplicados en clínica"}),
            "prescripcion": forms.Textarea(attrs={"rows": 3, "placeholder":
                                                  "Medicamento – dosis – frecuencia – duración"}),
            "recomendaciones": forms.Textarea(attrs={"rows": 2}),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, tipo, mascota, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo = tipo
        self.mascota = mascota

        self.fields["fecha_atencion"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]
        if not self.instance.pk:
            self.initial.setdefault("fecha_atencion", timezone.localtime().replace(second=0, microsecond=0))
            if mascota.peso:
                self.initial.setdefault("peso", mascota.peso)

        self.fields["motivo"].label = tipo.titulo_motivo
        if tipo.clave == "otro":
            self.fields["motivo"].required = False

        if not tipo.usa_evaluacion:
            for nombre in CAMPOS_EVALUACION:
                self.fields.pop(nombre, None)

        hosp = self.fields["hospitalizacion"]
        hosp.queryset = Hospitalizacion.objects.filter(mascota=mascota).order_by("-fecha_ingreso")
        hosp.empty_label = "No aplica"
        hosp.label_from_instance = lambda h: f"{h.numero} · {h.motivo} ({h.fecha_ingreso:%d/%m/%Y})"
        if not hosp.queryset.exists():
            self.fields.pop("hospitalizacion")

        # Campos propios del tipo
        detalle = self.instance.detalle or {}
        for campo in tipo.campos:
            nombre = self.PREFIJO + campo.nombre
            self.fields[nombre] = self._crear_campo(campo)
            if campo.nombre in detalle:
                self.initial[nombre] = self._a_python(campo, detalle[campo.nombre])

        _estilizar(self)

    # -- construcción de campos dinámicos --------------------------------
    def _crear_campo(self, c):
        comunes = {"label": c.etiqueta, "required": c.requerido, "help_text": c.ayuda}
        attrs = {"placeholder": c.placeholder} if c.placeholder else {}

        if c.tipo == "textarea":
            return forms.CharField(widget=forms.Textarea(attrs={"rows": 2, **attrs}), **comunes)
        if c.tipo == "int":
            return forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs=attrs), **comunes)
        if c.tipo == "decimal":
            return forms.DecimalField(min_value=0, decimal_places=2,
                                      widget=forms.NumberInput(attrs={"step": "0.01", **attrs}),
                                      **comunes)
        if c.tipo == "date":
            return forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
                                   **comunes)
        if c.tipo == "time":
            return forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
                                   **comunes)
        if c.tipo == "bool":
            return forms.BooleanField(**comunes)
        if c.tipo == "choice":
            opciones = list(c.opciones)
            if c.nombre == "cirugia_relacionada":
                cirugias = RegistroClinico.objects.filter(
                    mascota=self.mascota, tipo="cirugia", anulado=False,
                ).order_by("-fecha_atencion")
                opciones = [
                    (str(r.pk), f"{r.numero} · {r.detalle.get('procedimiento', 'Cirugía')} "
                                f"({r.fecha_atencion:%d/%m/%Y})")
                    for r in cirugias
                ]
            return forms.ChoiceField(choices=[("", "Seleccionar…")] + opciones, **comunes)
        return forms.CharField(max_length=255, widget=forms.TextInput(attrs=attrs), **comunes)

    @staticmethod
    def _a_python(campo, valor):
        if valor in (None, ""):
            return valor
        try:
            if campo.tipo == "date":
                return date.fromisoformat(valor)
            if campo.tipo == "time":
                return time.fromisoformat(valor)
            if campo.tipo == "decimal":
                return Decimal(str(valor))
        except (TypeError, ValueError):
            return valor
        return valor

    @staticmethod
    def _a_json(valor):
        if isinstance(valor, (date, time)):
            return valor.isoformat(timespec="minutes") if isinstance(valor, time) else valor.isoformat()
        if isinstance(valor, Decimal):
            return str(valor)
        return valor

    # -- agrupación para la plantilla ------------------------------------
    def grupos_especificos(self):
        """[(titulo, [BoundField...]), ...] para pintar la sección propia del tipo."""
        return [
            (titulo, [(self[self.PREFIJO + c.nombre], c) for c in campos])
            for titulo, campos in grupos_de(self.tipo)
        ]

    def save(self, commit=True):
        registro = super().save(commit=False)
        registro.tipo = self.tipo.clave
        registro.mascota = self.mascota
        registro.detalle = {
            c.nombre: self._a_json(self.cleaned_data.get(self.PREFIJO + c.nombre))
            for c in self.tipo.campos
            if self.cleaned_data.get(self.PREFIJO + c.nombre) not in (None, "")
        }
        if self.tipo.clave == "otro" and not registro.motivo:
            registro.motivo = registro.detalle.get("procedimiento", "Otro procedimiento")[:255]
        if commit:
            registro.save()
        return registro


class AnularRegistroForm(forms.Form):
    motivo_anulacion = forms.CharField(
        label="Motivo de la anulación", max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Ej: registrado en la mascota equivocada"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _estilizar(self)


# ---------------------------------------------------------------------------
# Hospitalización
# ---------------------------------------------------------------------------

class HospitalizacionForm(forms.ModelForm):
    class Meta:
        model = Hospitalizacion
        fields = [
            'mascota', 'motivo', 'area', 'pronostico',
            'peso_actual', 'temperatura', 'frecuencia_cardiaca', 'frecuencia_respiratoria', 'mucosas',
            'diagnostico_presuntivo', 'tratamiento_inicial', 'observaciones',
            'documento_consentimiento', 'examenes_adjuntos',
        ]
        widgets = {
            'motivo': forms.TextInput(attrs={'placeholder': 'Ej. Gastroenteritis hemorrágica, trauma...'}),
            'area': forms.TextInput(attrs={'placeholder': 'Ej. Jaula 3 · Aislamiento'}),
            'peso_actual': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': 'kg'}),
            'temperatura': forms.NumberInput(attrs={'step': '0.1', 'placeholder': '°C'}),
            'frecuencia_cardiaca': forms.NumberInput(attrs={'min': '0', 'placeholder': 'lpm'}),
            'frecuencia_respiratoria': forms.NumberInput(attrs={'min': '0', 'placeholder': 'rpm'}),
            'mucosas': forms.TextInput(attrs={'placeholder': 'Ej. Rosadas, TLLC < 2 s'}),
            'diagnostico_presuntivo': forms.Textarea(attrs={'rows': 3}),
            'tratamiento_inicial': forms.Textarea(attrs={'rows': 3, 'placeholder':
                                                         'Fluidoterapia, medicamentos, dieta, monitoreo...'}),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'mascota': 'Paciente',
            'motivo': 'Motivo principal de ingreso',
            'mucosas': 'Estado de mucosas y TLLC',
            'tratamiento_inicial': 'Plan de tratamiento inicial',
            'documento_consentimiento': 'Consentimiento informado firmado',
            'examenes_adjuntos': 'Exámenes clínicos / laboratorio',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        internadas = Hospitalizacion.objects.filter(estado='ACTIVO').values('mascota_id')
        campo = self.fields['mascota']
        campo.queryset = (Mascota.objects.select_related('id_dueno')
                          .exclude(id_mascota__in=internadas).order_by('nombre'))
        campo.label_from_instance = lambda m: f"{m.nombre} · {m.get_especie_display()} — {m.id_dueno.nombre_completo}"
        campo.empty_label = "Seleccionar paciente…"
        _estilizar(self)


class EvolucionForm(forms.ModelForm):
    class Meta:
        model = EvolucionHospitalaria
        fields = [
            'fecha', 'estado_general', 'peso', 'temperatura', 'frecuencia_cardiaca',
            'frecuencia_respiratoria', 'mucosas', 'apetito', 'orina', 'defeca', 'vomito',
            'fluidoterapia', 'medicamentos', 'observaciones',
        ]
        widgets = {
            'fecha': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'peso': forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'kg'}),
            'temperatura': forms.NumberInput(attrs={'step': '0.1', 'placeholder': '°C'}),
            'frecuencia_cardiaca': forms.NumberInput(attrs={'placeholder': 'lpm'}),
            'frecuencia_respiratoria': forms.NumberInput(attrs={'placeholder': 'rpm'}),
            'fluidoterapia': forms.TextInput(attrs={'placeholder': 'Ej. Lactato de Ringer 40 ml/h'}),
            'medicamentos': forms.Textarea(attrs={'rows': 2, 'placeholder':
                                                  'Medicamento – dosis – vía – hora'}),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M']
        self.initial.setdefault('fecha', timezone.localtime().replace(second=0, microsecond=0))
        _estilizar(self)


class AltaForm(forms.ModelForm):
    class Meta:
        model = Hospitalizacion
        fields = ['condicion_alta', 'resumen_alta', 'indicaciones_alta', 'proximo_control']
        widgets = {
            'resumen_alta': forms.Textarea(attrs={'rows': 4, 'placeholder':
                                                  'Evolución durante la estancia, tratamientos y resultados'}),
            'indicaciones_alta': forms.Textarea(attrs={'rows': 4, 'placeholder':
                                                       'Medicación en casa, dieta, cuidados, signos de alarma'}),
            'proximo_control': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['condicion_alta'].required = True
        self.fields['resumen_alta'].required = True
        _estilizar(self)
