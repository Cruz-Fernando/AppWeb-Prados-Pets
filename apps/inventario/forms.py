from django import forms


class CargaExcelForm(forms.Form):
    archivo_excel = forms.FileField(
        label="Seleccionar archivo Excel (.xlsx)",
        widget=forms.FileInput(attrs={'accept': '.xlsx, .xls', 'class': 'form-control'})
    )

    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get('archivo_excel')
        if archivo:
            if not archivo.name.endswith(('.xlsx', '.xls')):
                raise forms.ValidationError("El archivo seleccionado debe tener extensión .xlsx o .xls")
        return archivo