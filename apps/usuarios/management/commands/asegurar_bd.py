"""
Cierra la API de datos de Supabase sobre las tablas de la app: activa RLS en
todas las tablas de public y quita los permisos de los roles anon y
authenticated. Ver apps/usuarios/seguridad_bd.py.

    python manage.py asegurar_bd --simular   # muestra qué cambiaría, sin guardar
    python manage.py asegurar_bd
"""

from django.core.management.base import BaseCommand

from apps.usuarios.seguridad_bd import asegurar_base


class Command(BaseCommand):
    help = "Activa RLS en public y quita permisos a los roles de la API de Supabase."

    def add_arguments(self, parser):
        parser.add_argument("--simular", action="store_true",
                            help="Hace los cambios en una transacción y la revierte.")
        parser.add_argument("--database", default="default")

    def handle(self, *args, **opciones):
        r = asegurar_base(using=opciones["database"], simular=opciones["simular"])
        if not r["postgresql"]:
            self.stdout.write("La base no es PostgreSQL: no hay nada que hacer.")
            return
        prefijo = "[SIMULACIÓN, no se guardó nada] " if opciones["simular"] else ""
        self.stdout.write(f"{prefijo}RLS activado en {len(r['rls_activado'])} tablas.")
        if r["roles"]:
            self.stdout.write(f"{prefijo}Permisos quitados a {', '.join(r['roles'])}: {r['permisos_quitados']}.")
        else:
            self.stdout.write("No existen los roles anon ni authenticated (no es Supabase).")
        if r["tablas_ajenas"]:
            self.stdout.write(self.style.WARNING(
                f"{len(r['tablas_ajenas'])} tablas no son de este usuario y siguen sin RLS: "
                + ", ".join(r["tablas_ajenas"])))
