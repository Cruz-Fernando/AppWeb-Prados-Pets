#!/usr/bin/env bash
# Restaura una copia de seguridad de Prados Pets en la base de DATABASE_URL.
#
# Uso:
#   DATABASE_URL=postgresql://usuario:clave@host:5432/base ./restaurar.sh ultima
#   DATABASE_URL=... ./restaurar.sh backup-2026-11-27
#   DATABASE_URL=... ./restaurar.sh --archivo prados-pets-2026-11-27.dump.gpg
#
# Variables de entorno:
#   DATABASE_URL       (obligatoria) base destino, en formato postgresql://…
#   BACKUP_PASSPHRASE  frase de cifrado; si no está, se pide sin mostrarla
#   BACKUP_REPO        repositorio de copias (por defecto Cruz-Fernando/Prados-pets-backups)
#
# Necesita gpg, psql y un pg_restore de la misma versión mayor que la copia
# o más nuevo. Para descargar de GitHub también necesita gh con la sesión
# iniciada (gh auth login); con --archivo no hace falta.
#
# Si la base destino ya tiene tablas, pide escribir RESTAURAR antes de
# tocarla. Si es una base de Supabase, pide además escribir su host.
# La restauración va en una sola transacción: si algo falla, la base queda
# como estaba. El dump descifrado vive solo en una carpeta temporal que se
# borra al terminar, pase lo que pase.

set -Eeuo pipefail
umask 077

REPO="${BACKUP_REPO:-Cruz-Fernando/Prados-pets-backups}"
TABLAS=(directorio_dueno directorio_mascota agendamiento_cita facturacion_factura inventario_producto)

falla() { echo "ERROR: $*" >&2; exit 1; }
uso() {
    sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
}

# --- Argumentos ---------------------------------------------------------------
etiqueta=""
archivo=""
case "${1:-}" in
    "" | -h | --help) uso ;;
    --archivo)
        archivo="${2:-}"
        [ -n "$archivo" ] || uso
        [ -f "$archivo" ] || falla "No existe el archivo $archivo."
        ;;
    *) etiqueta="$1" ;;
esac

[ -n "${DATABASE_URL:-}" ] || falla "Falta la variable DATABASE_URL (base destino)."
case "$DATABASE_URL" in
    postgres://* | postgresql://*) ;;
    *) falla "DATABASE_URL debe tener el formato postgresql://usuario:clave@host:puerto/base." ;;
esac
programas=(gpg gpgconf psql pg_restore sha256sum)
if [ -n "$etiqueta" ]; then programas+=(gh); fi
for programa in "${programas[@]}"; do
    command -v "$programa" >/dev/null || falla "Falta el programa $programa."
done

tmp="$(mktemp -d)"
limpiar() {
    if [ -d "$tmp/gnupg" ]; then GNUPGHOME="$tmp/gnupg" gpgconf --kill gpg-agent 2>/dev/null || true; fi
    rm -rf "$tmp"
}
trap limpiar EXIT
trap 'exit 130' INT TERM

# --- Descarga ------------------------------------------------------------------
if [ -n "$etiqueta" ]; then
    if [ "$etiqueta" = "ultima" ]; then
        etiqueta="$(gh release list --repo "$REPO" --limit 1000 --json tagName,createdAt \
            --jq '[.[] | select(.tagName | startswith("backup-"))] | sort_by(.createdAt) | last | .tagName // empty')" \
            || falla "No se pudo consultar $REPO. ¿Iniciaste sesión con gh auth login?"
        [ -n "$etiqueta" ] || falla "No hay copias en $REPO."
    fi
    echo "Descargando $etiqueta de $REPO…"
    gh release download "$etiqueta" --repo "$REPO" --dir "$tmp/descarga" \
        --pattern '*.dump.gpg' --pattern '*.dump.gpg.sha256' \
        || falla "No se pudo descargar $etiqueta."
    cifrado="$(find "$tmp/descarga" -name '*.dump.gpg' -print -quit)"
    [ -n "$cifrado" ] || falla "El release $etiqueta no tiene un archivo .dump.gpg."
else
    cifrado="$archivo"
fi

# --- Suma de verificación --------------------------------------------------------
if [ -f "$cifrado.sha256" ]; then
    (cd "$(dirname "$cifrado")" && sha256sum --check --status "$(basename "$cifrado").sha256") \
        || falla "La suma SHA-256 no coincide: la copia está incompleta o fue alterada."
    echo "SHA-256 correcto."
else
    [ -z "$etiqueta" ] || falla "El release $etiqueta no tiene el archivo .sha256."
    echo "AVISO: no hay $cifrado.sha256; solo queda la verificación de integridad de gpg."
fi

# --- Descifrado ------------------------------------------------------------------
if [ -z "${BACKUP_PASSPHRASE:-}" ]; then
    [ -t 0 ] || falla "Define BACKUP_PASSPHRASE o corre el script en una terminal para escribir la frase."
    read -rsp "Frase de cifrado (BACKUP_PASSPHRASE): " BACKUP_PASSPHRASE
    echo
fi
export GNUPGHOME="$tmp/gnupg"
mkdir -m 700 "$GNUPGHOME"
dump="$tmp/copia.dump"
gpg --batch --yes --quiet --no-symkey-cache --pinentry-mode loopback --passphrase-fd 3 \
    --output "$dump" --decrypt "$cifrado" 3< <(printf '%s' "$BACKUP_PASSPHRASE") \
    || falla "No se pudo descifrar: la frase es incorrecta o el archivo está dañado."
unset BACKUP_PASSPHRASE
echo "Copia descifrada."

# --- Versión de pg_restore ---------------------------------------------------------
lista="$tmp/lista.txt"
pg_restore --list "$dump" >"$lista" || falla "pg_restore no pudo leer la copia."
copia_version="$(sed -nE 's/^;[[:space:]]+Dumped by pg_dump version: ([0-9][0-9.]*).*/\1/p' "$lista" | head -n1)"
local_version="$(pg_restore --version | sed -E 's/^[^0-9]*([0-9][0-9.]*).*/\1/')"
[ -n "$copia_version" ] || falla "No se pudo leer la versión de pg_dump de la copia."
if [ "${local_version%%.*}" -lt "${copia_version%%.*}" ]; then
    falla "La copia se hizo con pg_dump $copia_version y tu pg_restore es $local_version. Instala PostgreSQL ${copia_version%%.*} o más nuevo."
fi
echo "Copia hecha con pg_dump $copia_version · pg_restore local $local_version."

# --- Base destino --------------------------------------------------------------------
# Host sin usuario ni clave, solo para mostrarlo y confirmarlo.
destino_host="$(printf '%s' "$DATABASE_URL" | sed -E 's#^[a-z]+://([^@/]*@)?(\[[^]]*\]|[^:/?]*).*#\2#')"
[ -n "$destino_host" ] || destino_host="socket local"
destino_base="$(psql "$DATABASE_URL" -XAtqc 'select current_database()')" \
    || falla "No se pudo conectar a la base destino."
tablas_destino="$(psql "$DATABASE_URL" -XAtqc "select count(*) from pg_tables where schemaname = 'public'")"
echo
echo "Destino: base «$destino_base» en $destino_host ($tablas_destino tablas en public)."

if [ "$tablas_destino" -gt 0 ]; then
    echo "ATENCIÓN: la base destino NO está vacía. Las tablas de la copia se borran"
    echo "y se vuelven a crear: se pierden los datos que tengan ahora."
    read -rp "Escribe RESTAURAR para continuar: " respuesta || respuesta=""
    [ "$respuesta" = "RESTAURAR" ] || falla "Cancelado: no se tocó la base."
fi
case "$destino_host" in
    *supabase*)
        echo "ATENCIÓN: el destino es una base de Supabase."
        read -rp "Escribe el host ($destino_host) para confirmar: " respuesta || respuesta=""
        [ "$respuesta" = "$destino_host" ] || falla "Cancelado: no se tocó la base."
        ;;
esac

# --- Restauración --------------------------------------------------------------------
echo
echo "Restaurando…"
# El esquema public ya existe en cualquier base: se quita de la lista para que
# --clean no intente borrarlo ni crearlo otra vez.
grep -vE '^[0-9]+; [0-9]+ [0-9]+ (SCHEMA - public|COMMENT - SCHEMA public) ' "$lista" >"$tmp/lista-restaurar.txt"
pg_restore --clean --if-exists --no-owner --no-privileges --single-transaction --exit-on-error \
    --use-list="$tmp/lista-restaurar.txt" --dbname="$DATABASE_URL" "$dump" \
    || falla "La restauración falló y se deshizo: la base quedó como estaba."

echo "Restauración terminada. Registros:"
for tabla in "${TABLAS[@]}"; do
    printf '  %-22s %s\n' "$tabla" "$(psql "$DATABASE_URL" -XAtqc "select count(*) from public.$tabla")"
done
echo "El dump descifrado se borra ahora."
