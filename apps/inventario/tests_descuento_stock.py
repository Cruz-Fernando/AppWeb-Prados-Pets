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
from apps.inventario.models import InsumoServicio, MovimientoInventario, Producto
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


class ServicioDescuentoTests(TestCase):
    """La regla del descuento (inventario simple): resta, nunca negativo, vencido no se usa."""

    def test_descuenta_la_cantidad_y_deja_el_movimiento(self):
        p = crear_producto("AMOX", 10)
        mov = descontar_stock(p.pk, 4, observacion="Prueba")
        p.refresh_from_db()
        self.assertEqual(p.stock_actual, 6)
        self.assertEqual((mov.tipo, mov.cantidad, mov.monto_total), ("SALIDA_CLINICA", 4, Decimal("4000")))

    def test_no_deja_stock_negativo(self):
        p = crear_producto("VAC", 2)
        with self.assertRaises(StockInsuficiente) as error:
            descontar_stock(p.pk, 3)
        self.assertIn("pediste 3 y hay 2 disponibles", str(error.exception))
        p.refresh_from_db()
        self.assertEqual(p.stock_actual, 2)
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_producto_vencido_no_se_usa(self):
        p = crear_producto("SUERO", 5)
        p.fecha_vencimiento = timezone.localdate() - timedelta(days=1)
        p.save()
        self.assertEqual(disponibilidad(p), (0, 5))
        with self.assertRaises(StockInsuficiente) as error:
            descontar_stock(p.pk, 1)
        self.assertIn("está vencido", str(error.exception))

    def test_devolver_suma_una_sola_vez(self):
        p = crear_producto("GASA", 4)
        salida = descontar_stock(p.pk, 3)
        devolver_movimientos([salida], motivo="prueba")
        devolver_movimientos([salida], motivo="prueba otra vez")   # no duplica
        p.refresh_from_db(); salida.refresh_from_db()
        self.assertEqual(p.stock_actual, 4)
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
        # PB-21: la jeringa quedó con 2 (menos de 5); la amoxicilina con 7 ya no alerta
        self.assertContains(detalle, "«Producto JER» quedó con 2 unidades: stock bajo (menos de 5)")
        self.assertNotContains(detalle, "«Producto AMOX» quedó con")
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
            "condicion_pelaje": "Normal",
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