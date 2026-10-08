from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Rol, Usuario


class RolForm(forms.ModelForm):
    class Meta:
        model = Rol
        fields = ["nombre_rol", "descripcion"]
        widgets = {
            "nombre_rol": forms.TextInput(
                attrs={"class": "app-input", "placeholder": "Ej. veterinario"}
            ),
            "descripcion": forms.Textarea(
                attrs={"class": "app-input", "rows": 3}
            ),
        }
        labels = {
            "nombre_rol": "Nombre del rol",
            "descripcion": "Descripción",
        }


class UsuarioRolForm(forms.ModelForm):
    """
    Formulario reducido a propósito (HU02): un administrador asigna el rol
    y controla si el usuario está activo. La creación de cuentas nuevas no
    es parte de esta historia.
    """

    estado = forms.ChoiceField(
        choices=[("activo", "Activo"), ("inactivo", "Inactivo")],
        widget=forms.Select(attrs={"class": "app-input"}),
        label="Estado",
        help_text="Un usuario en estado 'inactivo' no podrá iniciar sesión.",
    )

    class Meta:
        model = Usuario
        fields = ["id_rol", "estado"]
        widgets = {
            "id_rol": forms.Select(attrs={"class": "app-input"}),
        }
        labels = {
            "id_rol": "Rol",
        }


class UsuarioCreacionForm(UserCreationForm):
    """
    Alta de personal (HU02): el administrador registra a una persona del
    equipo (auxiliar, veterinario, groomer, domiciliario, u otro
    administrador) con su rol desde el primer momento — nunca queda sin
    rol, a diferencia del superusuario original creado por createsuperuser.

    Se apoya en UserCreationForm de Django para el manejo de la contraseña
    (validación de dos campos, hasheo al guardar) en vez de reinventarlo.
    """

    estado = forms.ChoiceField(
        choices=[("activo", "Activo"), ("inactivo", "Inactivo")],
        initial="activo",
        label="Estado",
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "nombre_completo", "telefono", "id_rol", "estado")
        labels = {
            "id_rol": "Rol",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "app-input")

    # is_staff se calcula solo, en Usuario.save(), a partir del rol elegido
    # (ver models.py) — no hace falta tocarlo aquí.
