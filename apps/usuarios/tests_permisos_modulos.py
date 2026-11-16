"""Cada rol entra solo a los módulos que ve en el menú lateral."""

from django.test import TestCase

from apps.usuarios.models import Rol, Usuario

INVENTARIO = ["/inventario/", "/inventario/nuevo/", "/inventario/reposicion/",
              "/inventario/kardex/", "/inventario/exportar-excel/", "/inventario/cargar-excel/"]
CLINICO = ["/clinico/historial/", "/clinico/hospitalizacion/"]
PELUQUERIA = ["/peluqueria/", "/peluqueria/agendar/"]


class PermisosPorModuloTests(TestCase):
    def entrar(self, nombre_rol):
        rol, _ = Rol.objects.get_or_create(nombre_rol=nombre_rol)
        usuario = Usuario.objects.create_user(
            username=f"permiso_{nombre_rol}", password="Clave#12345",
            nombre_completo=nombre_rol.title(), id_rol=rol,
        )
        self.client.force_login(usuario)

    def assert_estado(self, urls, esperado):
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, esperado)

    def test_domiciliario_no_entra_a_inventario_clinico_ni_peluqueria(self):
        self.entrar("domiciliario")
        self.assert_estado(INVENTARIO + CLINICO + PELUQUERIA + ["/clinico/recordatorios/"], 403)

    def test_groomer_solo_peluqueria_y_recordatorios(self):
        self.entrar("groomer")
        self.assert_estado(INVENTARIO + CLINICO, 403)
        self.assert_estado(PELUQUERIA + ["/clinico/recordatorios/"], 200)

    def test_auxiliar_entra_a_todo_lo_operativo(self):
        self.entrar("auxiliar")
        self.assert_estado(INVENTARIO + CLINICO + PELUQUERIA + ["/clinico/recordatorios/"], 200)

    def test_veterinario_no_entra_a_peluqueria(self):
        self.entrar("veterinario")
        self.assert_estado(INVENTARIO + CLINICO, 200)
        self.assert_estado(PELUQUERIA, 403)