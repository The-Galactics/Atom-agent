# Historias de Usuario e Issues — SchoolApp CLI
**Versión:** 1.0.0 
**Estructura:** Issues tipo GitHub, organizadas por Feature y Developer

---

> **Convención de IDs:**
> - Historia de Usuario: `HU-[MÓDULO]-[NNN]`
> - Issue: `ISSUE-[NNN]`
> - Feature: `FEAT-[MÓDULO]`
> - Requisito Técnico: `RT-[NNN]`

---

## Distribución del Equipo

| Developer | Alias sugerido | Módulos asignados |
|-----------|----------------|-------------------|
| Developer 1 | `@dev1` | Configuración del proyecto, Autenticación |
| Developer 2 | `@dev2` | Estudiantes, Materias |
| Developer 3 | `@dev3` | Tareas, Notas |
| Developer 4 | `@dev4` | Ranking, Utilidades compartidas, Integración |

---

---

# FEATURE: FEAT-SETUP — Configuración del Proyecto

---

## ISSUE-001 — Configuración inicial del proyecto Maven multi-módulo

**Asignado a:** `@dev1` 
**Tipo:** Requisito Técnico 
**Prioridad:** Alta 
**Labels:** `setup`, `infrastructure`

### Descripción
Se debe crear la estructura base del proyecto Maven con paquetes organizados por dominio, siguiendo la arquitectura de capas definida en el SRS.

### Criterios de Aceptación
- [ ] El proyecto `schoolapp-cli` tiene un `pom.xml` con todas las dependencias necesarias
- [ ] Existen los paquetes por dominio: `auth`, `student`, `professor`, `subject`, `task`, `grade`, `ranking`, `shared`
- [ ] Cada paquete contiene sus capas: `controller`, `service`, `repository`, `model`
- [ ] El proyecto compila sin errores con `mvn clean install`
- [ ] El paquete `shared` contiene las utilidades de lectura/escritura de JSON

### Requisitos Técnicos

```
RT-001: Java 21
RT-002: Maven 3.8+
RT-003: Dependencia para manejo de JSON: jackson-databind o gson
RT-004: Dependencia para hashing de contraseñas: bcrypt (jBCrypt)
RT-005: JUnit 5 para pruebas unitarias
```

### Estructura esperada
```
schoolapp-cli/
├── pom.xml
└── src/main/java/com/school/
    ├── App.java
    ├── auth/
    ├── student/
    ├── professor/
    ├── subject/
    ├── task/
    ├── grade/
    ├── ranking/
    └── shared/
```

---

## ISSUE-002 — Configurar JSON Server como capa de persistencia

**Asignado a:** `@dev1` 
**Tipo:** Requisito Técnico 
**Prioridad:** Alta 
**Labels:** `setup`, `infrastructure`, `json-server`

### Descripción
Implementar en el paquete `shared` la lógica de lectura y escritura sobre archivos `.json` que simulan la persistencia de datos.

### Criterios de Aceptación
- [ ] Existe un archivo `db.json` o archivos separados por entidad: `users.json`, `subjects.json`, `tasks.json`, `grades.json`, `periods.json`
- [ ] El paquete `shared` expone métodos genéricos para leer y escribir listas de objetos en JSON
- [ ] Se manejan correctamente excepciones de lectura/escritura
- [ ] Las 5 materias predeterminadas se cargan automáticamente al primer inicio

---

---

# FEATURE: FEAT-AUTH — Autenticación

---

## ISSUE-003 — HU-AUTH-01: Creación de cuentas y Admin por defecto

**Asignado a:** `@dev1` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `auth`, `feature` 
**Casos de prueba:** `CP-AUTH-001`, `CP-AUTH-001b`, `CP-AUTH-002`, `CP-AUTH-002b`

### Historia de Usuario
> **Como** sistema y como administrador 
> **Quiero** que el primer inicio genere un Admin por defecto y que solo el Admin pueda crear cuentas 
> **Para** garantizar que el acceso al sistema esté siempre controlado por roles

### Criterios de Aceptación
- [ ] Al iniciar el sistema por primera vez, se crea automáticamente un usuario Admin con correo `admin@colegio.edu.co` y contraseña por defecto cifrada con BCrypt
- [ ] Los reinicios posteriores no duplican el Admin por defecto
- [ ] El menú principal solo muestra "Iniciar sesión" y "Salir" — no existe opción de auto-registro
- [ ] Solo el Admin puede crear cuentas de profesores y estudiantes desde su menú
- [ ] Al crear una cuenta, el correo debe terminar en `@colegio.edu.co`; de lo contrario se rechaza
- [ ] No se permiten correos duplicados
- [ ] La contraseña de toda cuenta nueva se almacena cifrada con BCrypt
- [ ] El sistema confirma la creación con un mensaje de éxito
- [ ] Casos de prueba: `CP-AUTH-001`, `CP-AUTH-001b`, `CP-AUTH-002`, `CP-AUTH-002b`

### Notas técnicas
- Usar `Record` de Java 21 para el DTO de creación de cuenta
- Validación de correo con expresión regular: `^[a-zA-Z0-9._%+-]+@colegio\\.edu\\.co$`
- El POJO `User.java` debe tener todos los campos con getters/setters (Java 8 style)
- La lógica de "primer inicio" vive en `AuthService.seedDefaultAdmin()`, invocada al arrancar la app
- La contraseña por defecto del Admin debe estar documentada en el README o en un archivo de configuración

---

## ISSUE-004 — HU-AUTH-02: Inicio de sesión

**Asignado a:** `@dev1` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `auth`, `feature` 
**Casos de prueba:** `CP-AUTH-002b`, `CP-AUTH-003`, `CP-AUTH-004`, `CP-AUTH-006`

### Historia de Usuario
> **Como** usuario registrado 
> **Quiero** iniciar sesión con mi correo y contraseña 
> **Para** acceder al menú correspondiente a mi rol

### Criterios de Aceptación
- [ ] El sistema solicita correo y contraseña
- [ ] Rechaza el acceso si el correo no tiene dominio `@colegio.edu.co`
- [ ] Verifica las credenciales contra el archivo JSON
- [ ] Si son correctas, muestra el menú del rol correspondiente
- [ ] Si son incorrectas, muestra mensaje de error y no permite acceso
- [ ] El menú mostrado corresponde exactamente al rol del usuario
- [ ] Casos de prueba: `CP-AUTH-002b`, `CP-AUTH-003`, `CP-AUTH-004`, `CP-AUTH-006`

---

## ISSUE-005 — HU-AUTH-03: Cierre de sesión

**Asignado a:** `@dev1` 
**Tipo:** Historia de Usuario 
**Prioridad:** Media 
**Labels:** `auth`, `feature` 
**Casos de prueba:** `CP-AUTH-005`

### Historia de Usuario
> **Como** usuario autenticado 
> **Quiero** cerrar mi sesión 
> **Para** proteger mi cuenta cuando termino de usar el sistema

### Criterios de Aceptación
- [ ] Opción "Cerrar sesión" disponible en todos los menús de rol
- [ ] Al cerrar sesión, el sistema limpia el estado de sesión actual
- [ ] Redirige al menú principal (sin sesión)
- [ ] Casos de prueba: `CP-AUTH-005`

---

---

# FEATURE: FEAT-STU — Gestión de Estudiantes

---

## ISSUE-006 — HU-STU-01: Admin crea estudiante

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `student`, `admin`, `feature` 
**Casos de prueba:** `CP-STU-001`

### Historia de Usuario
> **Como** administrador 
> **Quiero** crear nuevos estudiantes en el sistema 
> **Para** que puedan acceder y recibir calificaciones

### Criterios de Aceptación
- [ ] El formulario solicita: nombre, correo institucional y contraseña temporal
- [ ] Se valida que el correo no esté duplicado
- [ ] El estudiante queda registrado con rol `ESTUDIANTE`
- [ ] Se muestra mensaje de éxito con los datos del estudiante creado
- [ ] Casos de prueba: `CP-STU-001`

---

## ISSUE-007 — HU-STU-02: Admin lista estudiantes

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `student`, `admin`, `feature` 
**Casos de prueba:** `CP-STU-002`

### Historia de Usuario
> **Como** administrador 
> **Quiero** ver la lista completa de estudiantes 
> **Para** tener visibilidad total del sistema

### Criterios de Aceptación
- [ ] Muestra nombre, correo y estado (activo) de cada estudiante
- [ ] Si no hay estudiantes, muestra "No hay estudiantes registrados"
- [ ] Casos de prueba: `CP-STU-002`

---

## ISSUE-008 — HU-STU-03: Admin edita estudiante

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Media 
**Labels:** `student`, `admin`, `feature` 
**Casos de prueba:** `CP-STU-003`

### Historia de Usuario
> **Como** administrador 
> **Quiero** editar los datos de un estudiante 
> **Para** corregir información desactualizada

### Criterios de Aceptación
- [ ] Permite editar: nombre y correo
- [ ] No permite cambiar el correo por uno ya registrado
- [ ] Confirma los cambios con mensaje de éxito
- [ ] Casos de prueba: `CP-STU-003`

---

## ISSUE-009 — HU-STU-04: Admin elimina estudiante

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Media 
**Labels:** `student`, `admin`, `feature` 
**Casos de prueba:** `CP-STU-004`, `CP-STU-005`

### Historia de Usuario
> **Como** administrador 
> **Quiero** eliminar un estudiante del sistema 
> **Para** mantener el registro limpio

### Criterios de Aceptación
- [ ] Solicita confirmación antes de eliminar
- [ ] El estudiante desaparece de la lista
- [ ] Sus notas quedan como "huérfanas" y NO se eliminan
- [ ] Muestra mensaje de éxito tras la eliminación
- [ ] Casos de prueba: `CP-STU-004`, `CP-STU-005`

---

## ISSUE-010 — HU-STU-05: Profesor crea estudiante

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `student`, `profesor`, `feature` 
**Casos de prueba:** `CP-STU-006`

### Historia de Usuario
> **Como** profesor 
> **Quiero** crear un estudiante 
> **Para** incorporarlo al sistema sin depender del administrador

### Criterios de Aceptación
- [ ] Mismo flujo de creación que el Admin
- [ ] El profesor no puede eliminar ni editar estudiantes
- [ ] Casos de prueba: `CP-STU-006`

---

## ISSUE-011 — HU-STU-06: Profesor lista estudiantes y restricciones del rol

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Media 
**Labels:** `student`, `profesor`, `feature` 
**Casos de prueba:** `CP-STU-007`, `CP-STU-007b`

### Historia de Usuario
> **Como** profesor 
> **Quiero** ver la lista de estudiantes 
> **Para** saber a quiénes puedo asignarles notas

### Criterios de Aceptación
- [ ] Muestra nombre y correo de cada estudiante
- [ ] El profesor **no puede** editar ni eliminar estudiantes; cualquier intento debe mostrar "Acceso no autorizado para este rol"
- [ ] El menú del profesor no contiene ninguna opción relacionada con gestión de materias
- [ ] Casos de prueba: `CP-STU-007`, `CP-STU-007b`

---

---

# FEATURE: FEAT-PROF — Gestión de Profesores

---

## ISSUE-027 — HU-PROF-01: Admin crea profesor

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `professor`, `admin`, `feature` 
**Casos de prueba:** `CP-PROF-001`

### Historia de Usuario
> **Como** administrador 
> **Quiero** crear cuentas de profesor en el sistema 
> **Para** que puedan acceder y gestionar tareas y notas

### Criterios de Aceptación
- [ ] El formulario solicita: nombre, correo institucional y contraseña temporal
- [ ] Se valida que el correo termine en `@colegio.edu.co`
- [ ] Se valida que el correo no esté duplicado con ningún otro usuario del sistema
- [ ] La cuenta queda registrada con rol `PROFESOR`
- [ ] La contraseña se almacena cifrada con BCrypt
- [ ] Se muestra mensaje de éxito con los datos del profesor creado
- [ ] Casos de prueba: `CP-PROF-001`

### Notas técnicas
- Reutilizar el paquete `professor` con capas: `ProfessorController → ProfessorService → ProfessorRepository`
- El modelo `Professor.java` es un POJO que encapsula un `User` filtrado por `rol = PROFESOR`
- La validación de correo y cifrado de contraseña se delegan a `shared/Validator` y `shared/PasswordUtil`

---

## ISSUE-028 — HU-PROF-02: Admin lista profesores

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `professor`, `admin`, `feature` 
**Casos de prueba:** `CP-PROF-002`

### Historia de Usuario
> **Como** administrador 
> **Quiero** ver la lista completa de profesores 
> **Para** tener visibilidad del cuerpo docente registrado en el sistema

### Criterios de Aceptación
- [ ] Muestra nombre, correo y estado (activo) de cada profesor
- [ ] Filtra únicamente usuarios con `rol = PROFESOR`
- [ ] Si no hay profesores registrados, muestra "No hay profesores registrados"
- [ ] Casos de prueba: `CP-PROF-002`

---

## ISSUE-029 — HU-PROF-03: Admin edita profesor

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Media 
**Labels:** `professor`, `admin`, `feature` 
**Casos de prueba:** `CP-PROF-003`

### Historia de Usuario
> **Como** administrador 
> **Quiero** editar los datos de un profesor 
> **Para** corregir o actualizar su información cuando sea necesario

### Criterios de Aceptación
- [ ] Permite editar: nombre y correo
- [ ] No permite cambiar el correo por uno ya registrado en el sistema (cualquier rol)
- [ ] El correo editado debe seguir siendo `@colegio.edu.co`
- [ ] Confirma los cambios con mensaje de éxito
- [ ] Casos de prueba: `CP-PROF-003`

---

## ISSUE-030 — HU-PROF-04: Admin elimina profesor

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Media 
**Labels:** `professor`, `admin`, `feature` 
**Casos de prueba:** `CP-PROF-004`, `CP-PROF-005`

### Historia de Usuario
> **Como** administrador 
> **Quiero** eliminar un profesor del sistema 
> **Para** dar de baja cuentas inactivas o incorrectas

### Criterios de Aceptación
- [ ] Si el profesor tiene tareas asociadas, el sistema muestra un aviso indicando cuántas tareas y notas quedarán huérfanas, y solicita confirmación explícita
- [ ] Si el profesor no tiene tareas, la eliminación procede directamente tras confirmación
- [ ] Al confirmar, el profesor desaparece de la lista de profesores
- [ ] Las tareas del profesor eliminado permanecen en el sistema con `profesorId` apuntando a un usuario inexistente (huérfanas) — no se eliminan en cascada (RN-10)
- [ ] Las notas asociadas a esas tareas también se conservan intactas
- [ ] Los promedios y el ranking de estudiantes no se ven afectados
- [ ] Muestra mensaje de éxito tras la eliminación
- [ ] Casos de prueba: `CP-PROF-004`, `CP-PROF-005`

---

---

# FEATURE: FEAT-SUB — Gestión de Materias

---

## ISSUE-012 — HU-SUB-01: Carga automática de materias predeterminadas

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `subject`, `setup`, `feature` 
**Casos de prueba:** `CP-SUB-001`

### Historia de Usuario
> **Como** sistema 
> **Quiero** cargar las 5 materias predeterminadas al iniciar 
> **Para** que estén disponibles desde el primer uso

### Criterios de Aceptación
- [ ] Se cargan: Matemáticas, Español, Ciencias Naturales, Ciencias Sociales, Inglés
- [ ] Se marcan con `predeterminada: true`
- [ ] No se duplican en reinicios
- [ ] Casos de prueba: `CP-SUB-001`

---

## ISSUE-013 — HU-SUB-02: Admin crea materia

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Media 
**Labels:** `subject`, `admin`, `feature` 
**Casos de prueba:** `CP-SUB-002`

### Historia de Usuario
> **Como** administrador 
> **Quiero** crear nuevas materias 
> **Para** ampliar la oferta académica del colegio

### Criterios de Aceptación
- [ ] Permite ingresar el nombre de la nueva materia
- [ ] No permite duplicados
- [ ] Confirma la creación
- [ ] Casos de prueba: `CP-SUB-002`

---

## ISSUE-014 — HU-SUB-03 / HU-SUB-04 / HU-SUB-05: Admin gestiona materias (leer, editar, eliminar)

**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario 
**Prioridad:** Media 
**Labels:** `subject`, `admin`, `feature` 
**Casos de prueba:** `CP-SUB-003`, `CP-SUB-004`, `CP-SUB-005`

### Historia de Usuario
> **Como** administrador 
> **Quiero** leer, editar y eliminar materias 
> **Para** mantener actualizado el catálogo académico

### Criterios de Aceptación
- [ ] Lista todas las materias indicando cuáles son predeterminadas
- [ ] Permite editar el nombre de materias no predeterminadas
- [ ] Permite eliminar materias no predeterminadas
- [ ] Bloquea la eliminación de las 5 materias predeterminadas con mensaje explicativo
- [ ] Casos de prueba: `CP-SUB-003`, `CP-SUB-004`, `CP-SUB-005`

---

---

# FEATURE: FEAT-TASK — Gestión de Tareas

---

## ISSUE-015 — HU-TASK-01: Profesor crea tarea

**Asignado a:** `@dev3` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `task`, `profesor`, `feature` 
**Casos de prueba:** `CP-TASK-001`

### Historia de Usuario
> **Como** profesor 
> **Quiero** crear tareas asociadas a una materia 
> **Para** organizar las actividades evaluativas

### Criterios de Aceptación
- [ ] Solicita: título (obligatorio), descripción y fecha límite
- [ ] Se asocia la tarea a una materia existente
- [ ] Se guarda el ID del profesor creador
- [ ] Muestra mensaje de éxito con datos de la tarea
- [ ] Casos de prueba: `CP-TASK-001`

---

## ISSUE-016 — HU-TASK-02 / HU-TASK-03 / HU-TASK-04: Profesor gestiona tareas (leer, editar, eliminar)

**Asignado a:** `@dev3` 
**Tipo:** Historia de Usuario 
**Prioridad:** Media 
**Labels:** `task`, `profesor`, `feature` 
**Casos de prueba:** `CP-TASK-002`, `CP-TASK-003`, `CP-TASK-004`

### Historia de Usuario
> **Como** profesor 
> **Quiero** listar, editar y eliminar tareas 
> **Para** mantener actualizado el plan de evaluaciones

### Criterios de Aceptación
- [ ] Lista tareas por materia con título y fecha límite
- [ ] Permite editar título, descripción y fecha
- [ ] Al eliminar una tarea con notas, advierte al usuario y solicita confirmación
- [ ] Al confirmar, elimina la tarea y sus notas asociadas
- [ ] Casos de prueba: `CP-TASK-002`, `CP-TASK-003`, `CP-TASK-004`

---

---

# FEATURE: FEAT-GRADE — Gestión de Notas

---

## ISSUE-017 — HU-GRADE-01: Profesor registra nota

**Asignado a:** `@dev3` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `grade`, `profesor`, `feature` 
**Casos de prueba:** `CP-GRADE-001`

### Historia de Usuario
> **Como** profesor 
> **Quiero** registrar la nota de un estudiante en una tarea 
> **Para** evaluar su desempeño académico

### Criterios de Aceptación
- [ ] Selecciona: materia → tarea → estudiante
- [ ] Ingresa una nota entre 0.0 y 5.0
- [ ] El sistema rechaza notas fuera de rango con mensaje explicativo
- [ ] La nota queda guardada con fecha de registro y ID del profesor
- [ ] Casos de prueba: `CP-GRADE-001`

---

## ISSUE-018 — HU-GRADE-02 / HU-GRADE-03 / HU-GRADE-04: Profesor gestiona notas (leer, editar, eliminar)

**Asignado a:** `@dev3` 
**Tipo:** Historia de Usuario 
**Prioridad:** Media 
**Labels:** `grade`, `profesor`, `feature` 
**Casos de prueba:** `CP-GRADE-002`, `CP-GRADE-003`, `CP-GRADE-004`

### Historia de Usuario
> **Como** profesor 
> **Quiero** listar, editar y eliminar notas 
> **Para** corregir errores y mantener el registro actualizado

### Criterios de Aceptación
- [ ] Lista todas las notas de una tarea con nombre del estudiante y valor
- [ ] Permite editar una nota (rango 0.0–5.0)
- [ ] Al editar, recalcula el promedio del estudiante en esa materia
- [ ] Permite eliminar una nota con confirmación
- [ ] Al eliminar, recalcula el promedio
- [ ] Casos de prueba: `CP-GRADE-002`, `CP-GRADE-003`, `CP-GRADE-004`

---

## ISSUE-019 — HU-GRADE-05: Estudiante ve sus notas por tarea

**Asignado a:** `@dev3` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `grade`, `estudiante`, `feature` 
**Casos de prueba:** `CP-GRADE-005`

### Historia de Usuario
> **Como** estudiante 
> **Quiero** ver mis notas por tarea 
> **Para** conocer mi desempeño en cada actividad evaluada

### Criterios de Aceptación
- [ ] Solo muestra las notas del estudiante autenticado
- [ ] Muestra: materia, tarea y nota
- [ ] Si no tiene notas, muestra "Aún no tienes notas registradas"
- [ ] No permite acceder a notas de otro estudiante
- [ ] Casos de prueba: `CP-GRADE-005`

---

## ISSUE-020 — HU-GRADE-06 / HU-GRADE-07: Estudiante ve promedios

**Asignado a:** `@dev3` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `grade`, `estudiante`, `feature` 
**Casos de prueba:** `CP-GRADE-006`, `CP-GRADE-007`

### Historia de Usuario
> **Como** estudiante 
> **Quiero** ver mi promedio por materia y mi promedio general 
> **Para** tener visibilidad de mi rendimiento académico global

### Criterios de Aceptación
- [ ] Muestra el promedio de cada materia (media aritmética de todas las notas de tareas en esa materia)
- [ ] Si una materia no tiene notas, muestra "Sin notas registradas" — **no cuenta como 0**
- [ ] El promedio general se calcula **solo sobre las materias que tienen al menos una nota** (RN-04); las materias sin notas se excluyen del cálculo
- [ ] Si no hay ninguna materia con notas, muestra "Promedio general: Sin datos"
- [ ] Muestra una nota aclaratoria indicando sobre cuántas materias se calculó el promedio general
- [ ] Los promedios se muestran con 2 decimales
- [ ] Casos de prueba: `CP-GRADE-006`, `CP-GRADE-007`

---

---

# FEATURE: FEAT-RANK — Ranking Trimestral

---

## ISSUE-021 — HU-RANK-01: Cálculo automático de promedio trimestral

**Asignado a:** `@dev4` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `ranking`, `feature` 
**Casos de prueba:** `CP-RANK-001`, `CP-RANK-004`

### Historia de Usuario
> **Como** sistema 
> **Quiero** calcular el promedio de cada estudiante al cerrar un trimestre 
> **Para** alimentar el ranking con datos correctos

### Criterios de Aceptación
- [ ] El período trimestral se define como cada 90 días desde la fecha de inicio del sistema
- [ ] El promedio considera solo las 5 materias predeterminadas
- [ ] El cálculo es: media de promedios por materia
- [ ] El resultado queda almacenado en el período correspondiente
- [ ] Casos de prueba: `CP-RANK-001`, `CP-RANK-004`

---

## ISSUE-022 — HU-RANK-02: Admin consulta ranking trimestral

**Asignado a:** `@dev4` 
**Tipo:** Historia de Usuario 
**Prioridad:** Alta 
**Labels:** `ranking`, `admin`, `feature` 
**Casos de prueba:** `CP-RANK-002`, `CP-RANK-002b`

### Historia de Usuario
> **Como** administrador 
> **Quiero** consultar el ranking trimestral 
> **Para** reconocer y anunciar a los estudiantes más destacados

### Criterios de Aceptación
- [ ] Solo el administrador puede ver el ranking
- [ ] Muestra los **3 primeros lugares o más en caso de empate** con nombre y promedio (ver ISSUE-023)
- [ ] Si el trimestre actual **ya cerró**: muestra el ranking de ese trimestre
- [ ] Si el trimestre actual **aún está en curso**: muestra el ranking del último trimestre cerrado con el aviso _"Mostrando ranking del trimestre anterior. El trimestre actual aún está en curso."_
- [ ] Si **nunca ha cerrado un trimestre**: muestra _"Aún no hay trimestres cerrados con datos suficientes para generar el ranking"_
- [ ] El administrador puede consultar cualquier trimestre pasado cerrado
- [ ] Casos de prueba: `CP-RANK-002`, `CP-RANK-002b`

---

## ISSUE-023 — HU-RANK-03: Manejo de empates en el ranking

**Asignado a:** `@dev4` 
**Tipo:** Historia de Usuario 
**Prioridad:** Media 
**Labels:** `ranking`, `feature` 
**Casos de prueba:** `CP-RANK-003`

### Historia de Usuario
> **Como** administrador 
> **Quiero** que el sistema muestre a todos los estudiantes empatados 
> **Para** ser justo con quienes tienen el mismo mérito

### Criterios de Aceptación
- [ ] Si dos o más estudiantes comparten una posición, todos aparecen con la misma posición
- [ ] El ranking puede mostrar más de 3 estudiantes en caso de empate
- [ ] Las posiciones posteriores al empate se ajustan correctamente (ej. si hay 2 en el 1er lugar, el siguiente es el 3ro)
- [ ] Casos de prueba: `CP-RANK-003`

---

---

# FEATURE: FEAT-SHARED — Utilidades e Integración

---

## ISSUE-024 — Implementar menú de consola interactivo y navegación

**Asignado a:** `@dev4` 
**Tipo:** Requisito Técnico 
**Prioridad:** Alta 
**Labels:** `shared`, `ui`, `infrastructure`

### Descripción
Implementar en el paquete `shared` el sistema de menús de consola que será usado por todos los servicios. Debe ser reutilizable, limpio y manejar entradas inválidas sin cerrar el programa.

### Criterios de Aceptación
- [ ] Clase `MenuHelper` o similar con métodos reutilizables para mostrar menús y leer opciones
- [ ] Manejo de `NumberFormatException` cuando el usuario ingresa texto en lugar de número
- [ ] Mensajes de error amigables en español para cualquier entrada inválida
- [ ] Método para limpiar pantalla (compatible con Windows y Unix)
- [ ] Método para mostrar tablas simples en consola (columnas alineadas)

---

## ISSUE-025 — Implementar manejo global de excepciones y validaciones

**Asignado a:** `@dev4` 
**Tipo:** Requisito Técnico 
**Prioridad:** Media 
**Labels:** `shared`, `error-handling`

### Descripción
Asegurar que el sistema nunca se cierre abruptamente por una excepción no controlada. Implementar una capa de validación reutilizable en `shared`.

### Criterios de Aceptación
- [ ] Clase `Validator` con métodos: `isValidEmail()`, `isValidGrade()`, `isNotEmpty()`
- [ ] Todas las excepciones de I/O de JSON están manejadas con mensajes claros
- [ ] No se propagan `NullPointerException` ni `IndexOutOfBoundsException` al usuario
- [ ] Clase `AppException` para excepciones de negocio con mensajes en español

---

## ISSUE-026 — Escribir tests unitarios para servicios críticos

**Asignado a:** `@dev4` (coordinar con todo el equipo) 
**Tipo:** Requisito Técnico 
**Prioridad:** Media 
**Labels:** `testing`, `quality`

### Descripción
Implementar pruebas unitarias (JUnit 5) para los servicios con lógica de negocio crítica, especialmente los relacionados con notas y ranking.

### Criterios de Aceptación
- [ ] Tests para `AuthService`: registro, login, validación de correo
- [ ] Tests para `GradeService`: cálculo de promedio por materia, promedio general
- [ ] Tests para `RankingService`: cálculo de ranking, manejo de empates
- [ ] Cobertura mínima del 70% en los servicios mencionados
- [ ] Los tests pasan con `mvn test`

---

---

# Resumen de Issues por Developer

| Developer | Issues Asignadas | Total |
|-----------|-----------------|-------|
| `@dev1` | ISSUE-001, ISSUE-002, ISSUE-003, ISSUE-004, ISSUE-005 | 5 |
| `@dev2` | ISSUE-006, ISSUE-007, ISSUE-008, ISSUE-009, ISSUE-010, ISSUE-011, ISSUE-012, ISSUE-013, ISSUE-014, ISSUE-027, ISSUE-028, ISSUE-029, ISSUE-030 | 13 |
| `@dev3` | ISSUE-015, ISSUE-016, ISSUE-017, ISSUE-018, ISSUE-019, ISSUE-020 | 6 |
| `@dev4` | ISSUE-021, ISSUE-022, ISSUE-023, ISSUE-024, ISSUE-025, ISSUE-026 | 6 |

---

# Tabla de Relación HU → Issue → Casos de Prueba

| HU | Issue | Casos de Prueba |
|----|-------|-----------------|
| HU-AUTH-01 | ISSUE-003 | CP-AUTH-001, CP-AUTH-001b, CP-AUTH-002, CP-AUTH-002b |
| HU-AUTH-02 | ISSUE-004 | CP-AUTH-002b, CP-AUTH-003, CP-AUTH-004, CP-AUTH-006 |
| HU-AUTH-03 | ISSUE-005 | CP-AUTH-005 |
| HU-STU-01 | ISSUE-006 | CP-STU-001 |
| HU-STU-02 | ISSUE-007 | CP-STU-002 |
| HU-STU-03 | ISSUE-008 | CP-STU-003 |
| HU-STU-04 | ISSUE-009 | CP-STU-004, CP-STU-005 |
| HU-STU-05 | ISSUE-010 | CP-STU-006 |
| HU-STU-06 | ISSUE-011 | CP-STU-007, CP-STU-007b |
| HU-PROF-01 | ISSUE-027 | CP-PROF-001 |
| HU-PROF-02 | ISSUE-028 | CP-PROF-002 |
| HU-PROF-03 | ISSUE-029 | CP-PROF-003 |
| HU-PROF-04 | ISSUE-030 | CP-PROF-004, CP-PROF-005 |
| HU-SUB-01 | ISSUE-012 | CP-SUB-001 |
| HU-SUB-02 | ISSUE-013 | CP-SUB-002 |
| HU-SUB-03/04/05 | ISSUE-014 | CP-SUB-003, CP-SUB-004, CP-SUB-005 |
| HU-TASK-01 | ISSUE-015 | CP-TASK-001 |
| HU-TASK-02/03/04 | ISSUE-016 | CP-TASK-002, CP-TASK-003, CP-TASK-004 |
| HU-GRADE-01 | ISSUE-017 | CP-GRADE-001 |
| HU-GRADE-02/03/04 | ISSUE-018 | CP-GRADE-002, CP-GRADE-003, CP-GRADE-004 |
| HU-GRADE-05 | ISSUE-019 | CP-GRADE-005 |
| HU-GRADE-06/07 | ISSUE-020 | CP-GRADE-006, CP-GRADE-007 |
| HU-RANK-01 | ISSUE-021 | CP-RANK-001, CP-RANK-004 |
| HU-RANK-02 | ISSUE-022 | CP-RANK-002, CP-RANK-002b |
| HU-RANK-03 | ISSUE-023 | CP-RANK-003 |
