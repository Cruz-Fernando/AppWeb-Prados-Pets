from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import MascotaForm
from .models import Dueno, Mascota


class PantallaMascotaTests(TestCase):
    """Mejoras de diseño del formulario de mascota (edición vs registro, selects, fecha, columnas)."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_superuser(
            username="admin_pantallas",
            password="Clave-segura-123",
            nombre_completo="Admin Pantallas",
        )
        cls.dueno = Dueno.objects.create(
            nombre_completo="Ana Pérez", telefono="3001234567", direccion="Cúcuta"
        )
        cls.mascota = Mascota.objects.create(
            id_dueno=cls.dueno, nombre="Luna", especie="perro", peso="8.50"
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def _editar(self):
        return self.client.get(reverse("editar_mascota", args=[self.mascota.id_mascota]))

    def _registrar(self):
        return self.client.get(reverse("registrar_mascota"))

    # ── 1. La edición ya no se ve como un alta ─────────────────────────────────
    def test_editar_dice_editar_y_no_registrar(self):
        r = self._editar()
        self.assertContains(r, "<h1>Editar Mascota</h1>", html=True)
        self.assertContains(r, "Guardar Cambios")
        self.assertNotContains(r, "Registrar Nueva Mascota")
        self.assertNotContains(r, "Guardar Mascota")
        # Título de la pestaña y breadcrumb dicen "Editar" (el menú lateral conserva su enlace "Registrar Mascota")
        self.assertContains(r, "<title>Editar Mascota · Prados Pets</title>", html=True)
        self.assertContains(
            r, '<span class="app-topbar__current">Editar Mascota</span>', html=True
        )
        self.assertNotContains(
            r, '<span class="app-topbar__current">Registrar Mascota</span>', html=True
        )

    def test_editar_muestra_el_codigo_real_y_no_lo_baraja(self):
        r = self._editar()
        self.assertContains(r, self.mascota.codigo_mascota)
        # el elemento que el script barajaba solo existe al registrar
        self.assertNotContains(r, 'id="codigo-chars"')

    def test_registrar_conserva_el_codigo_que_se_genera_al_guardar(self):
        r = self._registrar()
        self.assertContains(r, "Registrar Nueva Mascota")
        self.assertContains(r, 'id="codigo-chars"')
        self.assertNotContains(r, "Editar Mascota")

    def test_editar_muestra_el_peso_para_no_borrarlo_al_guardar(self):
        r = self._editar()
        self.assertContains(r, 'name="peso"')
        self.assertContains(r, "8.50")

    def test_guardar_la_edicion_no_pierde_el_peso(self):
        self.client.post(
            reverse("editar_mascota", args=[self.mascota.id_mascota]),
            {
                "id_dueno": self.dueno.id_dueno,
                "buscar_dueno": "Ana Pérez (3001234567)",
                "nombre": "Luna",
                "especie": "perro",
                "peso": "8.50",
            },
        )
        self.mascota.refresh_from_db()
        self.assertEqual(str(self.mascota.peso), "8.50")

    def test_los_errores_generales_del_formulario_se_ven(self):
        # un error "sin campo" (p. ej. el de IntegrityError) antes no se mostraba en pantalla
        r = self.client.post(reverse("registrar_mascota"), {"nombre": "Sin dueño"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Debes seleccionar un dueño de la lista de sugerencias.")

    # ── 1c / 1d. Fecha oscura y columnas alineadas ──────────────────────────────
    def test_fecha_y_peso_tienen_estilo_oscuro_como_el_resto(self):
        r = self._editar()
        self.assertContains(r, '.app-form input[type="date"]')
        self.assertContains(r, "color-scheme: dark")

    def test_las_columnas_de_dos_campos_quedan_alineadas(self):
        r = self._editar()
        self.assertContains(r, ".form-row-2 > .form-field { margin-top: 0; }")

    # ── 2. Opciones vacías en español ─────────────────────────────────────────────
    def test_opcion_vacia_de_los_selects_esta_en_espanol(self):
        form = MascotaForm()
        self.assertEqual(form.fields["especie"].choices[0], ("", "Selecciona la especie"))
        self.assertEqual(form.fields["tamano"].choices[0], ("", "Selecciona el tamaño"))
        self.assertEqual(form.fields["sexo"].choices[0], ("", "Selecciona el sexo"))

    def test_las_opciones_reales_se_conservan(self):
        form = MascotaForm()
        self.assertEqual(
            [valor for valor, _ in form.fields["especie"].choices[1:]],
            [valor for valor, _ in Mascota.ESPECIE_CHOICES],
        )
        self.assertEqual(
            [valor for valor, _ in form.fields["sexo"].choices[1:]],
            [valor for valor, _ in Mascota.SEXO_CHOICES],
        )

    def test_no_aparece_texto_en_ingles_en_los_selects(self):
        for r in (self._registrar(), self._editar()):
            self.assertNotContains(r, "Select an option")
            self.assertContains(r, "Selecciona la especie")

    def test_especie_sigue_siendo_obligatoria(self):
        form = MascotaForm(
            data={
                "id_dueno": self.dueno.id_dueno,
                "buscar_dueno": "Ana Pérez (3001234567)",
                "nombre": "Sin especie",
                "especie": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("especie", form.errors)
