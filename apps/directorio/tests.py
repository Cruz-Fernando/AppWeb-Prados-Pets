from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Dueno, Mascota, Vacunacion
from .forms import MascotaForm
from apps.usuarios.models import Rol


class GestionMascotasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.create(nombre_rol="recepcion")
        cls.usuario = get_user_model().objects.create_user(
            username="recepcion",
            password="test-password",
            nombre_completo="Recepción",
            id_rol=rol,
        )
        cls.dueno = Dueno.objects.create(
            nombre_completo="Ana Pérez",
            telefono="3001234567",
            direccion="Cúcuta",
        )
        cls.mascota = Mascota.objects.create(
            id_dueno=cls.dueno,
            nombre="Luna",
            especie="perro",
            peso="8.50",
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_ruta_autocomplete_duenos_esta_registrada(self):
        self.assertEqual(reverse("autocomplete_duenos"), "/directorio/duenos/autocomplete/")

    def test_edicion_muestra_datos_existentes_y_antecedentes(self):
        response = self.client.get(
            reverse("editar_mascota", args=[self.mascota.id_mascota])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Luna")
        self.assertContains(response, "8.50")
        self.assertContains(response, "Ana Pérez (3001234567)")
        self.assertContains(response, "Antecedentes de vacunación")

    def test_edicion_actualiza_peso_y_datos_de_mascota(self):
        response = self.client.post(
            reverse("editar_mascota", args=[self.mascota.id_mascota]),
            {
                "id_dueno": self.dueno.id_dueno,
                "buscar_dueno": "Ana Pérez (3001234567)",
                "nombre": "Luna actualizada",
                "especie": "perro",
                "raza": "",
                "tamano": "",
                "sexo": "",
                "color": "",
                "fecha_nacimiento": "",
                "peso": "9.75",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.mascota.refresh_from_db()
        self.assertEqual(self.mascota.nombre, "Luna actualizada")
        self.assertEqual(str(self.mascota.peso), "9.75")

    def test_registra_antecedente_de_vacunacion(self):
        response = self.client.post(
            reverse("editar_mascota", args=[self.mascota.id_mascota]),
            {
                "guardar_vacunacion": "1",
                "vacuna": "Rabia",
                "fecha": "2026-10-20",
                "observaciones": "Aplicada en consulta",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Vacunacion.objects.get(mascota=self.mascota).vacuna,
            "Rabia",
        )

    def test_peso_debe_ser_positivo(self):
        form = MascotaForm(
            data={
                "id_dueno": self.dueno.id_dueno,
                "buscar_dueno": "Ana Pérez (3001234567)",
                "nombre": "Luna",
                "especie": "perro",
                "peso": "0",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("peso", form.errors)

    def test_busqueda_ajax_incluye_enlace_de_edicion(self):
        response = self.client.get(
            reverse("buscar_directorio"),
            {"q": "Luna"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        mascota_resultado = response.json()["mascotas"][0]
        self.assertEqual(
            mascota_resultado["url_edicion"],
            reverse("editar_mascota", args=[self.mascota.id_mascota]),
        )
