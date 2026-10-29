# Product Backlog – AppWeb Prados Pets (Entregable E1)

Este documento contiene el Product Backlog vigente del proyecto **AppWeb Prados Pets**, correspondiente al Entregable E1. La planificación está distribuida en **6 Sprints** de dos semanas organizados en **2 Iteraciones** (Sprints 1-3 y Sprints 4-6), abarcando del **14 de septiembre de 2026 al 3 de diciembre de 2026**.

---

## Resumen por Sprint

| Sprint | Iteración | RF del Sprint | Ventana (Inicio - Fin) | Construcción (Inicio - Fin) | Pruebas y Aprobación | Total Horas (Te) |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|
| **1** | 1 | RF16, RF17 | 14/09/2026 - 25/09/2026 | 14/09/2026 - 18/09/2026 | 16/09/2026 - 22/09/2026 | 194.25 h |
| **2** | 1 | RF04 | 28/09/2026 - 09/10/2026 | 28/09/2026 - 01/10/2026 | 30/09/2026 - 06/10/2026 | 173.25 h |
| **3** | 1 | RF05 | 13/10/2026 - 23/10/2026 | 13/10/2026 - 19/10/2026 | 16/10/2026 - 22/10/2026 | 224.25 h |
| **4** | 2 | RF06, RF09, RF12 | 26/10/2026 - 06/11/2026 | 26/10/2026 - 05/11/2026 | 28/10/2026 - 06/11/2026 | 313.75 h |
| **5** | 2 | RF07, RF08, RF10, RF15 | 09/11/2026 - 20/11/2026 | 09/11/2026 - 19/11/2026 | 11/11/2026 - 20/11/2026 | 320.75 h |
| **6** | 2 | RF13, RF14, RF11 | 23/11/2026 - 03/12/2026 | 23/11/2026 - 01/12/2026 | 01/12/2026 - 03/12/2026 | 288.00 h |

- **Total horas estimadas de construcción (Backlog):** 1,134 h
- **Total horas proyecto con verificación y pruebas (Te):** 1,514.25 h

---

## Tabla del Product Backlog (PB-01 a PB-21)

| ID | It. | Sp. | RF | Elemento del Backlog | HU | RN | Prioridad | Est. (h) | Responsables | Inicio | Fin | Criterios de Aceptación |
|:---|:---:|:---:|:---|:---|:---|:---:|:---:|:---:|:---|:---:|:---:|:---|
| PB-01 | 1 | 1 | RF16 | Control de acceso del personal de la clínica a sus módulos según su rol (inicio y cierre de sesión con usuario y contraseña) | HU-01, HU-02, HU-03 | R2 | Alta | 67 | Abel Stiven Ayala Llanes, Jhojan Fernando Cruz Bulla | 2026-09-14 | 2026-09-18 | Cada miembro del personal (administrador, veterinario o groomer) entra con su usuario y contraseña y accede solo a los módulos de su rol; al cerrar sesión no puede volver sin autenticarse. |
| PB-02 | 1 | 1 | RF17 | Gestión del personal de la clínica como usuarios del sistema con su rol, función exclusiva del administrador | HU-01 | R2 | Alta | 57 | Daniel Alejandro Pacheco Villamizar, Oscar Enrique Arias Cardile, Jeiner Duvan Carvajal Araque | 2026-09-14 | 2026-09-16 | Solo el administrador registra a cada empleado como usuario con su rol; usuarios y roles quedan guardados en la base de datos relacional. |
| PB-03 | 1 | 2 | RF04 | Registro de propietarios | HU-01, HU-02, HU-03 | R2, R5 | Alta | 14 | Jeiner Duvan Carvajal Araque | 2026-09-28 | 2026-09-29 | Se registra un propietario con sus datos; la información queda en la base de datos en la nube. |
| PB-04 | 1 | 2 | RF04 | Registro de mascotas (especie, raza, edad, peso y antecedentes de vacunación) asociadas a su propietario, con un código que incluye el año y el mes de registro (Acta 2) | HU-01, HU-02, HU-03 | R5 | Alta | 28 | Daniel Alejandro Pacheco Villamizar, Abel Stiven Ayala Llanes | 2026-09-28 | 2026-09-29 | Cada mascota queda asociada a un propietario, con especie, raza, edad, peso, antecedentes de vacunación y un código con el año y el mes de registro. |
| PB-05 | 1 | 2 | RF04 | Búsqueda en tiempo real de propietarios y mascotas | HU-01, HU-02, HU-03 | R5 | Alta | 33 | Oscar Enrique Arias Cardile, Jhojan Fernando Cruz Bulla | 2026-09-28 | 2026-09-29 | La búsqueda muestra resultados mientras se escribe (tiempo real, RNF04). |
| PB-06 | 1 | 2 | RF04 | Edición de propietarios y de mascotas | HU-01, HU-02, HU-03 | R2, R5 | Alta | 28 | Jeiner Duvan Carvajal Araque, Abel Stiven Ayala Llanes | 2026-09-29 | 2026-10-01 | Se editan los datos de un propietario o de una mascota y el cambio queda en la base de datos en la nube. |
| PB-07 | 1 | 3 | RF05 | Calendario dinámico con agenda diaria y semanal, consultada por el veterinario y el groomer | HU-01, HU-02, HU-03 | R6 | Alta | 57 | Oscar Enrique Arias Cardile, Jhojan Fernando Cruz Bulla | 2026-10-13 | 2026-10-16 | El calendario muestra la agenda diaria y semanal de consulta y peluquería; el veterinario y el groomer consultan su agenda. |
| PB-08 | 1 | 3 | RF05 | Programación de citas de consulta médica (mascota, servicio, fecha y hora) | HU-01, HU-02 | R6 | Alta | 24 | Daniel Alejandro Pacheco Villamizar, Abel Stiven Ayala Llanes, Jeiner Duvan Carvajal Araque | 2026-10-13 | 2026-10-13 | Una cita de consulta registra la mascota, el servicio, la fecha y la hora. |
| PB-09 | 1 | 3 | RF05 | Programación de citas de peluquería con el groomer (mascota, servicio, fecha, hora y duración) | HU-01, HU-03 | R6 | Alta | 28 | Jeiner Duvan Carvajal Araque, Abel Stiven Ayala Llanes | 2026-10-14 | 2026-10-15 | Una cita de peluquería registra la mascota, el servicio, el groomer, la fecha, la hora y la duración. |
| PB-10 | 1 | 3 | RF05 | Validación de cruces: no se permiten dos citas a la misma hora del veterinario ni del groomer | HU-01, HU-02, HU-03 | R6 | Alta | 14 | Daniel Alejandro Pacheco Villamizar, Abel Stiven Ayala Llanes | 2026-10-15 | 2026-10-16 | El sistema rechaza una cita en un horario ya ocupado por el veterinario o por el groomer. |
| PB-11 | 1 | 3 | RF05 | Cancelación de citas de consulta y de peluquería, y liberación del horario | HU-01, HU-02, HU-03 | R6 | Alta | 28 | Jhojan Fernando Cruz Bulla, Abel Stiven Ayala Llanes, Daniel Alejandro Pacheco Villamizar | 2026-10-16 | 2026-10-19 | Una cita cancelada queda con su motivo y libera el horario para una nueva cita. |
| PB-12 | 2 | 4 | RF06 | Registro de la consulta médica (anamnesis, constantes vitales y examen por sistemas) e historial clínico | HU-02 | R2 | Alta | 101 | Oscar Enrique Arias Cardile, Abel Stiven Ayala Llanes, Jeiner Duvan Carvajal Araque | 2026-10-28 | 2026-11-05 | Cada consulta queda guardada en el historial clínico de la mascota. |
| PB-13 | 2 | 4 | RF09 | Carga masiva del catálogo de medicamentos, servicios y productos con la plantilla de Excel | HU-01 | R7 | Alta | 93 | Daniel Alejandro Pacheco Villamizar, Jhojan Fernando Cruz Bulla | 2026-10-26 | 2026-11-04 | El catálogo se carga desde la plantilla y el sistema informa las filas con error. |
| PB-14 | 2 | 4 | RF12 | Recordatorios automáticos de vacunación y baño por mascota, según la periodicidad del patrocinador | HU-01, HU-02, HU-03 | R1, R3, R6 | Alta | 68 | Jeiner Duvan Carvajal Araque, Abel Stiven Ayala Llanes, Oscar Enrique Arias Cardile | 2026-10-26 | 2026-11-03 | Los recordatorios muestran la mascota, el propietario y el servicio pendiente según la periodicidad definida. |
| PB-15 | 2 | 5 | RF07 | Emisión del récipe médico desde la consulta, con los medicamentos del catálogo | HU-02 | R2 | Alta | 92 | Oscar Enrique Arias Cardile, Daniel Alejandro Pacheco Villamizar, Jeiner Duvan Carvajal Araque | 2026-11-12 | 2026-11-18 | El récipe incluye los medicamentos y las indicaciones y queda asociado a su consulta. |
| PB-16 | 2 | 5 | RF08 | Registro y cobro de los servicios de baño y peluquería según raza, tamaño y condición del pelaje, con la comisión del 40 % del groomer (Acta 2) | HU-03 | R3, R8 | Media | 67 | Jeiner Duvan Carvajal Araque, Abel Stiven Ayala Llanes, Oscar Enrique Arias Cardile | 2026-11-09 | 2026-11-11 | El servicio queda registrado con la mascota, la raza, el tamaño, la condición del pelaje, el tipo de corte y el groomer, se cobra según la tarifa y calcula la comisión del 40 % del groomer. |
| PB-17 | 2 | 5 | RF10 | Descuento automático del stock por consulta y peluquería | HU-02, HU-03 | R7 | Alta | 75 | Abel Stiven Ayala Llanes, Jhojan Fernando Cruz Bulla | 2026-11-11 | 2026-11-19 | El stock se descuenta al registrar cada consulta o servicio. |
| PB-18 | 2 | 5 | RF15 | Clasificación por colores de los clientes recurrentes según los criterios del patrocinador | HU-01 | R8 | Media | 29 | Jhojan Fernando Cruz Bulla, Daniel Alejandro Pacheco Villamizar | 2026-11-09 | 2026-11-10 | Los clientes recurrentes quedan identificados visualmente según los criterios del patrocinador. |
| PB-19 | 2 | 6 | RF13 | Factura consolidada con consulta, peluquería y productos, y registro de entradas y salidas de dinero, incluidos gastos como el arriendo (Acta 2) | HU-01 | R3, R8 | Alta | 109 | Oscar Enrique Arias Cardile, Daniel Alejandro Pacheco Villamizar, Jhojan Fernando Cruz Bulla | 2026-11-24 | 2026-12-01 | Una sola factura suma todo lo cobrado en la atención; las entradas y salidas de dinero (incluidos los gastos) quedan registradas. |
| PB-20 | 2 | 6 | RF14 | Reportes operativos y estadísticos diarios, semanales y mensuales, con rotación de productos, vencimientos, comisiones semanales por groomer y balance de ganancias o pérdidas (Acta 2) | HU-01 | R7 | Media | 84 | Jeiner Duvan Carvajal Araque, Abel Stiven Ayala Llanes | 2026-11-24 | 2026-12-01 | Los reportes se generan por día, semana y mes, e incluyen rotación de productos, vencimientos, las comisiones semanales de cada groomer y el balance de ganancias o pérdidas. |
| PB-21 | 2 | 6 | RF11 | Alertas en pantalla de stock bajo (menos de 2 o 5 unidades) y de vencimiento con fecha y lote | HU-01 | R7 | Media | 38 | Jeiner Duvan Carvajal Araque, Abel Stiven Ayala Llanes, Oscar Enrique Arias Cardile | 2026-11-23 | 2026-11-24 | La alerta aparece en pantalla cuando se cumple la condición de stock bajo o de vencimiento. |

---

## Convenciones y Definiciones

- **Historias de Usuario (HU):**
  - `HU-01`: Administrador
  - `HU-02`: Veterinario
  - `HU-03`: Groomer
- **Prioridad:**
  - **Alta:** Indispensable para operar la clínica o retener clientes.
  - **Media:** Mejora la operación y depende de elementos de prioridad alta.
- **Requisitos de Negocio (RN):** R1 a R9 según la Sección 2 del PGP.
