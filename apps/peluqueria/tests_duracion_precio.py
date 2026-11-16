from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.directorio.models import Dueno, Mascota
from apps.usuarios.models import Rol, Usuario

from .models import CitaPeluqueria
from .views import _etiqueta_duracion, _formatear_precio, _parsear_precio


def _usuario(username, rol):
    rol_obj, _ = Rol.objects.get_or_create(nombre_rol=rol)
    return Usuario.objects.create_user(
        username=username, password="Clave-segura-123", id_rol=rol_obj,
        nombre_completo=username.title(),
    )


class AyudantesDePeluqueriaTests(SimpleTestCase):
    def test_parsear_precio(self):
        self.assertEqual(_parsear_precio("$50.000 COP"), 50000)
        self.assertEqual(_parsear_precio("$1.250.000"), 1250000)
        self.assertEqual(_parsear_precio("75000"), 75000)
        for vacio in ("", "$", "abc", None, "$0 COP"):
            self.assertEqual(_parsear_precio(vacio), 0)

    def test_formatear_precio(self):
        self.assertEqual(_formatear_precio(1250000), "$1.250.000 COP")
        self.assertEqual(_formatear_precio(50000), "$50.000 COP")

    def test_etiqueta_duracion(self):
        self.assertEqual(_etiqueta_duracion(45), "45 minutos")
        self.assertEqual(_etiqueta_duracion(60), "1 hora")
        self.assertEqual(_etiqueta_duracion(90), "1 h 30 min")
        self.assertEqual(_etiqueta_duracion(120), "2 horas")


class DuracionYPrecioTests(TestCase):
    """La duración elegida y el precio escrito son los que se guardan (y salen en el PDF)."""

    def setUp(self):
        self.recepcion = _usuario("recep", "auxiliar")
        self.groomer = _usuario("groomer1", "groomer")
        dueno = Dueno.objects.create(nombre_completo="Ana", telefono="3001234567", direccion="Calle 1")
        self.mascota = Mascota.objects.create(
            id_dueno=dueno, nombre="Luna", especie="perro", tamano="grande"
        )
        self.client.login(username="recep", password="Clave-segura-123")
        self.manana = (timezone.localtime() + timedelta(days=1)).replace(hour=10, minute=0)

    def _datos(self, **cambios):
        datos = {
            "mascota_id": self.mascota.id_mascota,
            "servicio": "BANO",
            "groomer_id": self.groomer.pk,
            "fecha_hora": self.manana.strftime("%Y-%m-%dT%H:%M"),
            "precio": "$50.000",
            "observaciones": "",
        }
        datos.update(cambios)
        return datos

    def _guardar(self, **cambios):
        return self.client.post(reverse("peluqueria:guardar_cita"), self._datos(**cambios))

    # ── Duración ────────────────────────────────────────────────────────────────
    def test_la_duracion_elegida_se_guarda_aunque_el_tamano_sugiera_otra(self):
        self._guardar(duracion_min="45")  # la mascota es grande (sugiere 120)
        self.assertEqual(CitaPeluqueria.objects.get().duracion_estimada_min, 45)

    def test_sin_duracion_se_usa_la_sugerida_por_tamano(self):
        self._guardar()
        self.assertEqual(CitaPeluqueria.objects.get().duracion_estimada_min, 120)

    def test_duracion_invalida_se_rechaza(self):
        for valor in ("0", "10", "999", "abc", "-30", "62"):
            self._guardar(duracion_min=valor)
        self.assertEqual(CitaPeluqueria.objects.count(), 0)

    def test_la_duracion_elegida_se_usa_para_el_cruce_del_groomer(self):
        self._guardar(duracion_min="30")  # 10:00 a 10:30
        # 10:30 en punto: libre porque la primera cita duró solo 30 min (con 120 se habría cruzado)
        despues = (self.manana + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M")
        self._guardar(fecha_hora=despues, duracion_min="30")
        self.assertEqual(CitaPeluqueria.objects.count(), 2)

    # ── Precio ────────────────────────────────────────────────────────────────
    def test_el_precio_se_guarda_como_numero_de_pesos(self):
        self._guardar(precio="$1.250.000")
        self.assertEqual(CitaPeluqueria.objects.get().precio, 1250000)

    def test_precio_con_letras_sin_digitos_o_en_cero_se_rechaza(self):
        for valor in ("", "$", "abc", "$0", "0"):
            self._guardar(precio=valor)
        self.assertEqual(CitaPeluqueria.objects.count(), 0)

    def test_precio_demasiado_alto_se_rechaza(self):
        self._guardar(precio="$100.000.000")
        self.assertEqual(CitaPeluqueria.objects.count(), 0)

    # ── Pantalla ────────────────────────────────────────────────────────────────
    def test_el_panel_ofrece_la_duracion_como_campo_real_con_opciones(self):
        r = self.client.get(reverse("peluqueria:panel_peluqueria"))
        self.assertContains(r, 'name="duracion_min"')
        self.assertContains(r, '<option value="45">45 minutos</option>', html=True)
        self.assertContains(r, '<option value="120">2 horas</option>', html=True)

    def test_el_precio_no_arranca_con_un_signo_suelto_ni_total_en_cero(self):
        r = self.client.get(reverse("peluqueria:panel_peluqueria"))
        self.assertNotContains(r, 'value="$"')
        self.assertNotContains(r, ">$0 COP<")
        self.assertContains(r, "Por definir")

    def test_un_error_conserva_la_duracion_elegida(self):
        self._guardar(precio="$", duracion_min="45")
        r = self.client.get(reverse("peluqueria:panel_peluqueria"))
        self.assertContains(r, 'id="borrador-datos"')
        self.assertContains(r, '"duracion_min": "45"')
