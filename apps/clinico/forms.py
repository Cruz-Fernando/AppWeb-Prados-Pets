from django import forms
from .models import ConsultaMedica, Hospitalizacion


class ConsultaMedicaForm(forms.ModelForm):
    class Meta:
        model = ConsultaMedica
        fields = [
            "anamnesis",
            "peso",
            "temperatura",
            "frecuencia_cardiaca",
            "frecuencia_respiratoria",
            "examen_general",
            "sistema_tegumentario",
            "sistema_cardiovascular",
            "sistema_respiratorio",
            "sistema_digestivo",
            "sistema_genitourinario",
            "sistema_musculoesqueletico",
            "sistema_nervioso",
            "sistema_linfatico",
        ]
        widgets = {
            "anamnesis": forms.Textarea(attrs={"rows": 4}),
            "peso": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "temperatura": forms.NumberInput(attrs={"step": "0.1", "min": "1"}),
            "frecuencia_cardiaca": forms.NumberInput(attrs={"min": "0"}),
            "frecuencia_respiratoria": forms.NumberInput(attrs={"min": "0"}),
            "examen_general": forms.Textarea(attrs={"rows": 3}),
            "sistema_tegumentario": forms.Textarea(attrs={"rows": 2}),
            "sistema_cardiovascular": forms.Textarea(attrs={"rows": 2}),
            "sistema_respiratorio": forms.Textarea(attrs={"rows": 2}),
            "sistema_digestivo": forms.Textarea(attrs={"rows": 2}),
            "sistema_genitourinario": forms.Textarea(attrs={"rows": 2}),
            "sistema_musculoesqueletico": forms.Textarea(attrs={"rows": 2}),
            "sistema_nervioso": forms.Textarea(attrs={"rows": 2}),
            "sistema_linfatico": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["anamnesis"].widget.attrs["placeholder"] = (
            "Motivo de consulta, evolución y antecedentes relevantes"
        )

class HospitalizacionForm(forms.ModelForm):
    class Meta:
        model = Hospitalizacion
        fields = [
            'mascota', 'motivo', 'peso_actual', 'temperatura', 
            'frecuencia_cardiaca', 'frecuencia_respiratoria', 'mucosas',
            'diagnostico_presuntivo', 'tratamiento_inicial', 'observaciones',
            'documento_consentimiento', 'examenes_adjuntos'
        ]
        widgets = {
            'mascota': forms.Select(attrs={'class': 'form-select'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Parvovirosis, Traumatismo...'}),
            'peso_actual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'temperatura': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'frecuencia_cardiaca': forms.NumberInput(attrs={'class': 'form-control'}),
            'frecuencia_respiratoria': forms.NumberInput(attrs={'class': 'form-control'}),
            'mucosas': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Rosadas, pálidas...'}),
            'diagnostico_presuntivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'tratamiento_inicial': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'documento_consentimiento': forms.FileInput(attrs={'class': 'form-control'}),
            'examenes_adjuntos': forms.FileInput(attrs={'class': 'form-control'}),
        }