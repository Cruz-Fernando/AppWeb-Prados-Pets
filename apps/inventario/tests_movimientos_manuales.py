"""
Inventario simple: cada producto tiene su cantidad y una fecha de vencimiento.
Buscar, Añadir (reponer), Quitar (restar con motivo) y retirar / reactivar.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.inventario.models import InsumoServicio, MovimientoInventario, Producto
from apps.usuarios.models import Rol

Usuario = get_user_model()


def usuario(nombre, rol):
    return Usuario.objects.create_user(
        username=nombre, password="Clave#12345", nombre_completo=nombre.title(),
        id_rol=Rol.objects.get_or_create(nombre_rol=rol)[0],
    )


class InventarioSimpleTests(TestCase):
    def setUp(self):
        self.client.force_login(usuario("aux_inv", "auxiliar"))
        hoy = timezone.localdate()
        self.amox = Producto.objects.create(codigo="AMOX", nombre="Amoxicilina 500 mg", precio_compra=Decimal("800"),
                                            precio_venta=Decimal("1500"), stock_actual=12, stock_minimo=3,
                                            fecha_vencimiento=hoy + timedelta(days=200))
        self.suero = Producto.objects.create(codigo="SUERO", nombre="Suero oral", precio_compra=Decimal("2000"),
                                             precio_venta=Decimal("4000"), stock_actual=4, stock_minimo=1,
                                             fecha_vencimiento=hoy - timedelta(days=3))
        self.gasa = Producto.objects.create(codigo="GASA", nombre="Gasa estéril", precio_venta=Decimal("300"),
                                            stock_actual=0, stock_minimo=5)

    # ---------- Lista y búsqueda ----------
    def test_lista_muestra_botones_fechas_y_busca_en_vivo(self):
        r = self.client.get(reverse("inventario:lista"))
        self.assertContains(r, "Añadir unidades de Amoxicilina 500 mg")
        self.assertContains(r, "Quitar unidades de Amoxicilina 500 mg")
        self.assertContains(r, self.amox.fecha_vencimiento.strftime("%d/%m/%Y"))
        self.assertContains(r, "Vencido")
        self.assertContains(r, "Agotado")
        self.assertEqual(r.context["productos_vencidos"], 1)

        parcial = self.client.get(reverse("inventario:lista"), {"q": "gas", "parcial": "1"})
        self.assertContains(parcial, "Gasa estéril")
        self.assertNotContains(parcial, "Amoxicilina")
        self.assertNotContains(parcial, "<html")            # solo la tabla

    def test_indicadores_de_la_lista(self):
        Producto.objects.create(codigo="RET", nombre="Retirado", precio_compra=Decimal("999"),
                                precio_venta=Decimal("1"), stock_actual=50, activo=False)

        r = self.client.get(reverse("inventario:lista"))
        activos = Producto.objects.filter(activo=True)
        # Mismos valores que el cálculo anterior, producto por producto.
        self.assertEqual(r.context["total_valor_inventario"],
                         sum(p.valor_total_inventario for p in activos))       # 12×800 + 4×2000
        self.assertEqual(r.context["total_valor_inventario"], Decimal("17600"))
        self.assertEqual(r.context["productos_bajo_stock"], 1)                # gasa: 0 ≤ 5
        self.assertEqual(r.context["productos_vencidos"], 1)                  # suero
        self.assertEqual(r.context["total_retirados"], 1)

    # ---------- Quitar ----------
    def test_quitar_resta_y_queda_en_el_kardex(self):
        r = self.client.post(reverse("inventario:salida"), {
            "producto": self.amox.pk, "cantidad": 2, "motivo": "DANO", "observacion": "Frasco roto",
        })
        self.assertRedirects(r, reverse("inventario:lista"), fetch_redirect_response=False)
        self.amox.refresh_from_db()
        self.assertEqual(self.amox.stock_actual, 10)
        mov = MovimientoInventario.objects.get()
        self.assertEqual(mov.tipo, "AJUSTE_MERMA")
        self.assertIn("Daño o rotura · Frasco roto", mov.observacion)
        self.assertEqual(mov.monto_total, Decimal("1600"))     # se valora al costo de compra

    def test_se_puede_dar_de_baja_un_producto_vencido(self):
        self.client.post(reverse("inventario:salida"), {
            "producto": self.suero.pk, "cantidad": 4, "motivo": "VENCIMIENTO",
        })
        self.suero.refresh_from_db()
        self.assertEqual(self.suero.stock_actual, 0)

    def test_quitar_mas_de_lo_que_hay_se_rechaza(self):
        r = self.client.post(reverse("inventario:salida"), {"producto": self.amox.pk, "cantidad": 13, "motivo": "DANO"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "No hay stock suficiente")
        self.amox.refresh_from_db()
        self.assertEqual(self.amox.stock_actual, 12)

    def test_quitar_exige_motivo(self):
        r = self.client.post(reverse("inventario:salida"), {"producto": self.amox.pk, "cantidad": 1, "motivo": ""})
        self.assertContains(r, "Elige el motivo de la salida.")

    def test_venta_queda_como_salida_por_venta(self):
        self.client.post(reverse("inventario:salida"), {"producto": self.amox.pk, "cantidad": 1, "motivo": "VENTA"})
        self.assertEqual(MovimientoInventario.objects.get().tipo, "SALIDA_VENTA")

    def test_pantalla_de_quitar(self):
        r = self.client.get(reverse("inventario:salida"), {"producto": self.suero.pk})
        self.assertContains(r, "Todo (4)")
        self.assertContains(r, "está vencido")
        sin_producto = self.client.get(reverse("inventario:salida"))
        self.assertContains(sin_producto, "Amoxicilina 500 mg")
        self.assertNotContains(sin_producto, "Gasa estéril")     # sin unidades no se puede quitar

    # ---------- Añadir ----------
    def test_anadir_suma_y_actualiza_la_fecha(self):
        vence = timezone.localdate() + timedelta(days=300)
        self.client.post(reverse("inventario:reposicion"), {
            "producto": self.gasa.pk, "cantidad": 10, "fecha_vencimiento": vence.isoformat(),
        })
        self.client.post(reverse("inventario:reposicion"), {"producto": self.gasa.pk, "cantidad": 5})
        self.gasa.refresh_from_db()
        self.assertEqual((self.gasa.stock_actual, self.gasa.fecha_vencimiento), (15, vence))
        self.assertEqual(MovimientoInventario.objects.filter(tipo="ENTRADA_COMPRA").count(), 2)

    def test_no_se_puede_anadir_con_fecha_pasada(self):
        r = self.client.post(reverse("inventario:reposicion"), {
            "producto": self.gasa.pk, "cantidad": 5,
            "fecha_vencimiento": (timezone.localdate() - timedelta(days=1)).isoformat(),
        })
        self.assertContains(r, "Esa fecha ya pasó")
        self.gasa.refresh_from_db()
        self.assertEqual(self.gasa.stock_actual, 0)

    def test_anadir_preselecciona_el_producto(self):
        r = self.client.get(reverse("inventario:reposicion"), {"producto": self.amox.pk})
        self.assertContains(r, f'<option value="{self.amox.pk}" selected>')
        self.assertContains(r, "Hay ahora")

    def test_crear_producto_con_fecha(self):
        vence = timezone.localdate() + timedelta(days=90)
        self.client.post(reverse("inventario:crear_producto"), {
            "codigo": "NUEVO", "nombre": "Producto nuevo", "precio_compra": "100", "precio_venta": "200",
            "stock_actual": "7", "stock_minimo": "2", "fecha_vencimiento": vence.isoformat(),
        })
        nuevo = Producto.objects.get(codigo="NUEVO")
        self.assertEqual((nuevo.stock_actual, nuevo.fecha_vencimiento), (7, vence))

    # ---------- Retirar / reactivar ----------
    def test_retirar_da_de_baja_lo_que_queda_y_se_puede_reactivar(self):
        InsumoServicio.objects.create(servicio="BANO", producto=self.amox, cantidad=1)
        sin_confirmar = self.client.post(reverse("inventario:retirar", args=[self.amox.pk]), {"motivo": "OTRO"})
        self.assertContains(sin_confirmar, "Marca la casilla para confirmar.")

        self.client.post(reverse("inventario:retirar", args=[self.amox.pk]), {"motivo": "PERDIDA", "confirmar": "on"})
        self.amox.refresh_from_db()
        self.assertEqual((self.amox.activo, self.amox.stock_actual), (False, 0))
        baja = MovimientoInventario.objects.get()
        self.assertEqual(baja.cantidad, 12)
        self.assertIn("retirado", baja.observacion)

        lista = self.client.get(reverse("inventario:lista"))
        self.assertNotContains(lista, "Añadir unidades de Amoxicilina 500 mg")    # ya no está en la tabla
        retirados = self.client.get(reverse("inventario:lista"), {"retirados": "1"})
        self.assertContains(retirados, "Amoxicilina 500 mg")

        self.client.post(reverse("inventario:reactivar", args=[self.amox.pk]))
        self.amox.refresh_from_db()
        self.assertTrue(self.amox.activo)

    def test_retirar_sin_stock_no_crea_movimiento(self):
        self.client.post(reverse("inventario:retirar", args=[self.gasa.pk]), {"motivo": "OTRO", "confirmar": "on"})
        self.gasa.refresh_from_db()
        self.assertFalse(self.gasa.activo)
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_groomer_no_puede_mover_inventario(self):
        self.client.force_login(usuario("groomer_inv", "groomer"))
        for url in (reverse("inventario:salida"), reverse("inventario:retirar", args=[self.amox.pk])):
            self.assertEqual(self.client.get(url).status_code, 403)