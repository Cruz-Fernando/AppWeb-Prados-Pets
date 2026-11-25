"""
PB-11 / RF05 · Cancelación de citas de peluquería desde el calendario.

Criterio de aceptación: una cita cancelada queda con su motivo y libera el
horario para una nueva cita.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.directorio.models import Dueno, Mascota
from apps.inventario.models import InsumoServicio, MovimientoInventario, Producto
from apps.usuarios.models import Rol

from .cancelacion import CancelacionNoPermitida, cancelar_cita_peluqueria
from .insumos import descontar_insumos_cita
from .models import CitaPeluqueria

Usuario = get_user_model()


def crear_usuario(username, rol):
    return Usuario.objects.create_user(
        username=username, password="Clave#12345", nombre_completo=username.title(),
        id_rol=Rol.objects.get_or_create(nombre_rol=rol)[0],
    )


class CancelarCitaPeluqueriaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario("admin_cancel", "administrador")
        cls.auxiliar = crear_usuario("aux_cancel", "auxiliar")
        cls.groomer = crear_usuario("groomer_cancel", "groomer")
        cls.otro_groomer = crear_usuario("otro_groomer_cancel", "groomer")
        cls.veterinario = crear_usuario("vet_cancel", "veterinario")
        dueno = Dueno.objects.create(nombre_completo="Marta Díaz", telefono="3110000009", direccion="Calle 9")
        cls.mascota = Mascota.objects.create(id_dueno=dueno, nombre="Kira", especie="perro",
                                             sexo="F", peso=8, tamano="pequeno")

    def setUp(self):
        self.champu = Producto.objects.create(codigo="CHAMPU_C", nombre="Champú", precio_venta=Decimal("1000"),
                                              stock_actual=5, stock_minimo=1)
        InsumoServicio.objects.create(servicio="BANO", producto=self.champu, cantidad=2)
        self.inicio = (timezone.localtime() + timedelta(days=2)).replace(hour=10, minute=0, second=0,
                                                                         microsecond=0)
        self.cita = CitaPeluqueria.objects.create(
            mascota=self.mascota, nombre_mascota="Kira", raza="Criollo", tamano="PEQUENO", servicio="BANO",
            fecha_hora=self.inicio, duracion_estimada_min=60, precio=40000, groomer=self.groomer,
        )
        descontar_insumos_cita(self.cita)
        self.url = reverse("peluqueria:cancelar_cita", args=[self.cita.pk])

    def _cancelar(self, usuario, motivo="El dueño no puede asistir", **extra):
        self.client.force_login(usuario)
        return self.client.post(self.url, {"motivo_cancelacion": motivo, **extra})

    def _estado(self):
        self.cita.refresh_from_db()
        return self.cita.estado

    # ---------- Cancelar con motivo ----------
    def test_cancelar_con_motivo_guarda_estado_y_motivo(self):
        r = self._cancelar(self.auxiliar)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self._estado(), "Cancelada")
        self.assertEqual(self.cita.motivo_cancelacion, "El dueño no puede asistir")

    def test_pueden_cancelar_administrador_y_groomer_de_la_cita(self):
        for usuario in (self.admin, self.groomer):
            with self.subTest(usuario=usuario.username):
                CitaPeluqueria.objects.filter(pk=self.cita.pk).update(estado="Programada")
                self._cancelar(usuario)
                self.assertEqual(self._estado(), "Cancelada")

    # ---------- Sin motivo ----------
    def test_sin_motivo_no_cancela(self):
        r = self._cancelar(self.auxiliar, motivo="   ")
        self.assertEqual(self._estado(), "Programada")
        mensajes = [str(m) for m in r.wsgi_request._messages]
        self.assertIn("Debes indicar el motivo de la cancelación.", mensajes)

    def test_motivo_demasiado_largo_no_cancela(self):
        self._cancelar(self.auxiliar, motivo="x" * 256)
        self.assertEqual(self._estado(), "Programada")

    # ---------- Permisos ----------
    def test_otro_groomer_recibe_403(self):
        r = self._cancelar(self.otro_groomer)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self._estado(), "Programada")

    def test_veterinario_recibe_403(self):
        r = self._cancelar(self.veterinario)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self._estado(), "Programada")

    def test_requiere_login_y_post(self):
        r = self.client.post(self.url, {"motivo_cancelacion": "x"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])
        self.client.force_login(self.auxiliar)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self._estado(), "Programada")

    # ---------- Ya cancelada o ya cerrada ----------
    def test_no_cancela_dos_veces_y_conserva_el_primer_motivo(self):
        self._cancelar(self.auxiliar, motivo="Primero")
        self._cancelar(self.auxiliar, motivo="Segundo")
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.motivo_cancelacion, "Primero")

    def test_no_cancela_una_cita_realizada(self):
        CitaPeluqueria.objects.filter(pk=self.cita.pk).update(estado="Realizada")
        self._cancelar(self.auxiliar)
        self.assertEqual(self._estado(), "Realizada")
        self.assertFalse(self.cita.motivo_cancelacion)
        with self.assertRaises(CancelacionNoPermitida):
            cancelar_cita_peluqueria(self.cita, "x")

    # ---------- Insumos ----------
    def test_devuelve_los_insumos_al_inventario(self):
        self.champu.refresh_from_db()
        self.assertEqual(self.champu.stock_actual, 3)
        self._cancelar(self.auxiliar)
        self._cancelar(self.auxiliar)                 # el segundo intento no devuelve otra vez
        self.champu.refresh_from_db()
        self.assertEqual(self.champu.stock_actual, 5)
        self.assertEqual(MovimientoInventario.objects.filter(tipo="ENTRADA_DEVOLUCION").count(), 1)

    # ---------- Horario liberado ----------
    def test_el_horario_queda_libre_para_otra_cita(self):
        datos = {
            "mascota_id": self.mascota.pk, "servicio": "BANO", "groomer_id": self.groomer.pk,
            "fecha_hora": self.inicio.strftime("%Y-%m-%dT%H:%M"), "duracion_min": "60",
            "precio": "40000", "condicion_pelaje": "Normal",
        }
        self.client.force_login(self.auxiliar)
        self.client.post(reverse("peluqueria:guardar_cita"), datos)
        self.assertEqual(CitaPeluqueria.objects.count(), 1)      # ocupado: no agenda

        self._cancelar(self.auxiliar)
        self.client.post(reverse("peluqueria:guardar_cita"), datos)
        nueva = CitaPeluqueria.objects.exclude(pk=self.cita.pk).get()
        self.assertEqual((nueva.estado, nueva.fecha_hora, nueva.groomer), ("Programada", self.inicio, self.groomer))

    # ---------- Calendario ----------
    def _calendario(self, usuario):
        self.client.force_login(usuario)
        url = reverse("agendamiento:calendario") + f"?vista=dia&fecha={self.inicio.date().isoformat()}"
        return self.client.get(url).content.decode()

    def test_calendario_ofrece_cancelar_solo_a_quien_puede(self):
        html = self._calendario(self.groomer)
        self.assertIn(f'data-cancelar-url="{self.url}"', html)
        self.assertIn('data-cancelable="1"', html)

        html = self._calendario(self.otro_groomer)
        self.assertNotIn(f'data-cancelar-url="{self.url}"', html)
        self.assertIn('data-cancelable="0"', html)

    def test_calendario_muestra_la_cancelada_con_su_motivo(self):
        self._cancelar(self.auxiliar, motivo="Lluvia fuerte")
        html = self._calendario(self.auxiliar)
        self.assertIn("cal-event--cancelada", html)
        self.assertIn('data-motivo="Lluvia fuerte"', html)
        self.assertIn('data-cancelable="0"', html)
