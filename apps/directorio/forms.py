from django import forms
from .models import Mascota


class MascotaForm(forms.ModelForm):
    # Campo de texto visible para buscar el dueño — el valor real va en id_dueno (hidden)
    buscar_dueno = forms.CharField(
        required=True,
        label="Propietario",
        widget=forms.TextInput(attrs={
            'id': 'buscar_dueno',
            'class': 'form-control',
            'placeholder': 'Escribe el nombre o teléfono del dueño…',
            'autocomplete': 'off',
        }),
    )

    class Meta:
        model = Mascota
        fields = [
            'id_dueno', 'nombre', 'especie', 'raza',
            'tamano', 'sexo', 'color', 'fecha_nacimiento',
        ]
        widgets = {
            'id_dueno': forms.HiddenInput(attrs={'id': 'id_dueno_hidden'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_nombre'}),
            'especie': forms.Select(attrs={'class': 'form-control', 'id': 'id_especie'}),
            'raza': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_raza'}),
            'tamano': forms.Select(attrs={'class': 'form-control', 'id': 'id_tamano'}),
            'sexo': forms.Select(attrs={'class': 'form-control', 'id': 'id_sexo'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_color', 'placeholder': 'Ej: marrón, negro con blanco…'}),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_fecha_nacimiento'}),
        }

    def clean(self):
        cleaned = super().clean()
        # Si el campo oculto id_dueno quedó vacío, lanzar error descriptivo
        if not cleaned.get('id_dueno'):
            self.add_error('buscar_dueno', 'Debes seleccionar un dueño de la lista de sugerencias.')
        return cleaned