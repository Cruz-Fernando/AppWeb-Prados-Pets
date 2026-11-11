<div align="center">

# 🐾 Prados Pets

### Sistema de gestión para clínica veterinaria

Directorio · Agenda · Historia clínica · Hospitalización · Peluquería · Inventario · Facturación · Reportes

![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?logo=postgresql&logoColor=white)
![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?logo=railway&logoColor=white)
![Metodología](https://img.shields.io/badge/Metodolog%C3%ADa-Scrum-7c3aed)
![Entregable](https://img.shields.io/badge/Entregable-E1-f472b6)
![Sprint](https://img.shields.io/badge/Sprint%20actual-5%20de%206-0ea5e9)

</div>

---

## 📋 Contenido

- [Acerca del proyecto](#-acerca-del-proyecto)
- [Estado actual](#-estado-actual)
- [Módulos y funcionalidades](#-módulos-y-funcionalidades)
- [Stack tecnológico](#️-stack-tecnológico)
- [Estructura del repositorio](#️-estructura-del-repositorio)
- [Cómo levantar el proyecto en local](#-cómo-levantar-el-proyecto-en-local)
- [Pruebas automatizadas](#-pruebas-automatizadas)
- [Cuentas de prueba](#-cuentas-de-prueba-solo-desarrollo)
- [Carga masiva de inventario](#-carga-masiva-de-inventario)
- [Despliegue](#️-despliegue)
- [Flujo de trabajo con Git](#-flujo-de-trabajo-con-git)
- [Product Backlog actualizado](#-product-backlog-actualizado)
- [Defectos y deuda técnica](#-defectos-y-deuda-técnica)
- [Equipo](#-equipo)
- [Cliente](#-cliente)

---

## 🩺 Acerca del proyecto

**AppWeb Prados Pets** es el sistema de gestión de la clínica veterinaria **Prados Pets** (Cúcuta). Reúne en una sola aplicación web el directorio de clientes y mascotas, la agenda de consulta y peluquería, la historia clínica, la hospitalización, el inventario, la facturación y los reportes.

Proyecto de la asignatura *Administración de Proyectos Informáticos*, entregable **E1**. Se trabaja con **Scrum**: **6 sprints de dos semanas** en **2 iteraciones**, del **14/09/2026 al 03/12/2026**.

---

## 📈 Estado actual

> Corte: **10 de noviembre de 2026**. Estamos en el **Sprint 5** (09/11 – 20/11).

| Indicador | Valor |
|---|---|
| Ítems del backlog | 21 (PB-01 a PB-21) |
| ✅ Terminados | 10 |
| ⚠️ Terminados con defecto abierto | 4 (PB-01, PB-08, PB-11, PB-14) |
| 🔄 En curso / parciales | 5 (PB-15 a PB-18, PB-21) |
| ⏳ Sin iniciar | 2 (PB-19, PB-20) |
| Horas del backlog terminadas | 453 h de 1.134 h (**40 %**); 640 h (**56 %**) si se cuentan los ítems con defecto abierto |
| Pruebas automatizadas | 93 pruebas: **78 pasan, 15 fallan** (ver [Defectos](#-defectos-y-deuda-técnica)) |

```
Sprint 1  ██████████  Cerrado      RF16, RF17   Acceso y usuarios
Sprint 2  ██████████  Cerrado      RF04         Directorio
Sprint 3  █████████░  Cerrado      RF05         Agenda y citas (cancelación de peluquería pendiente)
Sprint 4  █████████░  Cerrado      RF06, RF09, RF12  Historia clínica, carga masiva, recordatorios
Sprint 5  ███░░░░░░░  En curso     RF07, RF08, RF10, RF15
Sprint 6  █░░░░░░░░░  Por iniciar  RF13, RF14, RF11
```

---

## 🧩 Módulos y funcionalidades

| Módulo | Ruta | Qué hace hoy |
|---|---|---|
| **Usuarios y roles** | `/panel/`, `/usuarios/`, `/roles/` | Inicio y cierre de sesión, panel principal, alta/edición/baja de usuarios y roles (solo administrador). Roles: administrador, veterinario, auxiliar, groomer y domiciliario. |
| **Directorio** | `/directorio/` | Registro y edición de dueños y mascotas, código de mascota con año y mes (`AAMM`), peso y antecedentes de vacunación, búsqueda en tiempo real, listados y exportación a Excel. |
| **Agenda de consulta** | `/agendamiento/` | Calendario visual por día y semana (consulta y peluquería juntas), agendamiento con validación de cruces por veterinario, cancelación con motivo y comprobante PDF. |
| **Historia clínica** | `/clinico/historial/` | 8 tipos de registro (consulta general, vacunación, desparasitación, sedación, cirugía, eutanasia, control posoperatorio y otro), con constantes vitales, examen por sistemas, fórmula médica, adjuntos, edición/anulación con trazabilidad y PDF. |
| **Hospitalización** | `/clinico/hospitalizacion/` | Ingreso de pacientes, evolución diaria, alta con condición de salida y PDF. Se origina en la atención médica: no se agenda. |
| **Recordatorios** | `/clinico/recordatorios/` | Próximas vacunas y baños por mascota según el intervalo configurado. |
| **Peluquería** | `/peluqueria/` | Agendamiento con groomer, duración y precio, validación de cruces por groomer y comprobante PDF. |
| **Inventario** | `/inventario/` | Productos, medicamentos y servicios; lotes con vencimiento; reposición; kardex de movimientos; alerta de bajo stock; carga masiva y exportación a Excel. |
| **Facturación** | — | ⏳ Pendiente (Sprint 6). |
| **Reportes** | — | ⏳ Pendiente (Sprint 6). |

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend y frontend | Django 6.1 (Python 3.12+), arquitectura MVT, plantillas de Django + JavaScript |
| Base de datos | PostgreSQL en Supabase |
| PDF | xhtml2pdf |
| Excel | openpyxl |
| Producción | Railway + Gunicorn + WhiteNoise |
| Configuración | python-dotenv (`.env`) |
| Gestión | GitHub Issues + GitHub Projects, Scrum |

---

## 🗂️ Estructura del repositorio

```
AppWeb-Prados-Pets/
├── apps/
│   ├── usuarios/       # login, roles, permisos, panel, comando crear_usuarios_prueba
│   ├── directorio/     # dueños, mascotas, vacunación, búsqueda, exportación Excel
│   ├── agendamiento/   # citas de consulta, calendario, cancelación, PDF
│   ├── clinico/        # historia clínica, hospitalización, recordatorios, PDF
│   ├── peluqueria/     # citas de grooming y comprobante PDF
│   ├── inventario/     # productos, lotes, kardex, carga masiva Excel
│   ├── facturacion/    # (vacía, Sprint 6)
│   └── reportes/       # (vacía, Sprint 6)
├── config/
│   ├── settings/       # base.py, dev.py, prod.py
│   ├── middleware.py
│   ├── pdf.py          # utilidades comunes de PDF
│   └── urls.py
├── templates/          # una carpeta por app + base.html
├── static/             # css, js, img
├── requirements.txt    # dependencias de producción (las usa Railway)
├── requirements/       # base.txt, dev.txt, prod.txt
├── BACKLOG.md          # backlog del plan del proyecto (PGP)
├── Procfile
├── .env.example
└── manage.py
```

---

## 🚀 Cómo levantar el proyecto en local

### Requisitos

- **Python 3.12 o superior** (Django 6.1 no funciona con versiones anteriores)
- Git
- Acceso a una base PostgreSQL: la compartida en Supabase (credenciales por canal privado con el director del proyecto) o una local

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Cruz-Fernando/AppWeb-Prados-Pets.git
cd AppWeb-Prados-Pets

# 2. Crear y activar el entorno virtual
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env              # Windows: copy .env.example .env
# Completa DB_NAME, DB_USER, DB_PASSWORD y DB_HOST

# 5. Aplicar migraciones
python manage.py migrate

# 6. (Opcional) Crear las cuentas de prueba
python manage.py crear_usuarios_prueba

# 7. Levantar el servidor
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`.

> 💡 **Base local (opcional):** si no tienes acceso a Supabase, instala PostgreSQL, crea una base vacía (`createdb pradospets`) y pon en `.env`: `DB_NAME=pradospets`, `DB_USER=postgres`, `DB_PASSWORD=<tu clave>`, `DB_HOST=localhost`.

---

## 🧪 Pruebas automatizadas

```bash
python manage.py test                 # todo el proyecto
python manage.py test apps.clinico    # una sola app
```

Django crea una base de pruebas temporal, así que el usuario de la base necesita permiso para crear bases de datos.

Regla del equipo: **no se fusiona a `main` un PR que deje pruebas fallando** o con marcas de conflicto (`<<<<<<<`, `=======`, `>>>>>>>`).

---

## 👤 Cuentas de prueba (solo desarrollo)

> ⚠️ **Nunca usar en producción.** Estas contraseñas son públicas. La migración `0004_seed_usuarios_globales` solo las crea cuando `DEBUG=True`; en producción los usuarios se crean con `createsuperuser` o desde **Usuarios y Roles**.

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `administrador` | `Admin123*` |
| Veterinario | `veterinario` | `Vet123*` |
| Auxiliar | `auxiliar` | `Auxiliar123*` |
| Groomer | `groomer` | `Groomer123*` |
| Domiciliario | `domiciliario` | `Domicilio123*` |

---

## 📦 Carga masiva de inventario

**Inventario › Carga Masiva Excel** recibe un `.xlsx`. El sistema lee **solo la primera hoja**, con encabezados en la fila 1 y datos desde la fila 2, en este orden:

| Col. | Campo | Obligatorio | Aplica a |
|---|---|---|---|
| A | `Tipo` (`PRODUCTO`, `MEDICAMENTO` o `SERVICIO`) | Sí | Todos |
| B | `Codigo` (único) | Sí | Todos |
| C | `Nombre` | Sí | Todos |
| D | `Descripcion` | No | Todos |
| E | `Precio` (venta, en COP, solo números) | Sí | Todos |
| F | `StockMinimo` (5 si se deja vacío) | No | Producto, medicamento |
| G–J | `PrincipioActivo`, `Concentracion`, `Presentacion`, `RequiereReceta` (SI/NO) | No | Medicamento |
| K–M | `NumeroLote`, `FechaVencimiento` (AAAA-MM-DD), `CantidadLote` | No | Producto, medicamento |

Las filas con error se listan en pantalla y no se guardan; las demás sí. Un código que ya existe se rechaza. La plantilla se descarga desde la misma pantalla.

---

## ☁️ Despliegue

Producción en **Railway**: `https://appweb-prados-pets.up.railway.app`

El `Procfile` ejecuta en cada despliegue:

```
migrate  →  collectstatic  →  gunicorn (2 workers, timeout 120 s)
```

Variables de entorno en Railway (ver `.env.example`):

| Variable | Descripción |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
| `DJANGO_SECRET_KEY` | Clave secreta; sin ella la app no arranca |
| `DJANGO_ALLOWED_HOSTS` | Dominios separados por coma |
| `CSRF_TRUSTED_ORIGINS` | Orígenes con `https://`, separados por coma |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a Supabase |

**Antes de hacer push a `main`:** corre `python manage.py check`, `python manage.py makemigrations --check` y `python manage.py test`. Un archivo con marcas de conflicto rompe el build de Railway.

---

## 🌿 Flujo de trabajo con Git

- `main`: rama estable; es la que despliega Railway.
- Una rama por ítem o HU, creada desde `main`: `PB-15-recipe-medico`, `fix/permisos-rol`, etc.
- Se integra a `main` solo por **Pull Request**, con revisión de otra pareja y la descripción `Closes #N`.
- Antes de abrir el PR: `git pull origin main`, resolver conflictos **revisando cada bloque** y correr las pruebas.

---

## 🗃️ Product Backlog actualizado

> Actualizado al **10/11/2026** según el código de `main`. Las estimaciones, responsables y criterios de aceptación completos están en [`BACKLOG.md`](BACKLOG.md).

**Estado:** ✅ Terminado · ⚠️ Terminado con defecto abierto · 🔄 En curso · 🟡 Parcial · ⏳ Sin iniciar

### Iteración 1

| ID | Sp. | RF | Elemento | Est. (h) | Estado | Observaciones |
|:--|:-:|:--|:--|:-:|:-:|:--|
| PB-01 | 1 | RF16 | Control de acceso por rol (login y logout) | 67 | ⚠️ | Login y logout funcionan. **Defecto crítico BUG-01:** el control de permisos no reconoce el rol, así que solo el superusuario entra a los módulos protegidos. |
| PB-02 | 1 | RF17 | Gestión de usuarios y roles (solo administrador) | 57 | ✅ | Incluye protección del último administrador y de los roles base. Sus 4 pruebas fallan por BUG-01. |
| PB-03 | 2 | RF04 | Registro de propietarios | 14 | ✅ | Con listado y exportación a Excel. |
| PB-04 | 2 | RF04 | Registro de mascotas con código AAMM, peso y vacunación | 28 | ✅ | Sus pruebas fallan por BUG-01, no por la funcionalidad. |
| PB-05 | 2 | RF04 | Búsqueda en tiempo real de propietarios y mascotas | 33 | ✅ | Autocompletado AJAX. |
| PB-06 | 2 | RF04 | Edición de propietarios y mascotas | 28 | ✅ | |
| PB-07 | 3 | RF05 | Calendario diario y semanal | 57 | ✅ | Unifica consulta y peluquería. |
| PB-08 | 3 | RF05 | Citas de consulta médica | 24 | ⚠️ | **BUG-04:** `hora_fin` quedó obligatoria en la base de datos, pero la lógica asume 30 min cuando viene vacía (4 pruebas fallan). |
| PB-09 | 3 | RF05 | Citas de peluquería con groomer y duración | 28 | ✅ | Guarda duración y precio. |
| PB-10 | 3 | RF05 | Validación de cruces de veterinario y groomer | 14 | ✅ | Detecta solapamiento de rangos, no solo la misma hora. |
| PB-11 | 3 | RF05 | Cancelación de citas con motivo y liberación del horario | 28 | ⚠️ | Consulta: terminada. **Peluquería: falta la vista para cancelar** (el modelo ya tiene `estado` y `motivo_cancelacion`). |

### Iteración 2

| ID | Sp. | RF | Elemento | Est. (h) | Estado | Observaciones |
|:--|:-:|:--|:--|:-:|:-:|:--|
| PB-12 | 4 | RF06 | Consulta médica e historial clínico | 101 | ✅ | 8 tipos de registro, trazabilidad, anulación, adjuntos y PDF. Se agregó hospitalización completa. |
| PB-13 | 4 | RF09 | Carga masiva del catálogo por Excel | 93 | ✅ | Probada con 41 ítems de ejemplo sin errores. Mejora: importar categoría, proveedor, código de barras y precio de compra. |
| PB-14 | 4 | RF12 | Recordatorios de vacunación y baño | 68 | ⚠️ | Funciona. 2 pruebas fallan: una por BUG-05 y otra por BUG-06 (fecha del recordatorio). |
| PB-15 | 5 | RF07 | Récipe médico con medicamentos del catálogo | 92 | 🟡 | Existe la "Fórmula médica" como texto libre. Falta: seleccionar medicamentos del inventario, dosis e indicaciones por ítem, y PDF del récipe. |
| PB-16 | 5 | RF08 | Cobro de peluquería por raza, tamaño y pelaje, con comisión del 40 % | 67 | 🟡 | Hay tamaño, servicio y precio. Falta: condición del pelaje, tipo de corte, tabla de tarifas y cálculo de la comisión del groomer. |
| PB-17 | 5 | RF10 | Descuento automático de stock en consulta y peluquería | 75 | 🟡 | Existe `descontar_stock_consulta()` en `inventario/services.py`, pero **ninguna vista la usa todavía**. |
| PB-18 | 5 | RF15 | Clasificación por colores de clientes recurrentes | 29 | 🔄 | Solo existe el campo `es_recurrente`. Falta acordar los criterios con el patrocinador, calcularlos y mostrar los colores. |
| PB-19 | 6 | RF13 | Factura consolidada y registro de ingresos y gastos | 109 | ⏳ | La app `facturacion` está vacía. Hay modelos `Venta` y `DetalleVenta` en inventario con una migración pendiente (BUG-02). |
| PB-20 | 6 | RF14 | Reportes diarios, semanales y mensuales | 84 | ⏳ | La app `reportes` está vacía. Las exportaciones a Excel actuales pueden servir de base. |
| PB-21 | 6 | RF11 | Alertas de stock bajo y de vencimiento por lote | 38 | 🟡 | Ya hay un contador de bajo stock (stock ≤ mínimo). Falta: umbrales de 2 y 5 unidades, y alerta de vencimiento con fecha y lote. |

### Resumen por sprint

| Sprint | Fechas | RF | Horas | Avance |
|:-:|:--|:--|:-:|:--|
| 1 | 14/09 – 25/09 | RF16, RF17 | 124 | Cerrado, con BUG-01 abierto |
| 2 | 28/09 – 09/10 | RF04 | 103 | Cerrado |
| 3 | 13/10 – 23/10 | RF05 | 151 | Cerrado; falta cancelar peluquería |
| 4 | 26/10 – 06/11 | RF06, RF09, RF12 | 262 | Cerrado, con BUG-06 abierto |
| 5 | 09/11 – 20/11 | RF07, RF08, RF10, RF15 | 263 | **En curso:** 3 ítems parciales y 1 sin avance |
| 6 | 23/11 – 03/12 | RF13, RF14, RF11 | 231 | Por iniciar; PB-21 ya tiene base |

### Prioridad sugerida para lo que queda

1. **BUG-01 (permisos):** bloquea a todo el personal que no es superusuario. Es lo primero.
2. **BUG-02 a BUG-04:** migración pendiente, respaldo con datos sensibles y `hora_fin`. Todo el equipo debe partir de una base estable.
3. **PB-17 (descuento de stock):** PB-15, PB-16 y PB-19 dependen de que el inventario se mueva solo.
4. **PB-15 y PB-16:** completar el Sprint 5.
5. **PB-18:** pedir ya al patrocinador los criterios de colores para no frenar el sprint.
6. **Sprint 6:** PB-19 (factura), luego PB-20 (reportes, que se alimenta de la factura) y PB-21.

---

## 🐞 Defectos y deuda técnica

| ID | Prioridad | Descripción | Afecta | Solución propuesta |
|:--|:-:|:--|:--|:--|
| BUG-01 | 🔴 Crítica | `rol_requerido` (`apps/usuarios/permissions.py`) lee `request.user.rol`, atributo que no existe. Por eso solo el superusuario pasa y todos los demás reciben 403. Además 17 vistas piden el rol `recepcionista`, que no existe (el rol real es `auxiliar`). | PB-01, PB-02, PB-04 y 8 pruebas | Leer `request.user.id_rol.nombre_rol` y cambiar `recepcionista` por `auxiliar`. |
| BUG-02 | 🔴 Alta | Falta una migración: `makemigrations --check` detecta un cambio en `Venta.usuario` sin migrar. | Despliegue, PB-19 | `python manage.py makemigrations inventario` y subir la migración. |
| BUG-03 | 🔴 Alta | `datos_respaldo_sqlite.json` sigue en el repositorio (está en `.gitignore`, pero ya estaba versionado). Contiene hashes de contraseñas y datos de clientes. | Seguridad | `git rm --cached datos_respaldo_sqlite.json`, purgarlo del historial y cambiar las contraseñas de esos usuarios. |
| BUG-04 | 🟠 Alta | `Cita.hora_fin` es `NOT NULL`, pero el formulario y la validación tratan la hora de fin como opcional (30 min por defecto). | PB-08 y 4 pruebas | Calcular `hora_fin` en `save()` cuando venga vacía, o volver el campo `null=True`. |
| BUG-05 | 🟡 Media | Dos pruebas (`CancelarCitaRF05Tests` y la de cambio de intervalo en recordatorios) crean un rol que ya existe por la migración de roles: error de llave duplicada. | 2 pruebas | Usar `Rol.objects.get_or_create(...)` en esas pruebas. |
| BUG-06 | 🟡 Media | Para una cita ya pasada, el recordatorio muestra el 20/11 cuando la prueba espera la fecha de hoy. La prueba depende de la fecha actual. | PB-14 y 1 prueba | Revisar si el error está en el cálculo de la próxima fecha o en la prueba, y fijar la fecha en la prueba. |
| DT-01 | 🟡 Media | No hay integración continua: el 29/10 llegaron marcas de conflicto a `main` y rompieron el despliegue. | Todo el equipo | GitHub Action que corra `check`, `makemigrations --check` y `test` en cada PR. |
| DT-02 | 🟡 Media | `CitaPeluqueria` repite `nombre_mascota` y `raza` como texto además de la FK a `Mascota`. | Peluquería, reportes | Mostrar siempre los datos de la FK y retirar los campos de texto con una migración de datos. |
| DT-03 | 🟢 Baja | `requirements.txt` y `requirements/` no coinciden en versiones. | Mantenimiento | Dejar `requirements/prod.txt` como fuente y que `requirements.txt` solo contenga `-r requirements/prod.txt`. |
| DT-04 | 🟢 Baja | Pendientes del informe de QA del 28/10: desbordamiento horizontal en móvil, imágenes pesadas (logo de 80 KB mostrado a 36 px) y estilos repetidos dentro de las plantillas. | Interfaz | Ver `rediseno_gui_prados_pets.txt`. |

---

## 👥 Equipo

| Nombre | Rol |
|---|---|
| Jhojan Fernando Cruz Bulla | Director de Proyecto / Scrum Master / Fullstack |
| Oscar Enrique Arias Cardile | Líder Documental / Fullstack |
| Daniel Alejandro Pacheco Villamizar | Líder Tecnológico / Fullstack |
| Abel Stiven Ayala Llanes | Fullstack |
| Jeiner Duván Carvajal Araque | Fullstack / QA |

> Samuel Alexander García Sandoval, David Torres Ovallos y Juan Camilo Guarín Solano se retiraron del equipo en octubre de 2026.

---

## 🏥 Cliente

**Prados Pets**, clínica veterinaria de Cúcuta, representada por **Omar** (propietario), patrocinador y cliente del proyecto.