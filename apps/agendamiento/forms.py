from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Cita


class CitaForm(forms.ModelForm):
    """
    HU06-fix:
      - buscar_mascota: campo de texto libre visible; el id real va en
        un HiddenInput que el JS rellena tras elegir del dropdown AJAX.
      - tipo_servicio: Select con los choices del modelo.
      - fecha: atributo min=hoy para bloqueo en el navegador.
    """

    buscar_mascota = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Escribe nombre de la mascota o teléfono del dueño…",
            "autocomplete": "off",
            "id": "buscar_mascota_input",
        }),
        label="Buscar mascota",
    )

    class Meta:
        model = Cita
        fields = ["mascota", "veterinario", "tipo_servicio", "fecha", "hora_inicio", "hora_fin"]
        widgets = {
            "mascota": forms.HiddenInput(attrs={"id": "id_mascota_hidden"}),
            "veterinario": forms.Select(attrs={"class": "form-control"}),
            "tipo_servicio": forms.Select(attrs={"class": "form-control"}),
            "fecha": forms.DateInput(attrs={"type": "date", "class": "form-control", "id": "id_fecha"}),
            "hora_inicio": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "hora_fin": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha"].widget.attrs["min"] = timezone.now().date().isoformat()
        self.fields["mascota"].required = True

    def clean_fecha(self):
        fecha = self.cleaned_data.get("fecha")
        if fecha and fecha < timezone.now().date():
            raise ValidationError(
                "No se pueden agendar citas en fechas pasadas. Selecciona hoy o una fecha futura."
            )
        return fecha

    def clean(self):
        cleaned = super().clean()
        veterinario = cleaned.get("veterinario")
        fecha = cleaned.get("fecha")
        hora_inicio = cleaned.get("hora_inicio")

        if veterinario and fecha and hora_inicio:
            conflicto = Cita.objects.filter(
                veterinario=veterinario,
                fecha=fecha,
                hora_inicio=hora_inicio,
            ).exclude(estado="cancelada")

            if self.instance.pk:
                conflicto = conflicto.exclude(pk=self.instance.pk)

            if conflicto.exists():
                raise ValidationError(
                    f"El veterinario {veterinario} ya tiene una cita agendada "
                    f"el {fecha} a las {hora_inicio}. Elige otra hora u otro veterinario."
                )
        return cleaned
