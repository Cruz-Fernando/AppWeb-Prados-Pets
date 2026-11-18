"""
Pool de conexiones a PostgreSQL (Supabase).

Abrir una conexión nueva a Supabase cuesta ~1 s (TCP + TLS + autenticación
contra el pooler de São Paulo). Sin pool, Django abría una en cada petición.
Con el pool, las conexiones se reutilizan entre peticiones y entre hilos.

El chequeo por defecto de psycopg hace un ping (~150 ms) cada vez que se
entrega una conexión. Aquí solo se hace si la conexión estuvo inactiva más de
INACTIVIDAD_MAXIMA segundos, que es cuando de verdad pudo haberse cortado.
"""

import time

from psycopg_pool import ConnectionPool

INACTIVIDAD_MAXIMA = 60  # segundos


def comprobar_conexion(conexion):
    """Callback ``check`` del pool: se llama cada vez que una petición pide conexión."""
    ahora = time.monotonic()
    ultimo_uso = getattr(conexion, "_pp_ultimo_uso", None)
    conexion._pp_ultimo_uso = ahora
    # Recién creada (None) o usada hace poco: se entrega sin ping.
    if ultimo_uso is not None and ahora - ultimo_uso > INACTIVIDAD_MAXIMA:
        # Si falla, el pool la descarta y entrega otra.
        ConnectionPool.check_connection(conexion)
