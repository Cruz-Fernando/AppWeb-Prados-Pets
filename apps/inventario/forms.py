from django import forms
from django.utils import timezone

from .services import MOTIVOS_SALIDA
from .models import Producto, MovimientoInventario, Venta, DetalleVenta, CategoriaProducto, Proveedor


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo', 'codigo_barras', 'nombre', 'descripcion', 
            'categoria', 'proveedor', 'precio_compra', 'precio_venta', 
            'stock_actual', 'stock_minimo', 'fecha_vencimiento'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: PROD-001'}),
            'codigo_barras': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 770123456789'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'precio_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_venta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        }
        labels = {
            'stock_actual': 'Cantidad inicial',
            'fecha_vencimiento': 'Fecha de vencimiento (opcional)',
        }


class ReposicionForm(forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(activo=True).order_by('nombre'),
        empty_label="Selecciona un producto",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    cantidad = forms.IntegerField(
        min_value=1, max_value=100000, label="Cantidad recibida",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 12'})
    )
    fecha_vencimiento = forms.DateField(
        required=False, label="Fecha de vencimiento",
        help_text="Opcional. Si la escribes, pasa a ser la fecha del producto.",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d')
    )
    nuevo_precio_compra = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=0,
        label="Nuevo costo de compra (unidad)",
        help_text="Opcional, solo si cambió el costo.",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    observacion = forms.CharField(
        max_length=200, required=False, label="Observación",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Factura 1234 del proveedor'})
    )

    def clean_fecha_vencimiento(self):
        vence = self.cleaned_data.get('fecha_vencimiento')
        if vence and vence <= timezone.localdate():
            raise forms.ValidationError('Esa fecha ya pasó; no se puede ingresar mercancía vencida.')
        return vence


class SalidaManualForm(forms.Form):
    """Quitar unidades a mano, con su motivo."""
    cantidad = forms.IntegerField(
        min_value=1, max_value=100000, label="Cantidad a quitar",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 1'})
    )
    motivo = forms.ChoiceField(
        choices=[('', 'Selecciona el motivo')] + MOTIVOS_SALIDA, label="Motivo",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    observacion = forms.CharField(
        max_length=150, required=False, label="Observación",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Frasco roto al descargar'})
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto
        if producto is not None:
            self.fields['cantidad'].widget.attrs['max'] = producto.stock_actual

    def clean(self):
        datos = super().clean()
        if not datos.get('motivo'):
            self.add_error('motivo', 'Elige el motivo de la salida.')
        return datos


class RetirarProductoForm(forms.Form):
    motivo = forms.ChoiceField(
        choices=MOTIVOS_SALIDA, initial='OTRO', label="Motivo de la baja de las unidades restantes",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    observacion = forms.CharField(
        max_length=150, required=False, label="Observación",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Ya no se trabaja con este proveedor'})
    )
    confirmar = forms.BooleanField(
        required=True, label="Entiendo que el producto dejará de aparecer en el inventario",
        error_messages={'required': 'Marca la casilla para confirmar.'},
    )


class CargaExcelForm(forms.Form):
    archivo_excel = forms.FileField(
        label="Archivo Excel",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'})
    )

    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get('archivo_excel')
        if archivo:
            # openpyxl solo lee .xlsx: .xls y .csv fallaban al abrirse con un error técnico
            if not archivo.name.lower().endswith('.xlsx'):
                raise forms.ValidationError("El archivo debe ser .xlsx. Descarga la plantilla y guárdala como «Libro de Excel (.xlsx)».")
            if archivo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("El archivo pesa más de 5 MB. Divide la carga en varios archivos.")
        return archivo


# Alias por compatibilidad
CargarExcelForm = CargaExcelForm