from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.directorio.models import Dueno, Mascota
from apps.usuarios.models import Rol

from .models import ConsultaMedica


class HistorialClinicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.create(nombre_rol="veterinario")
        cls.profesional = get_user_model().objects.create_user(
            username="veterinaria",
            password="prueba-segura-123",
            nombre_completo="Dra. Ana",
            id_rol=rol,
        )
        dueno = Dueno.objects.create(
            nombre_completo="Carlos Ruiz",
            telefono="3001234567",
            direccion="Cúcuta",
        )
        cls.mascota = Mascota.objects.create(
            id_dueno=dueno,
            nombre="Toby",
            especie="perro",
        )

    def setUp(self):
        self.client.force_login(self.profesional)

    def test_lista_mascotas_permite_abrir_historia(self):
        response = self.client.get(
            reverse("clinico:seleccionar_mascota_historial")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecciona una mascota")
        self.assertContains(response, "Toby")
        self.assertContains(
            response,
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota]),
        )

    def test_historial_muestra_formulario_y_estado_vacio(self):
        response = self.client.get(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anamnesis")
        self.assertContains(response, "Constantes vitales")
        self.assertContains(response, "Examen por sistemas")
        self.assertContains(response, "Esta mascota aún no tiene consultas registradas.")

    def test_consulta_se_guarda_en_historial_y_se_muestra(self):
        response = self.client.post(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota]),
            {
                "anamnesis": "Vómito desde ayer y disminución del apetito.",
                "peso": "8.50",
                "temperatura": "38.5",
                "frecuencia_cardiaca": "100",
                "frecuencia_respiratoria": "24",
                "examen_general": "Paciente alerta e hidratado.",
                "sistema_digestivo": "Dolor leve a la palpación abdominal.",
            },
        )

        self.assertRedirects(
            response,
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota]),
        )
        consulta = ConsultaMedica.objects.get(mascota=self.mascota)
        self.assertEqual(consulta.profesional, self.profesional)
        self.assertEqual(consulta.anamnesis, "Vómito desde ayer y disminución del apetito.")
        self.assertEqual(str(consulta.peso), "8.50")
        self.assertEqual(str(consulta.temperatura), "38.5")
        self.assertEqual(consulta.sistema_digestivo, "Dolor leve a la palpación abdominal.")

        historial = self.client.get(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota])
        )
        self.assertContains(historial, "Vómito desde ayer y disminución del apetito.")
        self.assertContains(historial, "38.5 °C")
        self.assertContains(historial, "Dolor leve a la palpación abdominal.")
        self.assertContains(historial, "Dra. Ana")

    def test_consulta_no_se_guarda_sin_anamnesis(self):
        response = self.client.post(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota]),
            {"anamnesis": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].has_error("anamnesis", "required"))
        self.assertFalse(ConsultaMedica.objects.exists())
