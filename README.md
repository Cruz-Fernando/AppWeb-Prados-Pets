<div align="center">

# 🐾 Prados Pets

### Sistema de gestión para clínica veterinaria

Consulta · Hospitalización · Peluquería · Inventario · Facturación · Directorio · Reportes

![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?logo=postgresql&logoColor=white)
![Metodología](https://img.shields.io/badge/Metodolog%C3%ADa-Scrum-7c3aed)
![Entregable](https://img.shields.io/badge/Entregable-E1-f472b6)

</div>

---

## 📋 Contenido

- [Acerca del proyecto](#-acerca-del-proyecto)
- [Módulos del alcance (E1)](#-módulos-del-alcance-e1)
- [Stack tecnológico](#-stack-tecnológico)
- [Estructura del repositorio](#-estructura-del-repositorio)
- [Cómo levantar el proyecto en local](#-cómo-levantar-el-proyecto-en-local)
- [Cuentas de prueba](#-cuentas-de-prueba-para-desarrollo-por-rol)
- [Despliegue](#-despliegue)
- [Flujo de trabajo con Git](#-flujo-de-trabajo-con-git)
- [Gestión del proyecto](#-gestión-del-proyecto)
- [Equipo](#-equipo)
- [Cliente](#-cliente)

---

## 🩺 Acerca del proyecto

**AppWeb Prados Pets** es el sistema de gestión para la clínica veterinaria **Prados Pets** (Cúcuta). Centraliza en una sola aplicación web el agendamiento de citas, la atención clínica, el servicio de peluquería, el inventario, la facturación, el directorio de clientes y los reportes.

Proyecto desarrollado para la asignatura *Administración de Proyectos Informáticos*, entregable **E1**.

---

## 🧩 Módulos del alcance (E1)

Según el alcance acordado con el patrocinador (Charter v2.0 — octubre 2026), el entregable E1 comprende **6 módulos** y **3 Historias de Usuario** (HU-01 a HU-03), con 12 Requerimientos Funcionales (RF04 a RF15).

| # | Módulo | RF cubiertos | HU |
|---|---|---|---|
| 1 | **Directorio Digital de Clientes y Mascotas** | RF05, RF06 | HU-01 |
| 2 | **Agendamiento Visual de Citas** | RF04, RF07 | HU-01 |
| 3 | **Atención Médica e Historial Clínico** | RF08, RF09, RF10 | HU-02 |
| 4 | **Peluquería / Grooming** | RF13 | HU-03 |
| 5 | **Control de Inventario y Alertas** | RF11, RF12 | HU-01, HU-02 |
| 6 | **Facturación Consolidada y Reportes** | RF14, RF15 | HU-01 |

> ⚠️ La hospitalización **no se agenda** (entra como atención derivada de consulta — RF10).

---

## ✨ Funcionalidades destacadas

- 📅 **Calendario visual (HU08):** vistas día y semana con citas de consulta y peluquería unificadas, colores por servicio, línea de hora actual y atajos de teclado.
- 🔍 **Buscador unificado:** búsqueda de mascota por nombre, dueño o teléfono con autocompletado AJAX.
- ✂️ **Agendamiento de peluquería:** duración estimada según tamaño y selección de groomer responsable.
- 📄 **Comprobante en PDF:** se genera al agendar tanto consultas médicas como servicios de peluquería.
- 🔐 **Roles y permisos:** administrador, veterinario, auxiliar, groomer y domiciliario.

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend / Frontend | Django 6.1 (Python) — arquitectura MVT |
| Base de datos | PostgreSQL (Supabase) |
| Generación de PDF | xhtml2pdf |
| Servidor de producción | Gunicorn + WhiteNoise |
| Metodología | Scrum, sprints semanales |
| Gestión de tareas | GitHub Issues + GitHub Projects |

---

## 🗂️ Estructura del repositorio

```
prados-pets/
├── apps/
│   ├── agendamiento/        # citas de consulta y calendario visual
│   ├── clinico/             # consulta, hospitalización, historia clínica
│   ├── directorio/          # dueños y mascotas
│   ├── facturacion/         # facturas consolidadas
│   ├── inventario/          # productos, stock, alertas
│   ├── peluqueria/          # servicio de grooming y comprobante PDF
│   ├── reportes/            # estadísticas y fidelización
│   └── usuarios/            # autenticación, roles y permisos
├── config/                  # proyecto Django (urls, wsgi, asgi)
│   └── settings/
│       ├── base.py
│       ├── dev.py
│       └── prod.py
├── static/
├── templates/
├── .env.example
├── Procfile
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🚀 Cómo levantar el proyecto en local

### Requisitos previos

- Python 3
- Git
- Credenciales de la base de datos compartida (las entrega el director del proyecto por canal privado)

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Cruz-Fernando/prados-pets.git
cd prados-pets

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Completa DB_USER, DB_PASSWORD y DB_HOST en el archivo .env

# 5. Aplicar migraciones
python manage.py migrate

# 6. Levantar el servidor de desarrollo
python manage.py runserver
```

Abre `http://127.0.0.1:8000/` en el navegador.

---

## 👤 Cuentas de prueba para desarrollo (por rol)

> **⚠️ Solo para desarrollo local. No usar en producción.**

```bash
python manage.py crear_usuarios_prueba
```

| Rol | Usuario | Contraseña |
|---|---|---|
| **Administrador** | `administrador` | `Admin123*` |
| **Veterinario** | `veterinario` | `Vet123*` |
| **Auxiliar** | `auxiliar` | `Auxiliar123*` |
| **Groomer** | `groomer` | `Groomer123*` |
| **Domiciliario** | `domiciliario` | `Domicilio123*` |

---

## ☁️ Despliegue

El `Procfile` define el ciclo de vida en Railway:

- **release:** `migrate` + `collectstatic` automáticos en cada deploy.
- **web:** Gunicorn con 2 workers.

Variables de entorno necesarias: ver `.env.example`.

Producción: `https://prados-pets-canina.up.railway.app`

---

## 🌿 Flujo de trabajo con Git

- `main`: rama estable, recibe merges desde ramas de HU vía Pull Request.
- `HUxx-nombre-corto`: una rama por historia de usuario, creada desde `main`.

Cada PR debe incluir `Closes #N` para cerrar el issue correspondiente.

---

## 📊 Gestión del proyecto

- **Backlog e historias de usuario:** pestaña [Issues](../../issues).
- **Tablero Scrum:** pestaña [Projects](../../projects).
- **Sprints:** semanales, del 21 de septiembre al 08 de noviembre de 2026 (cierre E1).
- **Equipo:** 3 parejas de trabajo, 1 HU por pareja por sprint.

---

## 👥 Equipo

| Nombre | Rol |
|---|---|
| Jhojan Cruz Bulla | Director de Proyecto / Scrum Master / Fullstack |
| David Torres Ovallos | Líder Tecnológico / Backend |
| Oscar Enrique Arias Cardile | Líder Documental / Fullstack |
| Daniel Alejandro Pacheco Villamizar | Frontend |
| Abel Stiven Ayala Llanes | Fullstack |
| Jeiner Duván Carvajal Araque | Frontend / QA |

> Samuel Alexander García Sandoval y Juan Camilo Guarín Solano se retiraron del equipo en octubre de 2026.

---

## 🏥 Cliente

**Prados Pets** — clínica veterinaria (Cúcuta), representada por Omar (propietario), patrocinador y cliente del proyecto.
