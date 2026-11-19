<div align="center">

# 🐾 Prados Pets

### Sistema de gestión para clínica veterinaria

Directorio · Agenda · Historia clínica · Récipe · Hospitalización · Peluquería · Inventario · Facturación · Reportes

![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?logo=postgresql&logoColor=white)
![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?logo=railway&logoColor=white)
![Metodología](https://img.shields.io/badge/Metodolog%C3%ADa-Scrum-7c3aed)
![Entregable](https://img.shields.io/badge/Entregable-E1-f472b6)
![Sprint](https://img.shields.io/badge/Sprint%20actual-5%20de%206-0ea5e9)
![Pruebas](https://img.shields.io/badge/Pruebas-216%20pasan-22c55e)

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

**AppWeb Prados Pets** es el sistema de gestión de la clínica veterinaria **Prados Pets** (Cúcuta). Reúne en una sola aplicación web el directorio de clientes y mascotas, la agenda de consulta y peluquería, la historia clínica con récipe médico, la hospitalización, el inventario con descuento automático de stock, la facturación y los reportes.

Proyecto de la asignatura *Administración de Proyectos Informáticos*, entregable **E1**. Se trabaja con **Scrum**: **6 sprints de dos semanas** en **2 iteraciones**, del **14/09/2026 al 03/12/2026**.

---

## 📈 Estado actual

> Corte: **19 de noviembre de 2026**. Estamos en el **Sprint 5** (09/11 – 20/11).

| Indicador | Valor |
|---|---|
| Ítems del backlog | 21 (PB-01 a PB-21) |
| ✅ Terminados | 16 |
| 🟡 Parciales | 4 (PB-11, PB-19, PB-20, PB-21) |
| ⏳ Sin iniciar | 1 (PB-18, solo existe el campo `es_recurrente`) |
| Horas del backlog terminadas | **846 h de 1.134 h (75 %)** |
| Pruebas automatizadas | **216 pruebas: todas pasan** |
| Chequeos de Django | `check` sin errores y `makemigrations --check` sin migraciones pendientes |

```
Sprint 1  ██████████  Cerrado      RF16, RF17          Acceso y usuarios
Sprint 2  ██████████  Cerrado      RF04                Directorio
Sprint 3  █████████░  Cerrado      RF05                Agenda y citas (cancelar peluquería solo desde Facturación)
Sprint 4  ██████████  Cerrado      RF06, RF09, RF12    Historia clínica, carga masiva, recordatorios
Sprint 5  ████████░░  En curso     RF07, RF08, RF10, RF15   Falta PB-18 (colores de clientes)
Sprint 6  ████░░░░░░  Adelantado   RF13, RF14, RF11    Ganancias por groomer y alertas de inventario ya funcionan
```

### Cambios desde el corte anterior (10/11)

- **BUG-01 corregido:** los permisos ya leen el rol desde `id_rol.nombre_rol` y `recepcionista` se traduce a `auxiliar`. Todo el personal entra a sus módulos.
- **BUG-02, BUG-04, BUG-05 y BUG-06 corregidos:** ya no hay migraciones pendientes y todas las pruebas pasan.
- **PB-15 (récipe médico):** medicamentos del inventario con dosis, frecuencia, duración e indicaciones, y PDF del récipe.
- **PB-17 (descuento de stock):** el inventario se descuenta solo en consulta y en peluquería, y se devuelve si la cita de peluquería se cancela.
- **Facturación:** panel de ganancias por groomer (comisión del 40 %), cierre de servicios y exportación a Excel.
- **Notificaciones:** campana en la barra superior con recordatorios por avisar y alertas de inventario.
- **WhatsApp:** mensajes listos (enlaces `wa.me`) para recordatorios y confirmación de citas de peluquería, con un PDF para el cliente que se abre sin iniciar sesión.
- **Rendimiento:** pool de conexiones a Supabase y menos consultas por página (de ~2 s a ~0,5 s), imágenes WebP y pantalla de carga.

---

## 🧩 Módulos y funcionalidades

| Módulo | Ruta | Qué hace hoy |
|---|---|---|
| **Usuarios y roles** | `/panel/`, `/usuarios/`, `/roles/` | Inicio y cierre de sesión, panel principal, alta/edición/baja de usuarios y roles (solo administrador), protección del último administrador y de los roles base. Roles: administrador, veterinario, auxiliar, groomer y domiciliario. |
| **Notificaciones** | `/notificaciones/` | Campana en la barra superior, según el rol: recordatorios de vacunación y baño por avisar (de hoy o atrasados) y alertas de inventario (agotados, en stock mínimo, vencidos y por vencer en 30 días). Se carga después de la página para no retrasarla. |
| **Directorio** | `/directorio/` | Registro y edición de dueños y mascotas, código de mascota con año y mes (`AAMM`), peso y antecedentes de vacunación, búsqueda en tiempo real, listados y exportación a Excel. |
| **Agenda de consulta** | `/agendamiento/` | Calendario visual por día y semana (consulta y peluquería juntas), agendamiento con validación de cruces por veterinario, cancelación con motivo y comprobante PDF. |
| **Historia clínica** | `/clinico/historial/` | 8 tipos de registro (consulta general, vacunación, desparasitación, sedación, cirugía, eutanasia, control posoperatorio y otro), con constantes vitales, examen por sistemas, adjuntos, edición/anulación con trazabilidad y PDF. Los medicamentos e insumos usados se descuentan del inventario en la misma transacción. |
| **Récipe médico** | `/clinico/registro/<id>/receta/pdf/` | Medicamentos del catálogo con dosis, frecuencia, duración e indicaciones por ítem, asociados al registro clínico, con PDF del récipe. |
| **Hospitalización** | `/clinico/hospitalizacion/` | Ingreso de pacientes, evolución diaria, alta con condición de salida y PDF. Se origina en la atención médica: no se agenda. |
| **Recordatorios** | `/clinico/recordatorios/` | Próximas vacunas y baños por mascota según el intervalo configurado en la cita. Se marcan como avisados y, mientras no se marquen, siguen apareciendo unos días para que no se pierdan. Mensaje de WhatsApp listo para enviar. |
| **Peluquería** | `/peluqueria/` | Agendamiento con groomer, raza, tamaño, condición del pelaje, tipo de servicio, duración y precio; comisión del 40 % calculada; validación de cruces por groomer; descuento de insumos; comprobante PDF interno y PDF de confirmación para el cliente por WhatsApp. |
| **Inventario** | `/inventario/` | Productos, medicamentos y servicios; lotes con vencimiento; reposición y salidas manuales con motivo; retiro y reactivación de productos; kardex de movimientos; insumos de peluquería; indicadores de bajo stock y vencimiento; carga masiva y exportación a Excel. |
| **Facturación** | `/facturacion/` | Ganancias por groomer por periodo (hoy, semana, mes, mes anterior o rango): servicios ganados, por cerrar y agendados. El administrador y el auxiliar cierran servicios como realizados o cancelados. Exportación a Excel. El groomer solo ve lo suyo. **Falta la factura consolidada y el registro de gastos.** |
| **Reportes** | — | ⏳ Pendiente (Sprint 6). Las comisiones por groomer ya salen en Facturación. |

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend y frontend | Django 6.1 (Python 3.12+), arquitectura MVT, plantillas de Django + JavaScript |
| Base de datos | PostgreSQL en Supabase, con pool de conexiones (`psycopg-pool`) |
| PDF | xhtml2pdf |
| Excel | openpyxl |
| Mensajería | Enlaces de WhatsApp (`wa.me`) con el mensaje ya escrito |
| Producción | Railway + Gunicorn + WhiteNoise |
| Configuración | python-dotenv (`.env`) |
| Gestión | GitHub Issues + GitHub Projects, Scrum |

---

## 🗂️ Estructura del repositorio

```
AppWeb-Prados-Pets/
├── apps/
│   ├── usuarios/       # login, roles, permisos, panel, notificaciones, comando crear_usuarios_prueba
│   ├── directorio/     # dueños, mascotas, vacunación, búsqueda, exportación Excel
│   ├── agendamiento/   # citas de consulta, calendario, cancelación, PDF
│   ├── clinico/        # historia clínica, récipe, hospitalización, recordatorios, insumos, PDF
│   ├── peluqueria/     # citas de grooming, comisión, insumos, confirmación al cliente, PDF
│   ├── inventario/     # productos, lotes, kardex, servicios de stock, carga masiva Excel
│   ├── facturacion/    # ganancias por groomer, cierre de servicios, exportación Excel
│   └── reportes/       # (vacía, Sprint 6)
├── config/
│   ├── settings/       # base.py, dev.py, prod.py
│   ├── db.py           # pool de conexiones a Supabase
│   ├── middleware.py   # exige login en todas las rutas
│   ├── pdf.py          # utilidades comunes de PDF
│   ├── whatsapp.py     # enlaces wa.me
│   └── urls.py
├── templates/          # una carpeta por app + base.html
├── static/             # css, js, img (WebP en pantallas, PNG en PDF), plantilla de Excel
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

> 💡 **Pool de conexiones:** cada proceso abre como máximo 4 conexiones (variable `DB_POOL_MAX`). El pooler de Supabase limita las conexiones totales y todo el equipo comparte la misma base, así que no conviene subirlo.

---

## 🧪 Pruebas automatizadas

```bash
python manage.py test                 # todo el proyecto (216 pruebas)
python manage.py test apps.clinico    # una sola app
```

Django crea una base de pruebas temporal, así que el usuario de la base necesita permiso para crear bases de datos. Con una base PostgreSQL local la batería completa tarda menos de un minuto.

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
| `DB_POOL_MAX` | (Opcional) conexiones máximas por proceso; 4 por defecto |

**Antes de hacer push a `main`:** corre `python manage.py check`, `python manage.py makemigrations --check` y `python manage.py test`. Un archivo con marcas de conflicto rompe el build de Railway.

---

## 🌿 Flujo de trabajo con Git

- `main`: rama estable; es la que despliega Railway.
- Una rama por ítem o HU, creada desde `main`: `PB-18-colores-clientes`, `fix/cancelar-peluqueria`, etc.
- Se integra a `main` solo por **Pull Request**, con revisión de otra pareja y la descripción `Closes #N`.
- Antes de abrir el PR: `git pull origin main`, resolver conflictos **revisando cada bloque** y correr las pruebas.
- Si dos ramas crean migraciones en la misma app, crea la migración de fusión con `python manage.py makemigrations --merge` y súbela en el mismo PR.

---

## 🗃️ Product Backlog actualizado

> Actualizado al **19/11/2026** según el código de `main`. Las estimaciones, responsables y criterios de aceptación completos están en [`BACKLOG.md`](BACKLOG.md).

**Estado:** ✅ Terminado · 🟡 Parcial · ⏳ Sin iniciar

### Iteración 1

| ID | Sp. | RF | Elemento | Est. (h) | Estado | Observaciones |
|:--|:-:|:--|:--|:-:|:-:|:--|
| PB-01 | 1 | RF16 | Control de acceso por rol (login y logout) | 67 | ✅ | BUG-01 corregido: cada rol entra solo a sus módulos. |
| PB-02 | 1 | RF17 | Gestión de usuarios y roles (solo administrador) | 57 | ✅ | Incluye protección del último administrador y de los roles base. |
| PB-03 | 2 | RF04 | Registro de propietarios | 14 | ✅ | Con listado y exportación a Excel. |
| PB-04 | 2 | RF04 | Registro de mascotas con código AAMM, peso y vacunación | 28 | ✅ | |
| PB-05 | 2 | RF04 | Búsqueda en tiempo real de propietarios y mascotas | 33 | ✅ | Autocompletado AJAX. |
| PB-06 | 2 | RF04 | Edición de propietarios y mascotas | 28 | ✅ | |
| PB-07 | 3 | RF05 | Calendario diario y semanal | 57 | ✅ | Unifica consulta y peluquería. |
| PB-08 | 3 | RF05 | Citas de consulta médica | 24 | ✅ | BUG-04 resuelto: si la hora de fin viene vacía, se completa con 30 min al guardar. |
| PB-09 | 3 | RF05 | Citas de peluquería con groomer y duración | 28 | ✅ | Guarda duración y precio. |
| PB-10 | 3 | RF05 | Validación de cruces de veterinario y groomer | 14 | ✅ | Detecta solapamiento de rangos, no solo la misma hora. |
| PB-11 | 3 | RF05 | Cancelación de citas con motivo y liberación del horario | 28 | 🟡 | Consulta: terminada (desde el calendario). Peluquería: solo se cancela desde **Facturación** al cerrar el servicio, y los insumos vuelven al inventario. **Falta cancelarla desde el calendario o la agenda de peluquería.** |

### Iteración 2

| ID | Sp. | RF | Elemento | Est. (h) | Estado | Observaciones |
|:--|:-:|:--|:--|:-:|:-:|:--|
| PB-12 | 4 | RF06 | Consulta médica e historial clínico | 101 | ✅ | 8 tipos de registro, trazabilidad, anulación, adjuntos y PDF. Se agregó hospitalización completa. |
| PB-13 | 4 | RF09 | Carga masiva del catálogo por Excel | 93 | ✅ | Probada con 41 ítems de ejemplo sin errores. Mejora posible: importar categoría, proveedor, código de barras y precio de compra. |
| PB-14 | 4 | RF12 | Recordatorios de vacunación y baño | 68 | ✅ | Con marca de "avisado", aviso en la campana y mensaje de WhatsApp. |
| PB-15 | 5 | RF07 | Récipe médico con medicamentos del catálogo | 92 | ✅ | Modelo `RecetaItem`: medicamento del inventario, dosis, frecuencia, duración e indicaciones por ítem; PDF del récipe asociado al registro clínico. |
| PB-16 | 5 | RF08 | Cobro de peluquería por raza, tamaño y pelaje, con comisión del 40 % | 67 | ✅ | Registra mascota, raza, tamaño, condición del pelaje, tipo de servicio/corte, groomer, precio y comisión del 40 %. |
| PB-17 | 5 | RF10 | Descuento automático de stock en consulta y peluquería | 75 | ✅ | Se descuenta al guardar el registro clínico o la cita (si no alcanza, no se guarda nada) y se devuelve al cancelar una cita de peluquería. Queda en el kardex. |
| PB-18 | 5 | RF15 | Clasificación por colores de clientes recurrentes | 29 | ⏳ | Solo existe el campo `es_recurrente` (sin uso). Falta acordar los criterios con el patrocinador, calcularlos y mostrar los colores. |
| PB-19 | 6 | RF13 | Factura consolidada y registro de ingresos y gastos | 109 | 🟡 | Ya hay panel de ganancias de peluquería por groomer. Faltan la factura que sume consulta, peluquería y productos, y el registro de gastos (arriendo, etc.). Los modelos `Venta` y `DetalleVenta` de inventario sirven de base. |
| PB-20 | 6 | RF14 | Reportes diarios, semanales y mensuales | 84 | 🟡 | Las comisiones por groomer por periodo ya salen en Facturación. Faltan rotación de productos, vencimientos y balance de ganancias o pérdidas. La app `reportes` sigue vacía. |
| PB-21 | 6 | RF11 | Alertas de stock bajo y de vencimiento por lote | 38 | 🟡 | La campana avisa productos agotados, en stock mínimo, vencidos y por vencer en 30 días. Falta usar los umbrales de 2 y 5 unidades del acta y mostrar el lote en la alerta. |

### Resumen por sprint

| Sprint | Fechas | RF | Horas | Avance |
|:-:|:--|:--|:-:|:--|
| 1 | 14/09 – 25/09 | RF16, RF17 | 124 | Cerrado |
| 2 | 28/09 – 09/10 | RF04 | 103 | Cerrado |
| 3 | 13/10 – 23/10 | RF05 | 151 | Cerrado; falta cancelar peluquería desde la agenda |
| 4 | 26/10 – 06/11 | RF06, RF09, RF12 | 262 | Cerrado |
| 5 | 09/11 – 20/11 | RF07, RF08, RF10, RF15 | 263 | **En curso:** 3 de 4 ítems terminados; falta PB-18 |
| 6 | 23/11 – 03/12 | RF13, RF14, RF11 | 231 | Adelantado: PB-19, PB-20 y PB-21 ya tienen base funcional |

### Prioridad sugerida para lo que queda

1. **BUG-03 (seguridad):** sacar del repositorio el respaldo con sesiones y hashes de contraseñas.
2. **PB-18:** pedir ya al patrocinador los criterios de colores para cerrar el Sprint 5 el 20/11.
3. **PB-11:** botón para cancelar citas de peluquería desde el calendario, con motivo (el modelo y la devolución de insumos ya existen).
4. **PB-19:** factura consolidada y gastos; es la base de los reportes.
5. **PB-20:** reportes de rotación, vencimientos y balance, alimentados por la factura.
6. **PB-21:** umbrales de 2 y 5 unidades y lote en la alerta.
7. **DT-01:** integración continua para no volver a romper `main`.

---

## 🐞 Defectos y deuda técnica

### Abiertos

| ID | Prioridad | Descripción | Afecta | Solución propuesta |
|:--|:-:|:--|:--|:--|
| BUG-03 | 🔴 Alta | `datos_respaldo_sqlite.json` sigue en el repositorio (está en `.gitignore`, pero ya estaba versionado). Contiene sesiones, hashes de contraseñas y datos de clientes. | Seguridad | `git rm --cached datos_respaldo_sqlite.json`, purgarlo del historial y cambiar las contraseñas de esos usuarios. |
| DT-01 | 🟡 Media | No hay integración continua: el 29/10 llegaron marcas de conflicto a `main` y rompieron el despliegue. | Todo el equipo | GitHub Action que corra `check`, `makemigrations --check` y `test` en cada PR. |
| DT-02 | 🟡 Media | `CitaPeluqueria` repite `nombre_mascota` y `raza` como texto además de la FK a `Mascota`. | Peluquería, reportes | Mostrar siempre los datos de la FK y retirar los campos de texto con una migración de datos. |
| DT-03 | 🟢 Baja | `requirements.txt` y `requirements/` no coinciden del todo. | Mantenimiento | Dejar `requirements/prod.txt` como fuente y que `requirements.txt` solo contenga `-r requirements/prod.txt`. |
| DT-04 | 🟢 Baja | `Cita.hora_fin` sigue siendo `NOT NULL` en la base; funciona porque el modelo la completa al guardar. | Agenda | Mantener `completar_hora_fin()` o volver el campo `null=True` si se quiere distinguir "sin hora de fin". |
| DT-05 | 🟢 Baja | Pendientes del informe de QA del 28/10: desbordamiento horizontal en móvil y estilos repetidos dentro de las plantillas. Las imágenes pesadas ya se resolvieron con WebP. | Interfaz | Ver `rediseno_gui_prados_pets.txt`. |

### Corregidos

| ID | Descripción | Corrección |
|:--|:--|:--|
| BUG-01 | El control de permisos leía `request.user.rol` (no existe) y 17 vistas pedían el rol `recepcionista`. | Se lee `id_rol.nombre_rol` y `recepcionista` se traduce a `auxiliar` en `apps/usuarios/permissions.py`. |
| BUG-02 | Migración pendiente en `Venta.usuario`. | Migraciones creadas y fusionadas; `makemigrations --check` limpio. |
| BUG-04 | `hora_fin` obligatoria en la base pero opcional en el formulario. | `Cita.completar_hora_fin()` asigna 30 min por defecto al guardar. |
| BUG-05 | Pruebas que creaban un rol ya existente (llave duplicada). | Pruebas corregidas. |
| BUG-06 | Prueba de recordatorios dependiente de la fecha actual. | Prueba corregida. |
| — | 9 pruebas de peluquería no enviaban la condición del pelaje (obligatoria por PB-16). | Pruebas corregidas. |
| — | Error 500 al agendar peluquería. | Corregido el 15/11. |
| — | Páginas lentas (~2 s) por abrir una conexión nueva a Supabase en cada petición. | Pool de conexiones y menos consultas por página (~0,5 s). |

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