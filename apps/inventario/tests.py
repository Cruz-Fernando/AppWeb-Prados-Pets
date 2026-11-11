"""Pruebas de PB-13 (RF09): carga masiva del catálogo con la plantilla de Excel.

Criterio de aceptación: «El catálogo se carga desde la plantilla y el sistema
informa las filas con error».
"""
from datetime import date
from io import BytesIO

import openpyxl
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.usuarios.models import Rol

from .models import Medicamento, MovimientoInventario, Producto, Servicio, StockLote

ENCABEZADOS = [
    "Tipo", "Codigo", "Nombre", "Descripcion", "Precio", "StockMinimo",
    "PrincipioActivo", "Concentracion", "Presentacion", "RequiereReceta",
    "NumeroLote", "FechaVencimiento", "CantidadLote",
]


def excel(*filas):
    """Arma en memoria un .xlsx con los encabezados de la plantilla y las filas dadas."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(ENCABEZADOS)
    for fila in filas:
        ws.append(list(fila))
    buffer = BytesIO()
    wb.save(buffer)
    return SimpleUploadedFile(
        "catalogo.xlsx",
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class CargaMasivaCatalogoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        rol_admin, _ = Rol.objects.get_or_create(nombre_rol="administrador")
        rol_groomer, _ = Rol.objects.get_or_create(nombre_rol="groomer")
        # Administrador "normal": tiene el rol, pero NO es superusuario.
        cls.admin = Usuario.objects.create_user(
            username="admin_inventario",
            password="testpass123",
            nombre_completo="Admin Inventario",
            id_rol=rol_admin,
        )
        cls.groomer = Usuario.objects.create_user(
            username="groomer_inventario",
            password="testpass123",
            nombre_completo="Groomer Inventario",
            id_rol=rol_groomer,
        )
        cls.url = reverse("inventario:cargar_excel")

    def setUp(self):
        self.client.force_login(self.admin)

    def _subir(self, archivo):
        return self.client.post(self.url, {"archivo_excel": archivo})

    def test_administrador_sin_superusuario_puede_abrir_la_carga(self):
        self.assertFalse(self.admin.is_superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_groomer_no_puede_cargar_el_catalogo(self):
        self.client.force_login(self.groomer)
        response = self._subir(excel(
            ("PRODUCTO", "PROD-001", "Champú", "", 30000, 5, "", "", "", "", "", None, None),
        ))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Producto.objects.exists())

    def test_carga_medicamento_producto_y_servicio_con_lote_y_kardex(self):
        response = self._subir(excel(
            ("MEDICAMENTO", "MED-001", "Amoxicilina 250 mg", "Antibiótico", 1800, 20,
             "Amoxicilina", "250 mg", "Caja x 10", "SI", "AMX-01", date(2027, 11, 30), 100),
            ("PRODUCTO", "PROD-001", "Champú antipulgas", "", 32000, 5,
             "", "", "Frasco 250 ml", "", "SHP-01", "2028-06-30", 20),
            ("SERVICIO", "SERV-001", "Consulta general", "", 45000, None,
             "", "", "", "", "", None, None),
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["exitos"], 3)
        self.assertEqual(response.context["errores"], [])

        med = Producto.objects.get(codigo="MED-001")
        self.assertEqual(med.stock_actual, 100)
        self.assertEqual(med.stock_minimo, 20)
        self.assertTrue(Medicamento.objects.get(producto=med).requiere_receta)
        self.assertEqual(
            StockLote.objects.get(producto=med).fecha_vencimiento, date(2027, 11, 30)
        )

        prod = Producto.objects.get(codigo="PROD-001")
        self.assertEqual(prod.stock_actual, 20)
        self.assertEqual(
            StockLote.objects.get(producto=prod).fecha_vencimiento, date(2028, 6, 30)
        )

        self.assertTrue(Servicio.objects.filter(codigo="SERV-001").exists())
        self.assertEqual(
            MovimientoInventario.objects.filter(tipo="ENTRADA_COMPRA").count(), 2
        )

    def test_informa_filas_con_error_y_guarda_las_validas(self):
        response = self._subir(excel(
            ("PRODUCTO", "PROD-OK", "Correa", "", 25000, 4, "", "", "", "", "", None, None),
            ("JUGUETE", "X-1", "Pelota", "", 5000, 1, "", "", "", "", "", None, None),
            ("PRODUCTO", "", "Sin código", "", 5000, 1, "", "", "", "", "", None, None),
            ("PRODUCTO", "PROD-2", "Precio malo", "", "$abc", 1, "", "", "", "", "", None, None),
            ("PRODUCTO", "PROD-3", "Lote malo", "", 5000, 1, "", "", "", "", "L-1", None, "diez"),
        ))

        self.assertEqual(response.context["exitos"], 1)
        filas_con_error = sorted(e["fila"] for e in response.context["errores"])
        self.assertEqual(filas_con_error, [3, 4, 5, 6])
        self.assertEqual(list(Producto.objects.values_list("codigo", flat=True)), ["PROD-OK"])
        # La fila 6 falló al crear el lote: no debe quedar el producto a medias.
        self.assertFalse(Producto.objects.filter(codigo="PROD-3").exists())

    def test_codigo_repetido_se_rechaza_sin_duplicar(self):
        fila = ("PRODUCTO", "PROD-001", "Champú", "", 30000, 5, "", "", "", "", "", None, None)
        self._subir(excel(fila))
        response = self._subir(excel(fila))

        self.assertEqual(response.context["exitos"], 0)
        self.assertEqual(len(response.context["errores"]), 1)
        self.assertIn("ya existe", response.context["errores"][0]["error"])
        self.assertEqual(Producto.objects.filter(codigo="PROD-001").count(), 1)

    def test_descarga_la_plantilla_con_los_encabezados_esperados(self):
        response = self.client.get(reverse("inventario:descargar_plantilla"))

        self.assertEqual(response.status_code, 200)
        wb = openpyxl.load_workbook(BytesIO(response.content))
        encabezados = [c.value for c in wb.active[1]][: len(ENCABEZADOS)]
        self.assertEqual(encabezados, ENCABEZADOS)