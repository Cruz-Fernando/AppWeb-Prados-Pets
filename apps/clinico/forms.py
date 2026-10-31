from django import forms
from .models import Hospitalizacion

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