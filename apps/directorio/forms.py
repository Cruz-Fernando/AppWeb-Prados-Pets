from django import forms
from .models import Dueno, Mascota, Vacunacion


class DuenoForm(forms.ModelForm):
    class Meta:
        model = Dueno
        fields = ['nombre_completo', 'telefono', 'direccion', 'correo']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_nombre_completo'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_telefono'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_direccion'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_correo'}),
        }

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        dueno_id = self.instance.pk
        if Dueno.objects.filter(telefono=telefono).exclude(pk=dueno_id).exists():
            raise forms.ValidationError(
                f"El número de teléfono '{telefono}' ya está registrado por otro dueño."
            )
        return telefono


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
            'tamano', 'sexo', 'color', 'fecha_nacimiento', 'peso',
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
            'peso': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'id_peso',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Ej: 8.50',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['buscar_dueno'].initial = (
                f"{self.instance.id_dueno.nombre_completo} "
                f"({self.instance.id_dueno.telefono})"
            )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('id_dueno'):
            self.add_error('buscar_dueno', 'Debes seleccionar un dueño de la lista de sugerencias.')
        return cleaned


class VacunacionForm(forms.ModelForm):
    class Meta:
        model = Vacunacion
        fields = ['vacuna', 'fecha', 'observaciones']
        widgets = {
            'vacuna': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Rabia',
            }),
            'fecha': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Lote, veterinario u otra información relevante',
            }),
        }