from django import forms
from .models import Producto, MovimientoInventario, Venta, DetalleVenta, CategoriaProducto, Proveedor


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo', 'codigo_barras', 'nombre', 'descripcion', 
            'categoria', 'proveedor', 'precio_compra', 'precio_venta', 
            'stock_actual', 'stock_minimo'
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
        }


class ReposicionForm(forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(activo=True), 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    cantidad = forms.IntegerField(
        min_value=1, 
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    nuevo_precio_compra = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False, 
        help_text="Opcional si cambió el costo", 
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    observacion = forms.CharField(
        max_length=255, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
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