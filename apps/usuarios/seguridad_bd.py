"""
Cierra la API de datos de Supabase sobre las tablas de la app.

Supabase publica el esquema ``public`` por HTTP (PostgREST) para los roles
``anon`` y ``authenticated``: con la URL del proyecto y la clave ``anon``, que
no es secreta, cualquiera podría leer o modificar las tablas. La app no usa
esa API; Django se conecta directo como dueño de las tablas.

Aquí se hace dos cosas:

1. Se activa RLS en todas las tablas de ``public``. Sin políticas, nadie que
   no sea el dueño (o un rol con BYPASSRLS) puede leer ni escribir. Django es
   el dueño, así que no le afecta.
2. Si existen los roles ``anon`` y ``authenticated`` (solo en Supabase), se
   les quitan los permisos sobre tablas, secuencias y funciones de ``public``,
   también para las que se creen después.

Corre después de cada ``migrate`` (ver ``UsuariosConfig.ready``), así las
tablas nuevas quedan cerradas en el siguiente deploy. También se puede correr
a mano con ``python manage.py asegurar_bd``. En un PostgreSQL sin Supabase
solo activa RLS, que no cambia nada para la app.
"""

from django.db import connections, transaction

ROLES_API = ("anon", "authenticated")
OBJETOS = ("TABLES", "SEQUENCES", "FUNCTIONS")


def asegurar_base(using="default", simular=False):
    """Activa RLS y quita permisos a los roles de la API. Devuelve un resumen.

    Con ``simular=True`` hace todo dentro de una transacción y la revierte.
    """
    conexion = connections[using]
    resumen = {"postgresql": conexion.vendor == "postgresql", "rls_activado": [],
               "tablas_ajenas": [], "roles": [], "permisos_quitados": 0}
    if not resumen["postgresql"]:
        return resumen

    with transaction.atomic(using=using), conexion.cursor() as cursor:
        # Tablas de public sin RLS. Solo el dueño puede cambiarlas.
        cursor.execute("""
            SELECT c.relname, pg_get_userbyid(c.relowner) = current_user
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') AND NOT c.relrowsecurity
            ORDER BY c.relname
        """)
        for tabla, es_dueno in cursor.fetchall():
            if not es_dueno:
                resumen["tablas_ajenas"].append(tabla)
                continue
            cursor.execute(f"ALTER TABLE public.{conexion.ops.quote_name(tabla)} ENABLE ROW LEVEL SECURITY")
            resumen["rls_activado"].append(tabla)

        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname = ANY(%s) ORDER BY rolname", [list(ROLES_API)])
        roles = [fila[0] for fila in cursor.fetchall()]
        resumen["roles"] = roles
        if roles:
            cursor.execute("""
                SELECT count(*) FROM information_schema.role_table_grants
                WHERE table_schema = 'public' AND grantee = ANY(%s)
            """, [roles])
            resumen["permisos_quitados"] = cursor.fetchone()[0]
            lista = ", ".join(conexion.ops.quote_name(r) for r in roles)
            for objeto in OBJETOS:
                cursor.execute(f"REVOKE ALL ON ALL {objeto} IN SCHEMA public FROM {lista}")
                # Lo que cree después este mismo usuario (las migraciones de Django).
                cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON {objeto} FROM {lista}")

        if simular:
            transaction.set_rollback(True, using=using)
    return resumen


def asegurar_tras_migrar(sender, using="default", verbosity=1, **kwargs):
    """Handler de ``post_migrate``."""
    resumen = asegurar_base(using=using)
    if verbosity >= 1 and (resumen["rls_activado"] or resumen["permisos_quitados"]):
        mensaje = f"  Seguridad de la base: RLS activado en {len(resumen['rls_activado'])} tablas"
        if resumen["roles"]:
            mensaje += f"; {resumen['permisos_quitados']} permisos quitados a {', '.join(resumen['roles'])}"
        print(mensaje + ".")
    if resumen["tablas_ajenas"]:
        print(f"  AVISO: {len(resumen['tablas_ajenas'])} tablas de public no son de este usuario y siguen "
              f"sin RLS: {', '.join(resumen['tablas_ajenas'])}")
