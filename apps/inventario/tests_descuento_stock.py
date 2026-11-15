"""
PB-17 / RF10 · Descuento automático del stock por consulta y peluquería.

Criterio de aceptación: «El stock se descuenta al registrar cada consulta o servicio».
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.clinico.models import RegistroClinico
from apps.directorio.models import Dueno, Mascota
from apps.inventario.models import InsumoServicio, MovimientoInventario, Producto, StockLote
from apps.inventario.services import (
    StockInsuficiente,
    descontar_stock,
    devolver_movimientos,
    disponibilidad,
)
from apps.peluqueria.models import CitaPeluqueria
from apps.usuarios.models import Rol

Usuario = get_user_model()


def crear_usuario(username, rol):
    return Usuario.objects.create_user(
        username=username, password="Clave#12345", nombre_completo=username.title(),
        id_rol=Rol.objects.get_or_create(nombre_rol=rol)[0],
    )


def crear_producto(codigo, stock, precio="1000", minimo=2):
    return Producto.objects.create(codigo=codigo, nombre=f"Producto {codigo}",
                                   precio_venta=Decimal(precio), stock_actual=stock, stock_minimo=minimo)


def lote(producto, numero, cantidad, dias=None):
    vence = timezone.localdate() + timedelta(days=dias) if dias is not None else None
    return StockLote.objects.create(producto=producto, numero_lote=numero, cantidad=cantidad,
                                    fecha_vencimiento=vence)


class ServicioDescuentoTests(TestCase):
    """La regla del descuento: lotes por vencimiento, nunca negativo, devolución exacta."""

    def test_descuenta_primero_el_lote_que_vence_antes(self):
        p = crear_producto("AMOX", 10)
        tarde = lote(p, "L-TARDE", 4, dias=200)
        pronto = lote(p, "L-PRONTO", 3, dias=20)
        sin_fecha = lote(p, "L-SINFECHA", 3)

        mov = descontar_stock(p.pk, 5)

        p.refresh_from_db(); tarde.refresh_from_db(); pronto.refresh_from_db(); sin_fecha.refresh_from_db()
        self.assertEqual(p.stock_actual, 5)
        self.assertEqual((pronto.cantidad, tarde.cantidad, sin_fecha.cantidad), (0, 2, 3))
        self.assertEqual([u["numero"] for u in mov.lotes], ["L-PRONTO", "L-TARDE"])
        self.assertIn("lote L-PRONTO ×3", mov.observacion)
        self.assertEqual(mov.monto_total, Decimal("5000"))

    def test_no_usa_lotes_vencidos_ni_deja_stock_negativo(self):
        p = crear_producto("VAC", 5)
        lote(p, "L-VENCIDO", 3, dias=-1)
        lote(p, "L-OK", 2, dias=60)

        self.assertEqual(disponibilidad(p), (2, 3))
        with self.assertRaises(StockInsuficiente) as error:
            descontar_stock(p.pk, 3)
        self.assertIn("hay 2 disponibles", str(error.exception))
        self.assertIn("3 unidades vencidas", str(error.exception))

        p.refresh_from_db()
        self.assertEqual(p.stock_actual, 5)
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_usa_unidades_sin_lote_despues_de_los_lotes(self):
        p = crear_producto("GASA", 6)          # 2 en lote + 4 sin lote
        l = lote(p, "L1", 2, dias=90)
        mov = descontar_stock(p.pk, 5)
        p.refresh_from_db(); l.refresh_from_db()
        self.assertEqual((p.stock_actual, l.cantidad), (1, 0))
        self.assertEqual(mov.lotes, [{"lote": l.pk, "numero": "L1", "cantidad": 2}])

    def test_devolver_regresa_al_mismo_lote_una_sola_vez(self):
        p = crear_producto("SUERO", 4)
        l = lote(p, "L1", 4, dias=90)
        salida = descontar_stock(p.pk, 3)

        devolver_movimientos([salida], motivo="prueba")
        devolver_movimientos([salida], motivo="prueba otra vez")   # no duplica

        p.refresh_from_db(); l.refresh_from_db(); salida.refresh_from_db()
        self.assertEqual((p.stock_actual, l.cantidad), (4, 4))
        self.assertTrue(salida.devuelto)
        self.assertEqual(MovimientoInventario.objects.filter(tipo="ENTRADA_DEVOLUCION").count(), 1)


class DescuentoEnConsultaTests(TestCase):
    """Al registrar una consulta se descuentan los medicamentos e insumos usados."""

    @classmethod
    def setUpTestData(cls):
        cls.vet = crear_usuario("vet_stock", "veterinario")
        dueno = Dueno.objects.create(nombre_completo="Ana", telefono="3110000002", direccion="Calle 1")
        cls.mascota = Mascota.objects.create(id_dueno=dueno, nombre="Toby", especie="perro")

    def setUp(self):
        self.client.force_login(self.vet)
        self.amox = crear_producto("AMOX", 10, minimo=8)
        lote(self.amox, "A-1", 10, dias=120)
        self.jeringa = crear_producto("JER", 3)

    def _post(self, insumos):
        datos = {"fecha_atencion": "2026-11-15T09:30", "motivo": "Otitis",
                 "insumo_producto": [str(p.pk) for p, _ in insumos],
                 "insumo_cantidad": [str(c) for _, c in insumos]}
        return self.client.post(
            reverse("clinico:nuevo_registro", args=[self.mascota.id_mascota, "consulta_general"]), datos)

    def test_guardar_consulta_descuenta_y_queda_en_el_registro(self):
        respuesta = self._post([(self.amox, 2), (self.jeringa, 1), (self.amox, 1)])

        registro = RegistroClinico.objects.get()
        self.assertRedirects(respuesta, reverse("clinico:registro_detalle", args=[registro.pk]),
                             fetch_redirect_response=False)
        self.amox.refresh_from_db(); self.jeringa.refresh_from_db()
        self.assertEqual((self.amox.stock_actual, self.jeringa.stock_actual), (7, 2))
        usados = {m.producto.codigo: m.cantidad for m in registro.insumos_usados}
        self.assertEqual(usados, {"AMOX": 3, "JER": 1})          # el producto repetido se suma
        self.assertTrue(all(m.usuario == self.vet for m in registro.insumos_usados))

        detalle = self.client.get(reverse("clinico:registro_detalle", args=[registro.pk]))
        self.assertContains(detalle, "Medicamentos e insumos descontados")
        self.assertContains(detalle, "Se descontó del inventario: 3 × Producto AMOX, 1 × Producto JER.")
        self.assertContains(detalle, "quedó con 7 unidades (mínimo 8)")
        pdf = self.client.get(reverse("clinico:registro_pdf", args=[registro.pk]))
        self.assertEqual(pdf.status_code, 200)

    def test_si_no_alcanza_no_se_guarda_nada(self):
        respuesta = self._post([(self.amox, 2), (self.jeringa, 5)])

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No hay stock suficiente de «Producto JER»: pediste 5 y hay 3 disponibles.")
        self.assertFalse(RegistroClinico.objects.exists())
        self.amox.refresh_from_db()
        self.assertEqual(self.amox.stock_actual, 10)
        self.assertFalse(MovimientoInventario.objects.exists())
        self.assertContains(respuesta, "insumos-previos")        # lo escrito vuelve al formulario

    def test_cantidad_invalida_se_rechaza(self):
        respuesta = self._post([(self.amox, 0)])
        self.assertContains(respuesta, "debe ser un número entero entre 1 y 999")
        self.assertFalse(RegistroClinico.objects.exists())

    def test_consulta_sin_insumos_sigue_funcionando(self):
        self._post([])
        self.assertTrue(RegistroClinico.objects.exists())
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_anular_la_consulta_devuelve_al_inventario(self):
        self._post([(self.amox, 4)])
        registro = RegistroClinico.objects.get()

        respuesta = self.client.post(reverse("clinico:anular_registro", args=[registro.pk]),
                                     {"motivo_anulacion": "Mascota equivocada"}, follow=True)

        self.amox.refresh_from_db()
        self.assertEqual(self.amox.stock_actual, 10)
        self.assertEqual(StockLote.objects.get(numero_lote="A-1").cantidad, 10)
        self.assertContains(respuesta, "Se devolvió al inventario: 4 × Producto AMOX.")

    def test_buscador_de_productos(self):
        respuesta = self.client.get(reverse("inventario:buscar_producto"), {"q": "amo"})
        datos = respuesta.json()
        self.assertEqual(datos[0]["codigo"], "AMOX")
        self.assertEqual(datos[0]["disponible"], 10)


class DescuentoEnPeluqueriaTests(TestCase):
    """Al agendar el servicio se descuentan sus insumos; al cancelarlo vuelven."""

    @classmethod
    def setUpTestData(cls):
        cls.auxiliar = crear_usuario("aux_stock", "auxiliar")
        cls.groomer = crear_usuario("groomer_stock", "groomer")
        dueno = Dueno.objects.create(nombre_completo="Luis", telefono="3110000003", direccion="Calle 2")
        cls.mascota = Mascota.objects.create(id_dueno=dueno, nombre="Max", especie="perro",
                                             sexo="M", peso=30, tamano="grande")

    def setUp(self):
        self.client.force_login(self.auxiliar)
        self.champu = crear_producto("CHAMPU", 5)
        self.colonia = crear_producto("COLONIA", 1)
        InsumoServicio.objects.create(servicio="BANO", producto=self.champu, cantidad=1)
        InsumoServicio.objects.create(servicio="BANO", tamano="GRANDE", producto=self.champu, cantidad=2)
        InsumoServicio.objects.create(servicio="BANO", producto=self.colonia, cantidad=1)
        InsumoServicio.objects.create(servicio="CORTE", tamano="PEQUENO", producto=self.champu, cantidad=1)

    def _agendar(self, servicio="BANO", dias=2):
        fecha = (timezone.localtime() + timedelta(days=dias)).replace(hour=10, minute=0, second=0, microsecond=0)
        return self.client.post(reverse("peluqueria:guardar_cita"), {
            "mascota_id": self.mascota.pk, "servicio": servicio, "groomer_id": self.groomer.pk,
            "fecha_hora": fecha.strftime("%Y-%m-%dT%H:%M"), "duracion_min": "60", "precio": "45000",
        })

    def test_agendar_descuenta_segun_servicio_y_tamano(self):
        self._agendar()
        cita = CitaPeluqueria.objects.get()
        self.champu.refresh_from_db(); self.colonia.refresh_from_db()
        self.assertEqual((self.champu.stock_actual, self.colonia.stock_actual), (3, 0))   # GRANDE: champú ×2
        self.assertEqual({m.producto.codigo: m.cantidad for m in cita.insumos_usados},
                         {"CHAMPU": 2, "COLONIA": 1})

        panel = self.client.get(reverse("peluqueria:panel_peluqueria") + f"?descargar={cita.pk}")
        self.assertContains(panel, "Se descontó del inventario")

    def test_servicio_de_otro_tamano_no_descuenta(self):
        self._agendar(servicio="CORTE")
        self.assertTrue(CitaPeluqueria.objects.exists())
        self.champu.refresh_from_db()
        self.assertEqual(self.champu.stock_actual, 5)

    def test_si_un_insumo_no_alcanza_no_se_agenda(self):
        self._agendar(dias=2)
        respuesta = self._agendar(dias=3)          # la colonia ya se acabó
        self.assertEqual(CitaPeluqueria.objects.count(), 1)
        self.champu.refresh_from_db()
        self.assertEqual(self.champu.stock_actual, 3)
        panel = self.client.get(respuesta["Location"])
        self.assertContains(panel, "No hay stock suficiente de «Producto COLONIA»")

    def test_cancelar_la_cita_devuelve_los_insumos(self):
        self._agendar()
        cita = CitaPeluqueria.objects.get()
        cita.estado = "Cancelada"
        cita.save()
        cita.save()                                # guardar otra vez no devuelve dos veces
        self.champu.refresh_from_db(); self.colonia.refresh_from_db()
        self.assertEqual((self.champu.stock_actual, self.colonia.stock_actual), (5, 1))
        self.assertEqual(MovimientoInventario.objects.filter(tipo="ENTRADA_DEVOLUCION").count(), 2)


class ConfiguracionInsumosTests(TestCase):
    def setUp(self):
        self.producto = crear_producto("TOALLA", 10)
        self.url = reverse("inventario:insumos_peluqueria")

    def test_auxiliar_configura_actualiza_y_quita(self):
        self.client.force_login(crear_usuario("aux_cfg", "auxiliar"))
        datos = {"servicio": "BANO", "tamano": "", "producto": self.producto.pk, "cantidad": "1"}
        self.client.post(self.url, datos)
        self.client.post(self.url, {**datos, "cantidad": "3"})          # misma regla: actualiza
        insumo = InsumoServicio.objects.get()
        self.assertEqual(insumo.cantidad, 3)

        pagina = self.client.get(self.url)
        self.assertContains(pagina, "3 × Producto TOALLA")

        self.client.post(self.url, {"eliminar": insumo.pk})
        self.assertFalse(InsumoServicio.objects.exists())

    def test_cantidad_invalida_no_se_guarda(self):
        self.client.force_login(crear_usuario("aux_cfg2", "auxiliar"))
        self.client.post(self.url, {"servicio": "BANO", "tamano": "", "producto": self.producto.pk, "cantidad": "0"})
        self.assertFalse(InsumoServicio.objects.exists())

    def test_groomer_no_entra_a_configurar(self):
        self.client.force_login(crear_usuario("groomer_cfg", "groomer"))
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(reverse("inventario:buscar_producto"), {"q": "to"}).status_code, 403)