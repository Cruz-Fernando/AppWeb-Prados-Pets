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
![Pruebas](https://img.shields.io/badge/Pruebas-184%20pasan-16a34a)

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

> Corte: **16 de noviembre de 2026**, después de fusionar `Pruebas_V2` en `main` (PR #67). Estamos en el **Sprint 5** (09/11 – 20/11).

| Indicador | Valor |
|---|---|
| Ítems del backlog | 21 (PB-01 a PB-21) |
| ✅ Terminados | 15 |
| ⚠️ Terminados con pendiente | 1 (PB-11) |
| 🟡 Parciales | 5 (PB-15, PB-18, PB-19, PB-20, PB-21) |
| ⏳ Sin iniciar | 0 |
| Horas del backlog terminadas | 754 h de 1.134 h (**66 %**); 782 h (**69 %**) si se cuenta PB-11 |
| Pruebas automatizadas | **184 pruebas, todas pasan** |

```
Sprint 1  ██████████  Cerrado      RF16, RF17        Acceso y usuarios
Sprint 2  ██████████  Cerrado      RF04              Directorio
Sprint 3  █████████░  Cerrado      RF05              Agenda y citas (falta cancelar peluquería futura)
Sprint 4  ██████████  Cerrado      RF06, RF09, RF12  Historia clínica, carga masiva, recordatorios
Sprint 5  █████░░░░░  En curso     RF07, RF08, RF10, RF15  (RF08 y RF10 terminados)
Sprint 6  ██░░░░░░░░  Por iniciar  RF13, RF14, RF11  (ya tienen base)
```

---

## 🧩 Módulos y funcionalidades

| Módulo | Ruta | Qué hace hoy |
|---|---|---|
| **Usuarios y roles** | `/panel/`, `/usuarios/`, `/roles/` | Inicio y cierre de sesión, panel principal con avisos de recordatorios, alta/edición/baja de usuarios y roles (solo administrador). Roles: administrador, veterinario, auxiliar, groomer y domiciliario; cada uno ve solo sus módulos. |
| **Directorio** | `/directorio/` | Registro y edición de dueños y mascotas, código de mascota con año y mes (`AAMM`), peso y antecedentes de vacunación, búsqueda en tiempo real, listados y exportación a Excel. Insignias de cliente **Frecuente** y **VIP** (ver PB-18). |
| **Agenda de consulta** | `/agendamiento/` | Calendario visual por día y semana (consulta y peluquería juntas), agendamiento con validación de cruces por veterinario, hora de fin opcional (30 min por defecto), cancelación con motivo y comprobante PDF. |
| **Historia clínica** | `/clinico/historial/` | 8 tipos de registro (consulta general, vacunación, desparasitación, sedación, cirugía, eutanasia, control posoperatorio y otro), con constantes vitales, examen por sistemas, fórmula médica, **medicamentos e insumos usados** (se descuentan del inventario y vuelven al anular), adjuntos, edición/anulación con trazabilidad y PDF. |
| **Hospitalización** | `/clinico/hospitalizacion/` | Ingreso de pacientes, evolución diaria, alta con condición de salida y PDF. Se origina en la atención médica: no se agenda. |
| **Recordatorios** | `/clinico/recordatorios/` | Próximas vacunas y baños por mascota según el intervalo configurado; aviso en el panel principal. |
| **Peluquería** | `/peluqueria/` | Agendamiento con groomer, servicio, condición del pelaje, duración y precio; validación de cruces por groomer; vista previa de los insumos que se van a descontar; comisión del groomer (40 %) y comprobante PDF. |
| **Inventario** | `/inventario/` | Productos, medicamentos y servicios con **cantidad y fecha de vencimiento por producto** (sin lotes); búsqueda en tiempo real; botones Añadir y Quitar en cada fila (con motivo); retiro y reactivación sin perder el historial; kardex; **insumos por servicio de peluquería**; descuento automático desde consulta y peluquería; alertas de stock mínimo, vencidos y por vencer (30 días); carga masiva y exportación a Excel. |
| **Facturación** | `/facturacion/` | Ganancias por groomer (hoy, semana, mes, mes anterior o fechas elegidas): facturado, comisión del 40 % y lo que queda a la clínica, con el detalle de cada servicio. Cierre de servicios pasados como realizados o cancelados (al cancelar vuelven los insumos). Exportación a Excel. El groomer ve solo lo suyo. Falta la factura consolidada (PB-19). |
| **Reportes** | — | ⏳ Pendiente (Sprint 6). Las comisiones por groomer ya se consultan en Facturación. |

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
│   ├── clinico/        # historia clínica, hospitalización, recordatorios, insumos usados, PDF
│   ├── peluqueria/     # citas de grooming, comisión, insumos por cita, comprobante PDF
│   ├── inventario/     # productos, kardex, descuento de stock, insumos por servicio, carga Excel
│   ├── facturacion/    # ganancias y comisiones por groomer, exportación Excel
│   └── reportes/       # (vacía, Sprint 6)
├── config/
│   ├── settings/       # base.py, dev.py, prod.py
│   ├── middleware.py
│   ├── pdf.py          # utilidades comunes de PDF
│   └── urls.py
├── templates/          # una carpeta por app + base.html
├── static/             # css, js, img, plantillas (plantilla Excel de inventario)
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
python manage.py test                 # todo el proyecto (184 pruebas al 16/11/2026)
python manage.py test apps.clinico    # una sola app
```

Django crea una base de pruebas temporal, así que el usuario de la base necesita permiso para crear bases de datos.

Regla del equipo: **no se fusiona a `main` un PR que deje pruebas fallando** o con marcas de conflicto (`<<<<<<<`, `=======`, `>>>>>>>`). Si cambias una validación (por ejemplo, un campo que pasa a ser obligatorio), actualiza también las pruebas que envían ese formulario.

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

**Inventario › Carga Masiva Excel** recibe solo archivos `.xlsx` (usa la plantilla que se descarga desde la misma pantalla). El sistema lee **la primera hoja**, sin importar cuál estaba abierta al guardar, valida los encabezados de la fila 1 y procesa los datos desde la fila 2 (máximo 2.000 filas), en este orden:

| Col. | Campo | Obligatorio | Aplica a |
|---|---|---|---|
| A | `Tipo` (`PRODUCTO`, `MEDICAMENTO` o `SERVICIO`) | Sí | Todos |
| B | `Codigo` (único) | Sí | Todos |
| C | `Nombre` | Sí | Todos |
| D | `Descripcion` | No | Todos |
| E | `Precio` (venta, en COP, solo números) | Sí | Todos |
| F | `StockMinimo` (5 si se deja vacío) | No | Producto, medicamento |
| G–J | `PrincipioActivo`, `Concentracion`, `Presentacion`, `RequiereReceta` (SI/NO) | No | Medicamento |
| K | `NumeroLote` (se acepta, pero **ya no se usa**: el inventario no maneja lotes) | No | — |
| L | `FechaVencimiento` (AAAA-MM-DD): fecha de vencimiento del producto | No | Producto, medicamento |
| M | `CantidadLote`: **cantidad inicial** del producto | No | Producto, medicamento |

Las filas con error se listan en pantalla y no se guardan; las demás sí. Un código que ya existe se rechaza, y una fecha de vencimiento ya pasada no se carga como stock. Si el producto vence en 30 días o menos, se avisa.

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
- Si el PR se fusiona con **Squash and merge**, actualiza la rama de origen con `main` (`git merge origin/main`) antes de seguir trabajando en ella.
- Revisa `git status` antes de `git add .`: solo deben subirse archivos del proyecto (nada de archivos vacíos, `.env` ni respaldos de la base).

---

## 🗃️ Product Backlog actualizado

> Actualizado al **16/11/2026** según el código de `main`. Las estimaciones, responsables y criterios de aceptación completos están en [`BACKLOG.md`](BACKLOG.md).

**Estado:** ✅ Terminado · ⚠️ Terminado con pendiente · 🟡 Parcial · ⏳ Sin iniciar

### Iteración 1

| ID | Sp. | RF | Elemento | Est. (h) | Estado | Observaciones |
|:--|:-:|:--|:--|:-:|:-:|:--|
| PB-01 | 1 | RF16 | Control de acceso por rol (login y logout) | 67 | ✅ | Login, logout y permisos por rol. BUG-01 corregido: el rol se lee de `id_rol` y el nombre antiguo `recepcionista` se trata como `auxiliar`. |
| PB-02 | 1 | RF17 | Gestión de usuarios y roles (solo administrador) | 57 | ✅ | Incluye protección del último administrador y de los roles base. |
| PB-03 | 2 | RF04 | Registro de propietarios | 14 | ✅ | Con listado y exportación a Excel. |
| PB-04 | 2 | RF04 | Registro de mascotas con código AAMM, peso y vacunación | 28 | ✅ | |
| PB-05 | 2 | RF04 | Búsqueda en tiempo real de propietarios y mascotas | 33 | ✅ | Autocompletado AJAX. |
| PB-06 | 2 | RF04 | Edición de propietarios y mascotas | 28 | ✅ | |
| PB-07 | 3 | RF05 | Calendario diario y semanal | 57 | ✅ | Unifica consulta y peluquería. |
| PB-08 | 3 | RF05 | Citas de consulta médica | 24 | ✅ | BUG-04 corregido: la hora de fin es opcional y se asumen 30 min. |
| PB-09 | 3 | RF05 | Citas de peluquería con groomer y duración | 28 | ✅ | Guarda duración, precio y condición del pelaje. |
| PB-10 | 3 | RF05 | Validación de cruces de veterinario y groomer | 14 | ✅ | Detecta solapamiento de rangos, no solo la misma hora. |
| PB-11 | 3 | RF05 | Cancelación de citas con motivo y liberación del horario | 28 | ⚠️ | Consulta: terminada. Peluquería: solo se cancela desde Facturación cuando la cita ya pasó (y devuelve los insumos). **Falta cancelar una cita futura de peluquería.** |

### Iteración 2

| ID | Sp. | RF | Elemento | Est. (h) | Estado | Observaciones |
|:--|:-:|:--|:--|:-:|:-:|:--|
| PB-12 | 4 | RF06 | Consulta médica e historial clínico | 101 | ✅ | 8 tipos de registro, trazabilidad, anulación, adjuntos y PDF. Se agregó hospitalización completa. |
| PB-13 | 4 | RF09 | Carga masiva del catálogo por Excel | 93 | ✅ | Valida archivo, encabezados y fechas, e informa fila por fila. Mejora pendiente: importar el precio de compra (DT-05). |
| PB-14 | 4 | RF12 | Recordatorios de vacunación y baño | 68 | ✅ | Uno por mascota, con aviso en el panel y enlace en el menú. |
| PB-15 | 5 | RF07 | Récipe médico con medicamentos del catálogo | 92 | 🟡 | El registro clínico ya toma los medicamentos e insumos del inventario (con cantidad) y salen en el PDF del registro. Falta: dosis e indicaciones por medicamento y el PDF del récipe. |
| PB-16 | 5 | RF08 | Cobro de peluquería por raza, tamaño y pelaje, con comisión del 40 % | 67 | ✅ | Registra mascota, raza, tamaño, condición del pelaje, tipo de servicio/corte, groomer, precio manual y comisión del 40 %. |
| PB-17 | 5 | RF10 | Descuento automático de stock en consulta y peluquería | 75 | ✅ | Se descuenta al guardar el registro clínico o agendar la peluquería; si algo no alcanza, no se guarda nada. Al anular o cancelar, vuelve. Queda en el kardex. Pantalla «Insumos por servicio» con reglas por tamaño. |
| PB-18 | 5 | RF15 | Clasificación por colores de clientes recurrentes | 29 | 🟡 | Insignias **Frecuente** (4+ visitas) y **VIP** (8+) en el listado y la búsqueda de dueños. Falta: contar las visitas (BUG-09) y confirmar los umbrales con el patrocinador. |
| PB-19 | 6 | RF13 | Factura consolidada y registro de ingresos y gastos | 109 | 🟡 | Facturación ya muestra lo facturado en peluquería y la comisión por groomer. Falta: factura que sume consulta, peluquería y productos, y el registro de ingresos y gastos (arriendo). |
| PB-20 | 6 | RF14 | Reportes diarios, semanales y mensuales | 84 | 🟡 | Las comisiones por groomer por día, semana y mes (con Excel) ya están en Facturación. Falta: rotación de productos, vencimientos y balance de ganancias o pérdidas. |
| PB-21 | 6 | RF11 | Alertas de stock bajo y de vencimiento | 38 | 🟡 | Alertas de stock mínimo, vencidos y por vencer (30 días) en Inventario, y aviso al descontar. Falta: decidir los umbrales de 2 y 5 unidades y actualizar el criterio, que pide lote (DT-06). |

### Resumen por sprint

| Sprint | Fechas | RF | Horas | Avance |
|:-:|:--|:--|:-:|:--|
| 1 | 14/09 – 25/09 | RF16, RF17 | 124 | Cerrado; BUG-01 corregido |
| 2 | 28/09 – 09/10 | RF04 | 103 | Cerrado |
| 3 | 13/10 – 23/10 | RF05 | 151 | Cerrado; falta cancelar peluquería futura (PB-11) |
| 4 | 26/10 – 06/11 | RF06, RF09, RF12 | 262 | Cerrado |
| 5 | 09/11 – 20/11 | RF07, RF08, RF10, RF15 | 263 | **En curso:** PB-16 y PB-17 terminados (142 h); PB-15 y PB-18 parciales |
| 6 | 23/11 – 03/12 | RF13, RF14, RF11 | 231 | Por iniciar; PB-19 a PB-21 ya tienen base |

### Prioridad sugerida para lo que queda

1. **PB-15 (récipe):** dosis e indicaciones por medicamento y PDF del récipe, sobre la lista de medicamentos que ya tiene el registro clínico.
2. **PB-18 (clientes recurrentes):** contar las visitas reales (BUG-09) y confirmar con el patrocinador los umbrales de 4 y 8.
3. **PB-11:** botón para cancelar una cita de peluquería futura (la devolución de insumos ya funciona).
4. **Sprint 6:** PB-19 (factura consolidada e ingresos/gastos), luego PB-20 (reportes, que se alimenta de la factura) y cerrar PB-21.
5. **DT-01 (integración continua):** evita que lleguen a `main` pruebas fallando, como pasó el 16/11.

---

## 🐞 Defectos y deuda técnica

### Abiertos

| ID | Prioridad | Descripción | Afecta | Solución propuesta |
|:--|:-:|:--|:--|:--|
| BUG-09 | 🟠 Alta | `Dueno.numero_visitas` no se actualiza en ninguna parte (solo se puede editar en el admin), así que las insignias Frecuente y VIP no le aparecen a nadie. | PB-18 | Calcular las visitas a partir de las citas atendidas, los registros clínicos y las peluquerías realizadas, con los criterios que confirme el patrocinador. |
| BUG-03 | 🟠 Alta | `datos_respaldo_sqlite.json` (hashes de contraseñas y sesiones) se retiró del repositorio el 16/11, pero sigue en el historial de Git. | Seguridad | Cambiar las contraseñas de las cuentas que aparecen en el archivo. |
| DT-01 | 🟡 Media | No hay integración continua: el 29/10 llegaron marcas de conflicto a `main` y el 16/11 llegaron 9 pruebas fallando con el PR #67. | Todo el equipo | GitHub Action que corra `check`, `makemigrations --check` y `test` en cada PR. |
| DT-02 | 🟡 Media | `CitaPeluqueria` repite `nombre_mascota` y `raza` como texto además de la FK a `Mascota`. | Peluquería, reportes | Mostrar siempre los datos de la FK y retirar los campos de texto con una migración de datos. |
| DT-04 | 🟢 Baja | Pendientes del informe de QA del 28/10: desbordamiento horizontal en móvil, imágenes pesadas (logo de 80 KB mostrado a 36 px) y estilos repetidos dentro de las plantillas. | Interfaz | Aplicar las recomendaciones del informe de QA. |
| DT-05 | 🟢 Baja | La plantilla de Excel no trae precio de compra: el valor del inventario puede dar 0. | PB-13, PB-20 | Agregar la columna `PrecioCompra` a la plantilla y a la carga. |
| DT-06 | 🟢 Baja | Cambios de alcance sin registrar: el inventario ya no maneja lotes y la peluquería usa precio manual en vez de tabla de tarifas, pero los criterios de PB-16 y PB-21 en `BACKLOG.md` siguen hablando de «tarifa» y «lote». | Plan del proyecto | Registrar los cambios en el control de cambios y actualizar los criterios de aceptación. |

### Corregidos

| ID | Descripción | Corrección |
|:--|:--|:--|
| BUG-01 | El control de permisos no reconocía el rol: solo el superusuario entraba a los módulos. | Se lee `id_rol.nombre_rol`; `recepcionista` se trata como `auxiliar`. |
| BUG-02 | Faltaba una migración (`Venta.usuario`). | `makemigrations --check` ya no detecta cambios. |
| BUG-04 | `Cita.hora_fin` era obligatoria en la base. | Migración `0006_hora_fin_opcional`. |
| BUG-05 | Pruebas que creaban un rol que ya existía. | Usan `get_or_create`. |
| BUG-06 | Prueba de recordatorios que dependía de la fecha actual. | La suite pasa completa. |
| BUG-07 | 9 pruebas de peluquería e inventario fallaban porque no enviaban `condicion_pelaje`, que pasó a ser obligatoria con PB-16. | Pruebas actualizadas el 16/11. |
| BUG-08 | El comprobante PDF de peluquería no mostraba la condición del pelaje registrada en la cita. | El PDF usa la condición de la cita. |
| DT-03 | `requirements.txt` y `requirements/base.txt` no coincidían (faltaba `openpyxl` en `base.txt`). | Mismas dependencias y versiones en ambos. |

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
