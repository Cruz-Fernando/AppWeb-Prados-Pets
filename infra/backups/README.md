# Copias de seguridad de la base de datos

Cada **viernes a las 10:00 p. m. (hora de Colombia)** un workflow de GitHub
Actions saca una copia de la base de producción en Supabase, la verifica, la
cifra y la sube como **release** al repositorio privado
`Cruz-Fernando/Prados-pets-backups`. Se conservan las **últimas 12 copias**
(unos 3 meses). No cuesta nada: usa los minutos gratis de Actions.

> [!IMPORTANT]
> **Guarda `BACKUP_PASSPHRASE` fuera de GitHub** (gestor de contraseñas y una
> copia en papel en un lugar seguro). GitHub no deja volver a leer un secreto
> después de guardarlo y **sin esa frase las copias no se pueden abrir**.

| Archivo | Para qué |
|---|---|
| `workflow.yml` | El workflow. Va en `.github/workflows/` del repo de backups |
| `respaldar.sh` | Hace la copia, la verifica y la cifra. Va en la raíz del repo de backups |
| `restaurar.sh` | Descarga una copia, la verifica, la descifra y la restaura |

## Qué hace cada semana

1. Consulta la versión de PostgreSQL de Supabase e instala el `pg_dump` de esa
   misma versión mayor. Si no coinciden, falla con un mensaje claro.
2. `pg_dump -Fc --schema=public --no-owner --no-privileges`: todas las tablas
   de Django (clientes, mascotas, citas, historia clínica, facturas,
   inventario, usuarios y sesiones).
3. Verifica la copia antes de publicarla:
   - `pg_restore --list` la lee sin errores;
   - están las tablas `directorio_dueno`, `directorio_mascota`,
     `agendamiento_cita`, `facturacion_factura` e `inventario_producto`, con sus datos;
   - pesa al menos `TAMANO_MINIMO_KB` y tiene al menos `MINIMO_DUENOS` dueños;
   - **se restaura de verdad** en un PostgreSQL vacío de la misma versión, y
     los conteos de filas salen de esa restauración.
4. La cifra con `gpg --symmetric --cipher-algo AES256` y comprueba que se
   descifra idéntica. El dump sin cifrar nunca sale del runner ni se imprime.
5. Publica el release `backup-AAAA-MM-DD` con el `.dump.gpg`, su `.sha256` y
   unas notas con fecha, tamaño, versión de PostgreSQL y filas por tabla.
6. Borra las copias más viejas (release y etiqueta) para dejar solo 12. Este
   paso solo corre si la copia nueva se publicó bien.

Si cualquier paso falla, el workflow falla y GitHub te avisa por correo.

## Instalación (una sola vez)

### 1. Crear el repositorio privado

En GitHub: **New repository** → nombre `Prados-pets-backups` → **Private** →
marca *Add a README file* → **Create repository**.

O con `gh`:

```fish
gh repo create Cruz-Fernando/Prados-pets-backups --private --add-readme
```

### 2. Copiar el workflow y el script

```fish
cd ~/Documentos/Proyectos/Veterinaria-PradosPets
git clone https://github.com/Cruz-Fernando/Prados-pets-backups.git
cd Prados-pets-backups
mkdir -p .github/workflows
cp ../AppWeb-Prados-Pets/infra/backups/workflow.yml .github/workflows/copia-semanal.yml
cp ../AppWeb-Prados-Pets/infra/backups/respaldar.sh .
git add .github/workflows/copia-semanal.yml respaldar.sh
git commit -m "Copia de seguridad semanal de la base"
git push
```

Si después cambias `workflow.yml` o `respaldar.sh` en este repo, cópialos otra
vez al repo de backups.

### 3. Crear los secretos

En el repo de backups: **Settings → Secrets and variables → Actions → New
repository secret**. O con `gh`, que pide el valor sin dejarlo en el historial
de la terminal:

```fish
gh secret set SUPABASE_DB_URL --repo Cruz-Fernando/Prados-pets-backups
gh secret set BACKUP_PASSPHRASE --repo Cruz-Fernando/Prados-pets-backups
```

**`SUPABASE_DB_URL`: la cadena del Session pooler**

En Supabase: abre el proyecto → botón **Connect** (arriba) → **Session
pooler** → copia la URI. Se ve así:

```
postgresql://postgres.<id-del-proyecto>:[YOUR-PASSWORD]@aws-0-<región>.pooler.supabase.com:5432/postgres
```

- Cambia `[YOUR-PASSWORD]` por la contraseña de la base. Si tiene caracteres
  especiales (`@ : / ? # % &`), escríbelos codificados (`@` → `%40`, etc.).
- Agrega `?sslmode=require` al final.
- **No uses la conexión directa** (`db.<id>.supabase.co`): es solo IPv6 y los
  runners de GitHub no tienen IPv6. El workflow la rechaza con un mensaje.
- Tampoco el *Transaction pooler* (puerto 6543): `pg_dump` necesita una sesión
  normal.

**`BACKUP_PASSPHRASE`: frase larga para cifrar**

Genérala, **guárdala primero en tu gestor de contraseñas** y después pégala en
el secreto:

```fish
openssl rand -base64 32
```

Si algún día la cambias, las copias anteriores siguen necesitando la frase
vieja: guarda las dos hasta que pasen 12 semanas.

### 4. Primera ejecución a mano

En el repo de backups: **Actions → Copia de seguridad semanal → Run workflow**.
O:

```fish
gh workflow run copia-semanal.yml --repo Cruz-Fernando/Prados-pets-backups
gh run watch --repo Cruz-Fernando/Prados-pets-backups
```

Revisa que en **Releases** aparezca `backup-AAAA-MM-DD` con dos archivos
(`.dump.gpg` y `.sha256`) y las notas con los conteos. Con el tamaño que
salga, ajusta `TAMANO_MINIMO_KB` en el workflow a más o menos la mitad (la
estructura sola, sin datos, ya pesa unos 120 KB; por eso el valor inicial es 100).

Para que los avisos de fallo te lleguen al correo: en GitHub, **Settings →
Notifications → System → Actions** → activa los correos de workflows
fallidos. GitHub los manda a quien hizo el último cambio en la línea `cron`.

## Cómo restaurar

Necesitas `gh`, `gpg` y PostgreSQL de la misma versión que la copia o más
nueva (la versión sale en las notas del release):

```fish
sudo pacman -S --needed postgresql github-cli
gh auth login
```

`restaurar.sh` recibe la etiqueta del release, `ultima`, o `--archivo` con
una copia ya descargada. Verifica el SHA-256, descifra (pide la frase sin
mostrarla si no está en `BACKUP_PASSPHRASE`), comprueba la versión de
`pg_restore` y restaura con `pg_restore --clean --if-exists --no-owner` en
**una sola transacción**: si algo falla, la base queda como estaba.

- Si la base destino ya tiene tablas, pide escribir `RESTAURAR`.
- Si el destino es una base de Supabase, pide además escribir su host.
- El dump descifrado se borra al terminar, aunque falle o lo canceles.

### Revisar una copia en tu PC

```fish
createdb prados_restaurada
env DATABASE_URL=postgresql://postgres@localhost:5432/prados_restaurada \
    bash infra/backups/restaurar.sh ultima

# Comprobar que la app arranca con esos datos (sin tocar tu .env):
env DB_NAME=prados_restaurada DB_USER=postgres DB_PASSWORD= DB_HOST=localhost DB_PORT=5432 \
    venv/bin/python manage.py check --database default
env DB_NAME=prados_restaurada DB_USER=postgres DB_PASSWORD= DB_HOST=localhost DB_PORT=5432 \
    venv/bin/python manage.py migrate --check

# Al terminar, bórrala: tiene datos personales reales.
dropdb prados_restaurada
```

### Recuperar producción después de un desastre

1. Saca la cadena del Session pooler del proyecto de Supabase donde vas a
   restaurar (el mismo o uno nuevo).
2. `env DATABASE_URL='<cadena>' bash infra/backups/restaurar.sh ultima`
   (pedirá `RESTAURAR` y el host).
3. Si cambiaste de proyecto, actualiza en Railway `DB_HOST`, `DB_USER`,
   `DB_PASSWORD` y `DB_NAME`, y en el repo de backups el secreto
   `SUPABASE_DB_URL`.
4. Corre la copia a mano una vez para confirmar que todo quedó bien.

## Si Supabase pausa el proyecto

El plan gratuito pausa los proyectos que pasan una semana sin actividad
(revisa la política vigente en la documentación de Supabase). Con la clínica
usando la app a diario no debería pasar, pero puede pasar en vacaciones o en
una instalación nueva.

- **Cómo se nota:** la app en Railway no conecta y el workflow de copias falla
  con «No se pudo conectar a Supabase». Te llega el correo de GitHub.
- **Qué hacer:** en el panel de Supabase abre el proyecto y pulsa **Restore
  project** (o *Resume*). Tarda unos minutos y los datos siguen ahí. Después
  corre la copia a mano.
- **Si ya no se puede reactivar** (Supabase pone un plazo): crea un proyecto
  nuevo y restaura la última copia como en *Recuperar producción*. Las copias
  no dependen de Supabase: están en GitHub.
- No cuentes con el workflow semanal para mantener el proyecto activo.

## Qué NO incluye la copia

- **Archivos subidos (MEDIA):** consentimientos, exámenes y adjuntos del
  registro clínico. Ver abajo.
- Los esquemas internos de Supabase (`auth`, `storage`, `realtime`): la app no
  los usa.
- Roles y permisos de la base (`--no-owner --no-privileges`), para poder
  restaurar en cualquier PostgreSQL.

### Riesgo con los archivos subidos

En producción Django guarda los archivos con `FileSystemStorage` en el disco
del contenedor de Railway (`MEDIA_ROOT = BASE_DIR / 'media'`). Por eso:

- **Se pierden en cada deploy.** El disco del contenedor se crea de cero cada
  vez, salvo que haya un volumen de Railway montado en `/app/media` (no se
  puede ver desde el código: revísalo en Railway).
- **No se pueden abrir en producción.** `static()` en `config/urls.py` solo
  sirve archivos con `DEBUG=True`, así que los enlaces dan 404.
- No hay forma limpia de sacarlos desde GitHub Actions, por eso la copia no
  los intenta.

Opciones:

1. **Supabase Storage con `django-storages` (S3).** Recomendada. Bucket
   privado, entra en el plan gratuito (1 GB) y se puede agregar a la copia
   semanal cifrada.
2. **Volumen de Railway** montado en `/app/media`. Los archivos sobreviven a
   los deploys, pero siguen sin servirse en producción y sacarlos para la
   copia es trabajo extra.
3. Guardarlos dentro de la base. No conviene: la base crece rápido y el plan
   gratuito de Supabase tiene 500 MB.

## Pendiente: archivos subidos a Supabase Storage

Próxima tarea, después de las copias de la base:

- [ ] Mover los archivos subidos (MEDIA) a **Supabase Storage** con
      `django-storages` (API S3).
- [ ] Que se puedan abrir en producción **con permisos por rol**, sin URLs
      públicas: son documentos clínicos. Bucket privado y una vista de Django
      que revise el rol antes de entregar el archivo (o una URL firmada de
      corta duración).
- [ ] Migrar los archivos que ya existan.
- [ ] Agregarlos a la copia semanal, también cifrados.

## Seguridad

- Las copias tienen datos personales de clientes (Ley 1581 de 2012). El repo
  de backups debe seguir **privado** y solo con acceso de quien lo necesite.
- Nunca se sube un dump sin cifrar. Si restauras una copia en tu PC, borra la
  base cuando termines.
- **Recomendado más adelante:** un usuario de solo lectura para las copias en
  vez del usuario `postgres`. No se creó porque cambia producción. En el SQL
  Editor de Supabase:

  ```sql
  create role copias_lectura login password '<clave larga>';
  grant usage on schema public to copias_lectura;
  grant select on all tables in schema public to copias_lectura;
  grant select on all sequences in schema public to copias_lectura;
  alter default privileges in schema public grant select on tables to copias_lectura;
  alter default privileges in schema public grant select on sequences to copias_lectura;
  ```

  En la cadena del pooler el usuario queda `copias_lectura.<id-del-proyecto>`.

## Cómo se probó (26/11/2026)

Con un PostgreSQL 18 local y datos ficticios (30 dueños, 60 mascotas, 60
citas, 10 facturas, 40 productos):

- `respaldar.sh`: copia, restauración de prueba con los conteos exactos,
  cifrado AES-256 y descifrado idéntico. Falla como debe si falta una tabla,
  si no hay dueños, si la copia pesa menos del mínimo o si la frase es corta.
- `restaurar.sh`: en una base vacía restaura sin preguntar; en una con datos
  pide `RESTAURAR`, con otra respuesta cancela sin tocar nada y, al aceptar,
  deja los datos exactamente como en la copia. Falla con una frase incorrecta
  o un archivo alterado. No deja archivos temporales.
- La app con la base restaurada: `check --database default` y
  `migrate --check` sin problemas, un usuario restaurado inicia sesión y la
  lista de dueños carga.
- `actionlint` y `shellcheck` sin avisos.
- Con la primera copia real (`backup-2026-11-26`, 161 KB): el workflow quedó en
  verde; `restaurar.sh ultima` la descargó, comprobó el SHA-256, la descifró y
  la restauró en un PostgreSQL 18 local. `check`, `migrate --check` y las
  páginas principales respondieron bien. Después se borró la base restaurada.

## Costos y límites

- GitHub Actions en un repo privado del plan Free: 2.000 minutos al mes. Cada
  copia tarda unos 2 o 3 minutos (≈ 12 minutos al mes).
- Cada archivo de un release puede pesar hasta 2 GB.
