#!/usr/bin/env bash
# Copia de seguridad cifrada de la base de Prados Pets (esquema public).
#
# La corre el workflow semanal del repositorio de backups y también se puede
# correr a mano para probar. Deja en $SALIDA:
#   prados-pets-AAAA-MM-DD.dump.gpg          la copia cifrada (AES-256)
#   prados-pets-AAAA-MM-DD.dump.gpg.sha256   su suma de verificación
#   notas.md                                 el resumen para el release
#
# Variables de entorno:
#   SUPABASE_DB_URL    (obligatoria) cadena del Session pooler de Supabase
#   BACKUP_PASSPHRASE  (obligatoria) frase para cifrar, de 20 caracteres o más
#   VERIFICAR_URL      base VACÍA donde se hace una restauración de prueba;
#                      los conteos de filas salen de ahí. Si no se da, se
#                      cuentan en la base de origen.
#   SALIDA             carpeta de salida (por defecto ./salida)
#   TAMANO_MINIMO_KB   tamaño mínimo del dump sin cifrar (por defecto 100; la
#                      estructura sola, sin datos, ya pesa unos 120 KB)
#   MINIMO_DUENOS      mínimo de dueños que debe tener la copia (por defecto 1)
#
# Nunca imprime la cadena de conexión, la frase ni el contenido del dump.
# El dump sin cifrar solo existe en una carpeta temporal que se borra al
# terminar, pase lo que pase.

set -Eeuo pipefail
umask 077

TABLAS=(directorio_dueno directorio_mascota agendamiento_cita facturacion_factura inventario_producto)
SALIDA="${SALIDA:-./salida}"
TAMANO_MINIMO_KB="${TAMANO_MINIMO_KB:-100}"
MINIMO_DUENOS="${MINIMO_DUENOS:-1}"

falla() {
    echo "ERROR: $*" >&2
    if [ -n "${GITHUB_ACTIONS:-}" ]; then echo "::error::$*"; fi
    exit 1
}
paso() { printf '\n== %s\n' "$*"; }

# --- Requisitos -------------------------------------------------------------
[ -n "${SUPABASE_DB_URL:-}" ] || falla "Falta la variable SUPABASE_DB_URL."
[ -n "${BACKUP_PASSPHRASE:-}" ] || falla "Falta la variable BACKUP_PASSPHRASE."
[ "${#BACKUP_PASSPHRASE}" -ge 20 ] || falla "BACKUP_PASSPHRASE es muy corta: usa 20 caracteres o más."
for programa in psql pg_dump pg_restore gpg gpgconf sha256sum numfmt; do
    command -v "$programa" >/dev/null || falla "Falta el programa $programa."
done

tmp="$(mktemp -d)"
limpiar() {
    if [ -d "$tmp/gnupg" ]; then GNUPGHOME="$tmp/gnupg" gpgconf --kill gpg-agent 2>/dev/null || true; fi
    rm -rf "$tmp"
}
trap limpiar EXIT
trap 'exit 130' INT TERM

# --- Versión: pg_dump debe ser de la misma versión mayor que el servidor -----
paso "Versión de PostgreSQL"
servidor_num="$(psql "$SUPABASE_DB_URL" -XAtqc 'show server_version_num')" \
    || falla "No se pudo conectar a la base. Revisa SUPABASE_DB_URL (debe ser la del Session pooler, puerto 5432) y que el proyecto de Supabase no esté pausado."
servidor_mayor=$((servidor_num / 10000))
servidor_version="$(psql "$SUPABASE_DB_URL" -XAtqc "select split_part(current_setting('server_version'), ' ', 1)")"
cliente_version="$(pg_dump --version | sed -E 's/^[^0-9]*([0-9][0-9.]*).*/\1/')"
cliente_mayor="${cliente_version%%.*}"
echo "Servidor: PostgreSQL $servidor_version · pg_dump: $cliente_version"
[ "$cliente_mayor" = "$servidor_mayor" ] \
    || falla "El servidor es PostgreSQL $servidor_mayor pero pg_dump es de la versión $cliente_mayor. Instala postgresql-client-$servidor_mayor (el workflow lo hace solo)."

# --- Copia --------------------------------------------------------------------
fecha="$(TZ=America/Bogota date +%F)"
hora="$(TZ=America/Bogota date +%H:%M)"
nombre="prados-pets-$fecha"
dump="$tmp/$nombre.dump"

paso "pg_dump del esquema public"
# --no-owner y --no-privileges: la copia se puede restaurar en cualquier
# PostgreSQL, aunque no existan los roles de Supabase.
pg_dump --dbname="$SUPABASE_DB_URL" --format=custom --schema=public \
    --no-owner --no-privileges --file="$dump" \
    || falla "pg_dump falló."
bytes_dump="$(stat -c %s "$dump")"
echo "Dump sin cifrar: $(numfmt --to=iec "$bytes_dump")"

# --- Verificación ---------------------------------------------------------------
paso "Verificación de la copia"
lista="$tmp/lista.txt"
pg_restore --list "$dump" >"$lista" || falla "pg_restore no pudo leer la copia: el archivo está dañado."
for tabla in "${TABLAS[@]}"; do
    grep -qE "^[0-9]+; [0-9]+ [0-9]+ TABLE public $tabla " "$lista" || falla "La copia no tiene la tabla $tabla."
    grep -qE "^[0-9]+; [0-9]+ [0-9]+ TABLE DATA public $tabla " "$lista" || falla "La copia no tiene los datos de $tabla."
done
echo "Las ${#TABLAS[@]} tablas principales están en la copia."
[ "$bytes_dump" -ge $((TAMANO_MINIMO_KB * 1024)) ] \
    || falla "La copia pesa solo $(numfmt --to=iec "$bytes_dump"); se esperaba al menos $TAMANO_MINIMO_KB KB."

if [ -n "${VERIFICAR_URL:-}" ]; then
    paso "Restauración de prueba"
    existentes="$(psql "$VERIFICAR_URL" -XAtqc "select count(*) from pg_tables where schemaname = 'public'")" \
        || falla "No se pudo conectar a la base de VERIFICAR_URL."
    [ "$existentes" = 0 ] || falla "La base de VERIFICAR_URL debe estar vacía y tiene $existentes tablas."
    # El esquema public ya existe en cualquier base nueva: se quita de la lista
    # para que la restauración no falle con "schema public already exists".
    grep -vE '^[0-9]+; [0-9]+ [0-9]+ (SCHEMA - public|COMMENT - SCHEMA public) ' "$lista" >"$tmp/lista-restaurar.txt"
    pg_restore --no-owner --no-privileges --single-transaction --exit-on-error \
        --use-list="$tmp/lista-restaurar.txt" --dbname="$VERIFICAR_URL" "$dump" \
        || falla "La restauración de prueba falló: la copia no sirve."
    echo "La copia se restauró sin errores en una base vacía."
    base_conteo="$VERIFICAR_URL"
    origen_conteo="contadas en la restauración de prueba"
else
    base_conteo="$SUPABASE_DB_URL"
    origen_conteo="contadas en la base de origen (sin restauración de prueba)"
fi

declare -A filas
for tabla in "${TABLAS[@]}"; do
    filas[$tabla]="$(psql "$base_conteo" -XAtqc "select count(*) from public.$tabla")"
    printf '  %-22s %s filas\n' "$tabla" "${filas[$tabla]}"
done
[ "${filas[directorio_dueno]}" -ge "$MINIMO_DUENOS" ] \
    || falla "La copia tiene ${filas[directorio_dueno]} dueños; se esperaban al menos $MINIMO_DUENOS."

# --- Cifrado ------------------------------------------------------------------
paso "Cifrado (AES-256)"
mkdir -p "$SALIDA"
cifrado="$SALIDA/$nombre.dump.gpg"
# Llavero temporal y sin caché de la frase: no toca el gpg del usuario.
export GNUPGHOME="$tmp/gnupg"
mkdir -m 700 "$GNUPGHOME"
gpg_frase() {
    # La frase entra por el descriptor 3 (nunca por la línea de comandos,
    # donde la vería cualquier proceso).
    gpg --batch --yes --quiet --no-symkey-cache --pinentry-mode loopback \
        --passphrase-fd 3 "$@" 3< <(printf '%s' "$BACKUP_PASSPHRASE")
}
# El dump de formato custom ya va comprimido: no se vuelve a comprimir.
gpg_frase --symmetric --cipher-algo AES256 --compress-algo none --output "$cifrado" "$dump" \
    || falla "No se pudo cifrar la copia."

# Prueba de ida y vuelta: lo descifrado tiene que ser idéntico al dump.
suma_dump="$(sha256sum <"$dump" | cut -d' ' -f1)"
suma_descifrado="$(gpg_frase --decrypt "$cifrado" | sha256sum | cut -d' ' -f1)"
[ "$suma_dump" = "$suma_descifrado" ] || falla "La copia cifrada no se descifra igual al original."
echo "La copia cifrada se descifra bien."

(cd "$SALIDA" && sha256sum "$nombre.dump.gpg" >"$nombre.dump.gpg.sha256")
bytes_cifrado="$(stat -c %s "$cifrado")"
suma_cifrado="$(cut -d' ' -f1 "$cifrado.sha256")"

# --- Notas del release ----------------------------------------------------------
{
    echo "## Copia de seguridad del $fecha"
    echo
    echo "| Dato | Valor |"
    echo "|---|---|"
    echo "| Fecha | $fecha $hora (hora de Colombia) |"
    echo "| Archivo | \`$nombre.dump.gpg\` ($(numfmt --to=iec "$bytes_cifrado") cifrado; $(numfmt --to=iec "$bytes_dump") sin cifrar) |"
    echo "| PostgreSQL | servidor $servidor_version · pg_dump $cliente_version |"
    echo "| Contenido | esquema \`public\`, formato custom (\`pg_dump -Fc\`) |"
    echo "| Cifrado | AES-256 con gpg (frase en el secreto \`BACKUP_PASSPHRASE\`) |"
    echo "| SHA-256 | \`$suma_cifrado\` |"
    echo
    echo "### Filas por tabla ($origen_conteo)"
    echo
    echo "| Tabla | Filas |"
    echo "|---|---:|"
    for tabla in "${TABLAS[@]}"; do echo "| \`$tabla\` | ${filas[$tabla]} |"; done
    echo
    echo "No incluye los archivos subidos (MEDIA): ver el README de infra/backups."
    echo
    echo "Para restaurar: \`DATABASE_URL=... ./restaurar.sh <etiqueta>\`"
} >"$SALIDA/notas.md"

if [ -n "${GITHUB_OUTPUT:-}" ]; then echo "fecha=$fecha" >>"$GITHUB_OUTPUT"; fi
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then cat "$SALIDA/notas.md" >>"$GITHUB_STEP_SUMMARY"; fi

paso "Listo"
echo "Copia cifrada: $cifrado"
