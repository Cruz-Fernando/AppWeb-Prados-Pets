"""Pruebas de las correcciones de cierre del Sprint 4 en la carga masiva (PB-13 / RF09)."""
from datetime import timedelta
from io import BytesIO

import openpyxl
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.usuarios.models import Rol

from .models import Producto, StockLote
from .tests import ENCABEZADOS, excel


def excel_con_instrucciones_activa(*filas):
    """Como la plantilla real: 2 hojas y el archivo guardado mirando «Instrucciones»."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Carga Inventario"
    ws.append(ENCABEZADOS)
    for fila in filas:
        ws.append(list(fila))
    wb.create_sheet("Instrucciones").append(["Lee esto primero"])
    wb.active = 1
    buffer = BytesIO()
    wb.save(buffer)
    return SimpleUploadedFile("catalogo.xlsx", buffer.getvalue())


class CargaMasivaCierreSprint4Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol, _ = Rol.objects.get_or_create(nombre_rol="administrador")
        cls.admin = get_user_model().objects.create_user(
            username="admin_s4", password="x", nombre_completo="Admin", id_rol=rol,
        )
        cls.url = reverse("inventario:cargar_excel")

    def setUp(self):
        self.client.force_login(self.admin)

    def _subir(self, archivo):
        return self.client.post(self.url, {"archivo_excel": archivo})

    def _fila(self, **cambios):
        base = dict(tipo="PRODUCTO", codigo="P-1", nombre="Champú", desc="", precio=30000, stock_min=5,
                    principio="", conc="", pres="", receta="", lote="", venc=None, cant=None)
        base.update(cambios)
        return tuple(base.values())

    def test_lee_la_primera_hoja_aunque_se_guarde_mirando_otra(self):
        response = self._subir(excel_con_instrucciones_activa(self._fila()))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["exitos"], 1)
        self.assertTrue(Producto.objects.filter(codigo="P-1").exists())

    def test_encabezados_cambiados_se_rechazan_sin_guardar_nada(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Tipo", "Codigo", "Nombre", "Precio", "Descripcion"] + ENCABEZADOS[5:])
        ws.append(list(self._fila()))
        buffer = BytesIO()
        wb.save(buffer)
        response = self._subir(SimpleUploadedFile("c.xlsx", buffer.getvalue()))
        self.assertEqual(response.context["errores"][0]["fila"], 1)
        self.assertFalse(Producto.objects.exists())

    def test_lote_sin_cantidad_se_rechaza_en_vez_de_perderse(self):
        response = self._subir(excel(self._fila(lote="L-1")))
        self.assertIn("CantidadLote", response.context["errores"][0]["error"])
        self.assertFalse(Producto.objects.exists())

    def test_lote_vencido_no_entra_como_stock(self):
        vencido = timezone.localdate() - timedelta(days=1)
        response = self._subir(excel(self._fila(lote="L-1", venc=vencido.isoformat(), cant=10)))
        self.assertIn("venció", response.context["errores"][0]["error"])
        self.assertFalse(StockLote.objects.exists())

    def test_acepta_precio_con_signo_y_fecha_dia_mes_anio(self):
        venc = (timezone.localdate() + timedelta(days=400)).strftime("%d/%m/%Y")
        response = self._subir(excel(self._fila(precio="$50.000", lote="L-1", venc=venc, cant=3)))
        self.assertEqual(response.context["errores"], [])
        producto = Producto.objects.get(codigo="P-1")
        self.assertEqual(producto.precio_venta, 50000)
        self.assertEqual(producto.stock_actual, 3)

    def test_codigo_repetido_en_el_mismo_archivo(self):
        response = self._subir(excel(self._fila(), self._fila(nombre="Otro")))
        self.assertEqual(response.context["exitos"], 1)
        self.assertIn("repetido", response.context["errores"][0]["error"])

    def test_requiere_receta_invalido_se_informa(self):
        response = self._subir(excel(self._fila(tipo="MEDICAMENTO", receta="TAL VEZ")))
        self.assertIn("SI o NO", response.context["errores"][0]["error"])

    def test_rechaza_archivos_que_no_son_xlsx(self):
        response = self._subir(SimpleUploadedFile("catalogo.csv", b"Tipo,Codigo\n"))
        self.assertTrue(response.context["form"].errors)