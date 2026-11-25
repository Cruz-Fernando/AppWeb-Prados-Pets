"""
PB-21 / RF11 · Alertas en pantalla de stock bajo y de vencimiento con fecha y lote.

Criterio de aceptación: la alerta aparece en pantalla cuando se cumple la
condición de stock bajo o de vencimiento.

Umbrales del acta: menos de 2 unidades = CRÍTICO (rojo), menos de 5 = BAJO
(amarillo). No dependen del stock mínimo de cada producto.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.inventario.alertas import alertas_inventario
from apps.inventario.models import Producto
from apps.inventario.services import registrar_entrada
from apps.usuarios.models import Rol

Usuario = get_user_model()


def producto(codigo, stock, *, vence=None, lote=None, minimo=10):
    return Producto.objects.create(codigo=codigo, nombre=f"Producto {codigo}", precio_venta=Decimal("1000"),
                                   stock_actual=stock, stock_minimo=minimo,
                                   fecha_vencimiento=vence, numero_lote=lote)


class AlertasInventarioPB21Tests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.user = Usuario.objects.create_user(
            username="aux_pb21", password="x", nombre_completo="Aux PB21",
            id_rol=Rol.objects.get_or_create(nombre_rol="auxiliar")[0],
        )
        self.client.force_login(self.user)

    def alertas(self):
        return {a["clave"]: a for a in alertas_inventario(self.hoy)}

    def codigos(self, alerta):
        return {d["producto"].codigo for d in alerta["productos"]}

    def campana(self):
        return self.client.get(reverse("usuarios:notificaciones"))

    # ---------- Stock: 1, 3 y 6 unidades ----------
    def test_una_unidad_es_critico_en_rojo(self):
        producto("UNO", 1)
        a = self.alertas()
        self.assertEqual(set(a), {"critico"})
        self.assertEqual((a["critico"]["nivel"], a["critico"]["total"]), ("peligro", 1))
        self.assertEqual(self.codigos(a["critico"]), {"UNO"})

    def test_tres_unidades_es_bajo_en_amarillo(self):
        producto("TRES", 3)
        a = self.alertas()
        self.assertEqual(set(a), {"bajo"})
        self.assertEqual(a["bajo"]["nivel"], "aviso")

    def test_seis_unidades_no_alerta_aunque_este_bajo_su_stock_minimo(self):
        producto("SEIS", 6, minimo=10)
        self.assertEqual(self.alertas(), {})
        r = self.campana()
        self.assertEqual(r.context["inventario"], [])
        self.assertContains(r, "Todo al día")

    def test_cero_unidades_es_agotado(self):
        producto("CERO", 0)
        self.assertEqual(set(self.alertas()), {"agotados"})

    def test_umbrales_en_los_bordes(self):
        for codigo, stock in (("B2", 2), ("B4", 4), ("B5", 5)):
            producto(codigo, stock)
        a = self.alertas()
        self.assertEqual(self.codigos(a["bajo"]), {"B2", "B4"})      # 5 ya no es «menos de 5»
        self.assertNotIn("critico", a)

    def test_la_campana_muestra_los_niveles_y_cuenta_la_burbuja(self):
        producto("UNO", 1)
        producto("TRES", 3)
        producto("SEIS", 6)
        r = self.campana()
        self.assertContains(r, "1 producto en stock crítico (menos de 2)")
        self.assertContains(r, "1 producto en stock bajo (menos de 5)")
        self.assertContains(r, "notif-item--peligro")
        self.assertContains(r, "notif-item--aviso")
        self.assertNotContains(r, "Producto SEIS")
        self.assertEqual(r.context["total"], 2)

    # ---------- Vencimiento por lote ----------
    def test_lote_vencido_muestra_producto_lote_fecha_y_cantidad(self):
        vence = self.hoy - timedelta(days=3)
        producto("SUERO", 8, vence=vence, lote="L-VEN-01")
        a = self.alertas()
        self.assertEqual(set(a), {"vencidos"})
        self.assertEqual(a["vencidos"]["nivel"], "peligro")

        r = self.campana()
        self.assertContains(r, "1 producto vencido con unidades")
        self.assertContains(r, "Producto SUERO")
        self.assertContains(r, "Lote L-VEN-01")
        self.assertContains(r, f"venció {vence:%d/%m/%Y}")
        self.assertContains(r, "8 unidades")

    def test_lote_por_vencer_muestra_producto_lote_fecha_y_cantidad(self):
        vence = self.hoy + timedelta(days=10)
        producto("VACUNA", 12, vence=vence, lote="L-PV-07")
        a = self.alertas()
        self.assertEqual(set(a), {"por_vencer"})
        r = self.campana()
        self.assertContains(r, "Lote L-PV-07")
        self.assertContains(r, f"vence {vence:%d/%m/%Y}")
        self.assertContains(r, "12 unidades")
        self.assertEqual(r.context["total"], 0)          # «por vencer» es informativo: no suma en la burbuja

    def test_lote_agotado_no_alerta_por_vencimiento(self):
        producto("VIEJO", 0, vence=self.hoy - timedelta(days=5), lote="L-AGO")
        producto("PRONTO", 0, vence=self.hoy + timedelta(days=5), lote="L-AGO-2")
        a = self.alertas()
        self.assertNotIn("vencidos", a)
        self.assertNotIn("por_vencer", a)
        self.assertNotContains(self.campana(), "L-AGO")

    def test_lote_que_vence_despues_de_30_dias_no_alerta(self):
        producto("LEJOS", 20, vence=self.hoy + timedelta(days=31), lote="L-OK")
        self.assertEqual(self.alertas(), {})

    def test_vencidos_se_ordenan_por_fecha(self):
        producto("V2", 6, vence=self.hoy - timedelta(days=1))
        producto("V1", 6, vence=self.hoy - timedelta(days=9))
        orden = [d["producto"].codigo for d in self.alertas()["vencidos"]["productos"]]
        self.assertEqual(orden, ["V1", "V2"])

    # ---------- Detalle desde la campana ----------
    def test_cada_producto_enlaza_al_inventario_filtrado(self):
        p = producto("SUERO", 8, vence=self.hoy - timedelta(days=3), lote="L-VEN-01")
        producto("OTRO", 9, vence=self.hoy - timedelta(days=2))
        detalle = self.alertas()["vencidos"]["productos"]
        url = next(d["url"] for d in detalle if d["producto"] == p)
        self.assertEqual(url, f"{reverse('inventario:lista')}?estado=vencidos&q=SUERO")
        self.assertContains(self.campana(), url.replace("&", "&amp;"))

        lista = self.client.get(url)
        self.assertEqual([x.codigo for x in lista.context["productos"]], ["SUERO"])
        self.assertContains(lista, "Lote L-VEN-01")

    def test_la_campana_resume_lo_que_no_cabe(self):
        for i in range(5):
            producto(f"C{i}", 1)
        a = self.alertas()["critico"]
        self.assertEqual((a["total"], len(a["productos"]), a["faltan"]), (5, 3, 2))
        self.assertContains(self.campana(), "y 2 más en el inventario")

    def test_filtros_de_la_lista(self):
        producto("UNO", 1)
        producto("TRES", 3)
        producto("SEIS", 6)
        url = reverse("inventario:lista")
        codigos = lambda r: {p.codigo for p in r.context["productos"]}  # noqa: E731
        self.assertEqual(codigos(self.client.get(url, {"estado": "critico"})), {"UNO"})
        self.assertEqual(codigos(self.client.get(url, {"estado": "bajo"})), {"TRES"})
        self.assertEqual(codigos(self.client.get(url, {"estado": "reabastecer"})), {"UNO", "TRES"})
        r = self.client.get(url)
        self.assertContains(r, ">Crítico</span>")
        self.assertContains(r, ">Stock bajo</span>")

    def test_buscar_por_numero_de_lote(self):
        producto("SUERO", 8, lote="L-BUSCA-9")
        producto("GASA", 8)
        r = self.client.get(reverse("inventario:lista"), {"q": "busca-9"})
        self.assertEqual([p.codigo for p in r.context["productos"]], ["SUERO"])

    # ---------- Registrar el lote ----------
    def test_anadir_unidades_con_lote_y_fecha(self):
        p = producto("AMOX", 2, vence=self.hoy + timedelta(days=60), lote="L-VIEJO")
        nueva = self.hoy + timedelta(days=200)
        self.client.post(reverse("inventario:reposicion"), {
            "producto": p.pk, "cantidad": "10", "fecha_vencimiento": nueva.isoformat(), "numero_lote": "L-NUEVO",
        })
        p.refresh_from_db()
        self.assertEqual((p.stock_actual, p.fecha_vencimiento, p.numero_lote), (12, nueva, "L-NUEVO"))
        self.assertIn("Lote L-NUEVO", p.movimientos.latest("pk").observacion)

    def test_fecha_nueva_sin_lote_no_conserva_el_lote_anterior(self):
        p = producto("AMOX", 2, vence=self.hoy + timedelta(days=60), lote="L-VIEJO")
        registrar_entrada(p.pk, 5, fecha_vencimiento=self.hoy + timedelta(days=200))
        p.refresh_from_db()
        self.assertIsNone(p.numero_lote)

    def test_solo_lote_actualiza_el_lote(self):
        vence = self.hoy + timedelta(days=60)
        p = producto("AMOX", 2, vence=vence)
        registrar_entrada(p.pk, 5, numero_lote="  L-SOLO  ")
        p.refresh_from_db()
        self.assertEqual((p.numero_lote, p.fecha_vencimiento), ("L-SOLO", vence))

    # ---------- Avisos al descontar ----------
    def test_aviso_tras_quitar_unidades(self):
        p = producto("GASA", 4)
        r = self.client.post(reverse("inventario:salida") + f"?producto={p.pk}",
                             {"producto": p.pk, "cantidad": "3", "motivo": "USO_INTERNO"}, follow=True)
        self.assertContains(r, "quedó con 1 unidad: stock crítico (menos de 2)")
