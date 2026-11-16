from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import CitaForm


class ResumenYSelectsDeCitaTests(TestCase):
    """Formulario "Agendar Cita": texto del select de veterinario y badge del resumen."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_superuser(
            username="admin_citas",
            password="Clave-segura-123",
            nombre_completo="Admin Citas",
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_opcion_vacia_del_veterinario_esta_en_espanol(self):
        self.assertEqual(
            CitaForm().fields["veterinario"].empty_label, "Selecciona un veterinario"
        )

    def test_el_formulario_no_muestra_texto_en_ingles(self):
        r = self.client.get(reverse("agendamiento:agendar_cita"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Selecciona un veterinario")
        self.assertNotContains(r, "Select an option")

    def test_el_resumen_vacio_no_dice_lista_para_guardar(self):
        r = self.client.get(reverse("agendamiento:agendar_cita"))
        # El badge arranca como "Faltan datos" y sin la clase verde de "lista"
        self.assertContains(r, 'id="sum_estado"')
        self.assertContains(r, "● Faltan datos</span>")
        self.assertNotContains(r, 'class="pp-summary__status pp-summary__status--lista"')
        self.assertNotContains(r, "● Lista para guardar</span>")

    def test_el_script_solo_marca_lista_cuando_hay_todos_los_datos_obligatorios(self):
        r = self.client.get(reverse("agendamiento:agendar_cita"))
        self.assertContains(r, "function actualizarEstado()")
        for campo in ("mascota", "veterinario", "fecha", "hora de inicio", "hora de fin"):
            self.assertContains(r, f"faltan.push('{campo}')")
