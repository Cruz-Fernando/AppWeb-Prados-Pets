from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Rol, Usuario


def _usuario(username, rol, password="Clave-segura-123", **extra):
    rol_obj, _ = Rol.objects.get_or_create(nombre_rol=rol)
    return Usuario.objects.create_user(
        username=username, password=password, id_rol=rol_obj,
        nombre_completo=username.title(), **extra,
    )


class LoginObligatorioTests(TestCase):
    """Nadie puede entrar a una ruta escribiendo la URL sin iniciar sesión."""

    RUTAS = [
        "/panel/", "/directorio/buscar/", "/directorio/registrar-dueno/",
        "/peluqueria/", "/peluqueria/agendar/", "/peluqueria/buscar-mascota/?q=ab",
        "/agendamiento/calendario/", "/agendamiento/agendar/", "/usuarios/", "/roles/",
        "/ruta-que-no-existe/",
    ]

    def test_rutas_redirigen_al_login(self):
        for ruta in self.RUTAS:
            with self.subTest(ruta=ruta):
                r = self.client.get(ruta)
                self.assertEqual(r.status_code, 302)
                self.assertTrue(r["Location"].startswith("/login/"), r["Location"])

    def test_fetch_sin_sesion_recibe_401_json(self):
        r = self.client.get("/peluqueria/buscar-mascota/?q=ab", headers={"Sec-Fetch-Mode": "cors"})
        self.assertEqual(r.status_code, 401)
        self.assertIn("error", r.json())

    def test_login_y_estaticos_siguen_abiertos(self):
        self.assertEqual(self.client.get("/login/").status_code, 200)

    def test_con_sesion_se_puede_entrar(self):
        _usuario("ana", "auxiliar")
        self.client.login(username="ana", password="Clave-segura-123")
        self.assertEqual(self.client.get("/panel/").status_code, 200)

    def test_usuario_logueado_en_login_va_al_panel(self):
        _usuario("ana", "auxiliar")
        self.client.login(username="ana", password="Clave-segura-123")
        r = self.client.get("/login/")
        self.assertRedirects(r, "/panel/", fetch_redirect_response=False)


class LoginLimiteIntentosTests(TestCase):
    def setUp(self):
        cache.clear()
        _usuario("ana", "auxiliar")

    def test_bloquea_tras_cinco_fallos_aunque_luego_la_clave_sea_correcta(self):
        for _ in range(5):
            r = self.client.post("/login/", {"username": "ana", "password": "mala"})
            self.assertEqual(r.status_code, 200)
        r = self.client.post("/login/", {"username": "ana", "password": "Clave-segura-123"})
        self.assertEqual(r.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_correcto_reinicia_el_contador(self):
        for _ in range(3):
            self.client.post("/login/", {"username": "ana", "password": "mala"})
        r = self.client.post("/login/", {"username": "ana", "password": "Clave-segura-123"})
        self.assertEqual(r.status_code, 302)
        self.client.logout()
        for _ in range(4):
            self.client.post("/login/", {"username": "ana", "password": "mala"})
        r = self.client.post("/login/", {"username": "ana", "password": "Clave-segura-123"})
        self.assertEqual(r.status_code, 302)


class AdministradoresProtegidosTests(TestCase):
    def setUp(self):
        self.admin = _usuario("jefe", "administrador")
        self.client.login(username="jefe", password="Clave-segura-123")
        self.rol_vet = Rol.objects.get_or_create(nombre_rol="veterinario")[0]

    def test_admin_no_puede_quitarse_su_propio_rol(self):
        r = self.client.post(
            reverse("usuarios:usuario_editar", args=[self.admin.pk]),
            {"id_rol": self.rol_vet.pk, "estado": "activo"},
        )
        self.assertEqual(r.status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.id_rol.nombre_rol, "administrador")

    def test_admin_no_puede_desactivarse(self):
        r = self.client.post(
            reverse("usuarios:usuario_editar", args=[self.admin.pk]),
            {"id_rol": self.admin.id_rol_id, "estado": "inactivo"},
        )
        self.assertEqual(r.status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.estado, "activo")

    def test_no_se_puede_degradar_al_ultimo_administrador(self):
        otro = _usuario("otro", "administrador")
        # Con otro admin activo, degradar a "otro" sí se permite...
        r = self.client.post(
            reverse("usuarios:usuario_editar", args=[otro.pk]),
            {"id_rol": self.rol_vet.pk, "estado": "activo"},
        )
        self.assertEqual(r.status_code, 302)
        # ...pero si "otro" es el único admin activo restante, no
        otro.refresh_from_db()
        self.assertEqual(otro.id_rol.nombre_rol, "veterinario")

    def test_roles_base_no_se_renombran_ni_se_eliminan(self):
        rol_admin = self.admin.id_rol
        r = self.client.post(
            reverse("usuarios:rol_editar", args=[rol_admin.pk]),
            {"nombre_rol": "jefe-supremo", "descripcion": ""},
        )
        self.assertEqual(r.status_code, 200)
        rol_admin.refresh_from_db()
        self.assertEqual(rol_admin.nombre_rol, "administrador")

        r = self.client.post(reverse("usuarios:rol_eliminar", args=[rol_admin.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Rol.objects.filter(pk=rol_admin.pk).exists())


class ComandoUsuariosPruebaTests(TestCase):
    @override_settings(DEBUG=False)
    def test_se_niega_fuera_de_desarrollo(self):
        with self.assertRaises(CommandError):
            call_command("crear_usuarios_prueba")
        self.assertFalse(Usuario.objects.filter(username="administrador").exists())
