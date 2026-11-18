"""Inventario unido: Kardex como pestaña, filtros, alertas y menú lateral simplificado."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.inventario.models import MovimientoInventario, Producto
from apps.usuarios.models import Rol

Usuario = get_user_model()


class KardexUnificadoTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="aux_kardex", password="x", nombre_completo="Aux Kardex",
            id_rol=Rol.objects.get_or_create(nombre_rol="auxiliar")[0],
        )
        self.client.force_login(self.user)
        hoy = timezone.localdate()
        self.amox = Producto.objects.create(codigo="AMOX", nombre="Amoxicilina", precio_compra=Decimal("800"),
                                            precio_venta=Decimal("1500"), stock_actual=12, stock_minimo=3,
                                            fecha_vencimiento=hoy + timedelta(days=10))
        self.gasa = Producto.objects.create(codigo="GASA", nombre="Gasa", precio_venta=Decimal("300"),
                                            stock_actual=0, stock_minimo=5)
        self.suero = Producto.objects.create(codigo="SUERO", nombre="Suero", precio_compra=Decimal("100"),
                                             precio_venta=Decimal("400"), stock_actual=2, stock_minimo=4,
                                             fecha_vencimiento=hoy - timedelta(days=1))
        for producto, tipo, cantidad in ((self.amox, "ENTRADA_COMPRA", 12), (self.amox, "SALIDA_CLINICA", 2),
                                         (self.gasa, "AJUSTE_MERMA", 1)):
            MovimientoInventario.objects.create(
                producto=producto, tipo=tipo, cantidad=cantidad, precio_unitario_historico=Decimal("10"),
                monto_total=Decimal("10") * cantidad, usuario=self.user,
            )

    def test_menu_lateral_sin_carga_masiva_ni_kardex(self):
        r = self.client.get(reverse("inventario:lista"))
        self.assertContains(r, 'id="nav-inventario"')
        self.assertNotContains(r, 'id="nav-inventario-excel"')
        self.assertNotContains(r, 'id="nav-inventario-kardex"')
        # La carga masiva sigue a mano en la página del inventario
        self.assertContains(r, reverse("inventario:cargar_excel"))
        self.assertContains(r, "Movimientos (Kardex)")

    def test_kardex_es_una_pestana_del_inventario(self):
        r = self.client.get(reverse("inventario:kardex"))
        self.assertContains(r, 'class="inv-tab is-activa" aria-current="page">Movimientos (Kardex)')
        self.assertContains(r, "Nuevo producto")
        self.assertEqual(r.context["resumen"]["unidades_entrada"], 12)
        self.assertEqual(r.context["resumen"]["unidades_salida"], 3)

    def test_kardex_filtra_por_producto_tipo_y_texto(self):
        url = reverse("inventario:kardex")
        r = self.client.get(url, {"producto": self.amox.pk})
        self.assertEqual(len(r.context["movimientos"]), 2)
        self.assertContains(r, "Historial de")

        r = self.client.get(url, {"tipo": "salidas"})
        self.assertEqual({m.tipo for m in r.context["movimientos"]}, {"SALIDA_CLINICA", "AJUSTE_MERMA"})

        r = self.client.get(url, {"q": "gasa", "parcial": "1"})
        self.assertEqual(len(r.context["movimientos"]), 1)
        self.assertNotContains(r, "<html")

        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        r = self.client.get(url, {"desde": manana})
        self.assertEqual(len(r.context["movimientos"]), 0)

    def test_kardex_exporta_a_excel_con_los_filtros(self):
        r = self.client.get(reverse("inventario:kardex"), {"producto": self.amox.pk, "exportar": "1"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheetml", r["Content-Type"])

    def test_lista_filtra_por_estado(self):
        url = reverse("inventario:lista")
        nombres = lambda r: {p.nombre for p in r.context["productos"]}  # noqa: E731
        self.assertEqual(nombres(self.client.get(url, {"estado": "agotados"})), {"Gasa"})
        self.assertEqual(nombres(self.client.get(url, {"estado": "vencidos"})), {"Suero"})
        self.assertEqual(nombres(self.client.get(url, {"estado": "por_vencer"})), {"Amoxicilina"})
        self.assertEqual(nombres(self.client.get(url, {"estado": "reabastecer"})), {"Gasa", "Suero"})
        self.assertEqual(len(self.client.get(url, {"estado": "otro"}).context["productos"]), 3)

    def test_campana_muestra_alertas_de_inventario(self):
        r = self.client.get(reverse("usuarios:notificaciones"))
        claves = {a["clave"] for a in r.context["inventario"]}
        self.assertEqual(claves, {"agotados", "bajo", "vencidos", "por_vencer"})
        self.assertContains(r, "1 producto agotado")
        self.assertContains(r, "?estado=vencidos")

    def test_groomer_no_ve_alertas_de_inventario(self):
        groomer = Usuario.objects.create_user(
            username="groomer_k", password="x", id_rol=Rol.objects.get_or_create(nombre_rol="groomer")[0])
        self.client.force_login(groomer)
        r = self.client.get(reverse("usuarios:notificaciones"))
        self.assertEqual(r.context["inventario"], [])
