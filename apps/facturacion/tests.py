"""
Facturación · Ganancias por groomer (comisión del 40 %).
"""

from datetime import timedelta
from decimal import Decimal
from io import BytesIO

import openpyxl
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.facturacion.ganancias import rango_de, resumen
from apps.inventario.models import InsumoServicio, Producto
from apps.peluqueria.models import CitaPeluqueria
from apps.usuarios.models import Rol

Usuario = get_user_model()


def usuario(nombre, rol, completo=None):
    return Usuario.objects.create_user(
        username=nombre, password="Clave#12345", nombre_completo=completo or nombre.title(),
        id_rol=Rol.objects.get_or_create(nombre_rol=rol)[0],
    )


class GananciasGroomerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = usuario("admin_fac", "administrador")
        cls.auxiliar = usuario("aux_fac", "auxiliar")
        cls.ana = usuario("ana_groomer", "groomer", "Ana Groomer")
        cls.luis = usuario("luis_groomer", "groomer", "Luis Groomer")
        cls.domiciliario = usuario("domi_fac", "domiciliario")

    def cita(self, groomer, precio, horas, estado="Programada", nombre="Luna"):
        return CitaPeluqueria.objects.create(
            nombre_mascota=nombre, raza="Criollo", servicio="BANO", groomer=groomer,
            fecha_hora=timezone.now() + timedelta(hours=horas), precio=precio, estado=estado,
        )

    def setUp(self):
        # Todo dentro de «hoy» para que el periodo «Hoy» los incluya
        ahora = timezone.localtime()
        self.horas_atras = -min(2, ahora.hour) if ahora.hour else 0
        self.r1 = self.cita(self.ana, 40000, self.horas_atras - 0.01, "Realizada", "Max")
        self.r2 = self.cita(self.ana, 25000, self.horas_atras - 0.02, "Realizada", "Kira")
        self.r3 = self.cita(self.luis, 30000, self.horas_atras - 0.03, "Realizada", "Toby")
        self.pend = self.cita(self.luis, 50000, self.horas_atras - 0.04, "Programada", "Coco")   # ya pasó
        self.canc = self.cita(self.ana, 99000, self.horas_atras - 0.05, "Cancelada", "Nala")

    # ---------- Cálculo ----------
    def test_comision_del_40_solo_de_lo_realizado(self):
        hoy = timezone.localdate()
        r = resumen(hoy, hoy)
        ana = next(f for f in r.filas if f.groomer == self.ana)
        luis = next(f for f in r.filas if f.groomer == self.luis)
        self.assertEqual((ana.servicios, ana.facturado, ana.comision, ana.clinica),
                         (2, Decimal("65000"), Decimal("26000"), Decimal("39000")))
        self.assertEqual(ana.cancelados, 1)
        self.assertEqual((luis.servicios, luis.comision, luis.por_cerrar), (1, Decimal("12000"), 1))
        self.assertEqual((r.facturado, r.comision, r.clinica), (Decimal("95000"), Decimal("38000"), Decimal("57000")))

    def test_periodos(self):
        lunes = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        self.assertEqual(rango_de("semana"), (lunes, lunes + timedelta(days=6)))
        hoy = timezone.localdate()
        self.assertEqual(rango_de("mes")[0], hoy.replace(day=1))
        desde, hasta = rango_de("mes_anterior")
        self.assertEqual((desde.day, hasta + timedelta(days=1)), (1, hoy.replace(day=1)))
        self.assertEqual(rango_de("rango", hoy, hoy - timedelta(days=3)), (hoy - timedelta(days=3), hoy))

    # ---------- Pantalla ----------
    def test_administrador_ve_a_todos(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("facturacion:panel"), {"periodo": "hoy"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Ana Groomer")
        self.assertContains(r, "Luis Groomer")
        self.assertContains(r, "$38.000")          # comisiones a pagar
        self.assertContains(r, "Por cerrar")

    def test_filtrar_por_groomer(self):
        self.client.force_login(self.auxiliar)
        r = self.client.get(reverse("facturacion:panel"), {"periodo": "hoy", "groomer": self.ana.pk})
        self.assertContains(r, "Servicios de Ana Groomer")
        self.assertNotContains(r, "Toby")

    def test_groomer_solo_ve_lo_suyo_y_no_cierra(self):
        self.client.force_login(self.ana)
        r = self.client.get(reverse("facturacion:panel"), {"periodo": "hoy", "groomer": self.luis.pk})
        self.assertContains(r, "Mis ganancias")
        self.assertContains(r, "$26.000")
        self.assertNotContains(r, "Luis Groomer")
        self.assertNotContains(r, "Toby")

        self.client.post(reverse("facturacion:cerrar_servicio", args=[self.pend.pk]), {"accion": "realizada"})
        self.pend.refresh_from_db()
        self.assertEqual(self.pend.estado, "Programada")

    def test_cerrar_como_realizada_suma_la_comision(self):
        self.client.force_login(self.auxiliar)
        r = self.client.post(reverse("facturacion:cerrar_servicio", args=[self.pend.pk]),
                             {"accion": "realizada", "query": "periodo=hoy"}, follow=True)
        self.pend.refresh_from_db()
        self.assertEqual(self.pend.estado, "Realizada")
        self.assertContains(r, "suma $20.000 de comisión")
        hoy = timezone.localdate()
        luis = next(f for f in resumen(hoy, hoy).filas if f.groomer == self.luis)
        self.assertEqual((luis.servicios, luis.comision, luis.por_cerrar), (2, Decimal("32000"), 0))

    def test_cancelar_devuelve_insumos_y_no_suma(self):
        champu = Producto.objects.create(codigo="CH", nombre="Champú", precio_venta=Decimal("1"), stock_actual=5)
        InsumoServicio.objects.create(servicio="BANO", producto=champu, cantidad=1)
        from apps.peluqueria.insumos import descontar_insumos_cita
        descontar_insumos_cita(self.pend)
        champu.refresh_from_db()
        self.assertEqual(champu.stock_actual, 4)

        self.client.force_login(self.admin)
        self.client.post(reverse("facturacion:cerrar_servicio", args=[self.pend.pk]),
                         {"accion": "cancelada", "motivo": "No llegó"})
        self.pend.refresh_from_db(); champu.refresh_from_db()
        self.assertEqual((self.pend.estado, self.pend.motivo_cancelacion), ("Cancelada", "No llegó"))
        self.assertEqual(champu.stock_actual, 5)

    def test_no_se_cierra_dos_veces(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("facturacion:cerrar_servicio", args=[self.r1.pk]),
                             {"accion": "cancelada"}, follow=True)
        self.r1.refresh_from_db()
        self.assertEqual(self.r1.estado, "Realizada")
        self.assertContains(r, "ya estaba realizada")

    def test_excel(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("facturacion:exportar_excel"), {"periodo": "hoy"})
        self.assertEqual(r.status_code, 200)
        wb = openpyxl.load_workbook(BytesIO(r.content))
        filas = {f[0]: f for f in wb["Por groomer"].iter_rows(min_row=4, values_only=True)}
        self.assertEqual(filas["Ana Groomer"][3], 26000)
        self.assertEqual(filas["TOTAL"][3], 38000)
        self.assertEqual(wb["Detalle de servicios"].max_row, 6)      # encabezado + 5 citas

    def test_permisos(self):
        self.client.force_login(self.domiciliario)
        self.assertEqual(self.client.get(reverse("facturacion:panel")).status_code, 403)
        self.client.force_login(self.auxiliar)
        panel = self.client.get(reverse("usuarios:dashboard"))
        self.assertContains(panel, 'id="nav-facturacion"')