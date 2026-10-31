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
        label="Archivo Excel o CSV",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls, .csv'})
    )

    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get('archivo_excel')
        if archivo:
            if not archivo.name.endswith(('.xlsx', '.xls', '.csv')):
                raise forms.ValidationError("El archivo seleccionado debe tener extensión .xlsx, .xls o .csv")
        return archivo


# Alias por compatibilidad
CargarExcelForm = CargaExcelForm