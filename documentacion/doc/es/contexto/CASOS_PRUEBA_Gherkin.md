# Casos de Prueba — SchoolApp CLI
**Formato:** Gherkin (BDD) 
**Versión:** 1.0.0 
**Asociación:** Cada caso de prueba tiene un ID único para vincularlo a issues de GitHub/GitLab

---

> **Cómo asociar a una issue:** 
> En tu issue, referencia el caso de prueba con su ID en la sección de criterios de aceptación. 
> Ejemplo: `Criterios de aceptación: CP-AUTH-001, CP-AUTH-002`

---

## Módulo: Autenticación (AUTH)

---

### CP-AUTH-001 — Inicio de sesión del Admin por defecto al primer inicio

**Asociado a:** RF-01 | HU-AUTH-01

```gherkin
Feature: Admin por defecto al primer inicio
Como sistema
Quiero crear una cuenta de administrador automáticamente al iniciar por primera vez
Para que haya siempre un usuario con acceso total desde el inicio

Scenario: Primer inicio del sistema crea Admin por defecto
Given el archivo de usuarios está vacío o no existe
When el sistema inicia por primera vez
Then debe crear un usuario con correo "admin@colegio.edu.co" y rol "ADMIN"
And la contraseña por defecto debe estar cifrada con BCrypt
And el sistema muestra "Sistema iniciado. Admin por defecto creado."

Scenario: Reinicios posteriores no duplican el Admin por defecto
Given ya existe el usuario "admin@colegio.edu.co" con rol "ADMIN"
When el sistema inicia nuevamente
Then no debe crear un segundo usuario admin
And el sistema inicia normalmente al menú de login
```

---

### CP-AUTH-001b — Admin crea cuenta de Profesor o Estudiante

**Asociado a:** RF-01b | HU-AUTH-01

```gherkin
Feature: Creación de cuentas por el Administrador
Como administrador
Quiero crear cuentas para profesores y estudiantes
Para que puedan acceder al sistema con su rol correspondiente

Scenario: Admin crea cuenta de profesor exitosamente
Given el administrador está autenticado
And el correo "prof@colegio.edu.co" no está registrado
When el administrador selecciona "Gestionar Profesores" > "Crear"
And ingresa nombre "Laura Gómez", correo "prof@colegio.edu.co" y contraseña "Temp123"
Then el sistema crea la cuenta con rol "PROFESOR"
And muestra "Profesor creado exitosamente"

Scenario: No existe opción de auto-registro en el menú principal
Given el sistema muestra el menú principal sin sesión
Then el menú solo debe mostrar "Iniciar sesión" y "Salir"
And no debe existir ninguna opción de "Registrarse"
```

---

### CP-AUTH-002 — Admin no puede crear cuenta con correo no institucional

**Asociado a:** RF-02 | HU-AUTH-01

```gherkin
Feature: Validación de correo institucional al crear cuenta
Como sistema
Quiero rechazar correos no institucionales
Para garantizar que solo usuarios del colegio accedan

Scenario: Admin intenta crear cuenta con correo externo
Given el administrador está autenticado
When intenta crear una cuenta con correo "usuario@gmail.com"
Then el sistema debe rechazar la operación
And mostrar el mensaje "El correo debe pertenecer al dominio @colegio.edu.co"
And no crear la cuenta

Scenario: Admin intenta crear cuenta con correo sin dominio
Given el administrador está autenticado
When intenta crear una cuenta con correo "usuario"
Then el sistema debe mostrar "Formato de correo inválido"
And no crear la cuenta
```

---

### CP-AUTH-002b — Rechazo en login por correo no institucional

**Asociado a:** RF-02 | HU-AUTH-02

```gherkin
Feature: Validación de correo en inicio de sesión
Scenario: Login rechazado con correo externo
Given el sistema muestra el menú de login
When el usuario ingresa el correo "jdoe@gmail.com"
Then el sistema debe mostrar "Correo o contraseña incorrectos"
And permanecer en la pantalla de login
```

---

### CP-AUTH-003 — Inicio de sesión con credenciales válidas

**Asociado a:** RF-03 | HU-AUTH-02

```gherkin
Feature: Inicio de sesión
Como usuario registrado
Quiero iniciar sesión con mis credenciales
Para acceder a las funciones de mi rol

Scenario: Login exitoso como Administrador
Given existe un usuario "admin@colegio.edu.co" con rol "ADMIN"
And la contraseña es "Admin2025"
When el usuario ingresa "admin@colegio.edu.co" y "Admin2025"
Then el sistema debe autenticar al usuario
And mostrar el mensaje "Bienvenido, Administrador"
And mostrar el menú de administrador

Scenario: Login exitoso como Profesor
Given existe un usuario "prof@colegio.edu.co" con rol "PROFESOR"
When el usuario ingresa "prof@colegio.edu.co" y su contraseña correcta
Then el sistema debe autenticar al usuario
And mostrar el menú de profesor

Scenario: Login exitoso como Estudiante
Given existe un usuario "est@colegio.edu.co" con rol "ESTUDIANTE"
When el usuario ingresa "est@colegio.edu.co" y su contraseña correcta
Then el sistema debe autenticar al usuario
And mostrar el menú de estudiante
```

---

### CP-AUTH-004 — Menú diferente por rol

**Asociado a:** RF-04 | HU-AUTH-02

```gherkin
Feature: Menú por rol
Como sistema
Quiero mostrar un menú diferente según el rol
Para que cada usuario solo vea sus opciones

Scenario Outline: Menú correcto según rol
Given el usuario "<correo>" con rol "<rol>" inicia sesión
Then el sistema debe mostrar el menú de "<rol>"
And las opciones deben corresponder a las permitidas para "<rol>"

Examples:
| correo | rol |
| admin@colegio.edu.co | ADMIN |
| prof@colegio.edu.co | PROFESOR |
| student@colegio.edu.co | ESTUDIANTE |
```

---

### CP-AUTH-005 — Cierre de sesión

**Asociado a:** RF-05 | HU-AUTH-03

```gherkin
Feature: Cierre de sesión
Como usuario autenticado
Quiero cerrar mi sesión
Para proteger mi cuenta

Scenario: Cierre de sesión exitoso
Given el usuario "jdoe@colegio.edu.co" tiene una sesión activa
When el usuario selecciona la opción "Cerrar sesión"
Then el sistema debe cerrar la sesión
And mostrar el mensaje "Sesión cerrada correctamente"
And redirigir al menú principal sin sesión
```

---

### CP-AUTH-006 — Bloqueo por credenciales incorrectas

**Asociado a:** RF-06 | HU-AUTH-02

```gherkin
Feature: Seguridad en inicio de sesión
Como sistema
Quiero bloquear accesos con credenciales incorrectas
Para proteger las cuentas de los usuarios

Scenario: Login fallido con contraseña incorrecta
Given existe un usuario "jdoe@colegio.edu.co"
When el usuario ingresa "jdoe@colegio.edu.co" y "ContraseñaWrong"
Then el sistema debe rechazar el inicio de sesión
And mostrar el mensaje "Correo o contraseña incorrectos"
And permanecer en la pantalla de login

Scenario: Login fallido con usuario inexistente
Given no existe ningún usuario con correo "fantasma@colegio.edu.co"
When el usuario intenta iniciar sesión con ese correo
Then el sistema debe mostrar "Correo o contraseña incorrectos"
```

---

## Módulo: Gestión de Estudiantes (STU)

---

### CP-STU-001 — Admin crea estudiante

**Asociado a:** RF-07 | HU-STU-01

```gherkin
Feature: Crear estudiante (Admin)
Como administrador
Quiero crear un nuevo estudiante
Para incorporarlo al sistema

Scenario: Creación exitosa de estudiante
Given el administrador está autenticado
And el correo "nuevo@colegio.edu.co" no está registrado
When el administrador selecciona "Gestionar Estudiantes" > "Crear"
And ingresa nombre "Ana García"
And ingresa correo "nuevo@colegio.edu.co"
And ingresa contraseña "Pass123"
Then el sistema debe crear al estudiante
And mostrar "Estudiante creado exitosamente"
And el estudiante debe aparecer en la lista

Scenario: Creación fallida por correo duplicado
Given existe un estudiante con correo "duplicado@colegio.edu.co"
When el administrador intenta crear otro con el mismo correo
Then el sistema debe mostrar "El correo ya está registrado"
And no crear el duplicado
```

---

### CP-STU-002 — Admin lista estudiantes

**Asociado a:** RF-08 | HU-STU-02

```gherkin
Feature: Listar estudiantes (Admin)
Como administrador
Quiero ver todos los estudiantes
Para tener visibilidad del sistema

Scenario: Lista con estudiantes registrados
Given existen 3 estudiantes registrados en el sistema
When el administrador selecciona "Gestionar Estudiantes" > "Ver todos"
Then el sistema debe mostrar los 3 estudiantes con su nombre y correo

Scenario: Lista vacía
Given no hay estudiantes registrados
When el administrador selecciona "Ver todos" los estudiantes
Then el sistema debe mostrar "No hay estudiantes registrados"
```

---

### CP-STU-003 — Admin edita estudiante

**Asociado a:** RF-09 | HU-STU-03

```gherkin
Feature: Editar estudiante (Admin)
Como administrador
Quiero editar los datos de un estudiante
Para mantener la información actualizada

Scenario: Edición exitosa de nombre
Given existe un estudiante con ID "u003" y nombre "Carlos"
When el administrador edita su nombre a "Carlos Alberto"
Then el sistema debe actualizar el registro
And mostrar "Estudiante actualizado correctamente"
And el nuevo nombre debe aparecer en la lista
```

---

### CP-STU-004 — Admin elimina estudiante

**Asociado a:** RF-10 | HU-STU-04

```gherkin
Feature: Eliminar estudiante (Admin)
Como administrador
Quiero eliminar un estudiante
Para mantener el sistema limpio

Scenario: Eliminación exitosa
Given existe un estudiante con correo "salida@colegio.edu.co"
When el administrador selecciona eliminar a ese estudiante
And confirma la acción
Then el sistema debe eliminar al estudiante
And mostrar "Estudiante eliminado correctamente"
And el estudiante no debe aparecer en la lista

Scenario: Cancelar eliminación
Given existe un estudiante con correo "salida@colegio.edu.co"
When el administrador intenta eliminarlo pero cancela la acción
Then el estudiante debe permanecer en el sistema
```

---

### CP-STU-005 — Notas huérfanas al eliminar estudiante

**Asociado a:** RF-11 | HU-STU-04

```gherkin
Feature: Integridad de notas al eliminar estudiante
Como sistema
Quiero conservar las notas aunque el estudiante sea eliminado
Para mantener trazabilidad histórica

Scenario: Notas conservadas tras eliminación de estudiante
Given el estudiante "u003" tiene 5 notas registradas
When el administrador elimina al estudiante "u003"
Then las 5 notas deben permanecer en el sistema con estado "huérfana"
And no deben afectar el ranking de otros estudiantes
```

---

### CP-STU-006 — Profesor crea estudiante

**Asociado a:** RF-12 | HU-STU-05

```gherkin
Feature: Crear estudiante (Profesor)
Como profesor
Quiero crear un estudiante
Para incorporarlo a mis clases

Scenario: Profesor crea estudiante exitosamente
Given el profesor "prof@colegio.edu.co" está autenticado
When crea un estudiante con datos válidos
Then el estudiante debe quedar registrado en el sistema
And visible también para el administrador
```

---

### CP-STU-007 — Profesor lista estudiantes

**Asociado a:** RF-13 | HU-STU-06

```gherkin
Feature: Listar estudiantes (Profesor)
Como profesor
Quiero ver la lista de estudiantes
Para saber a quiénes puedo asignar notas

Scenario: Profesor ve lista de estudiantes
Given existen estudiantes registrados
When el profesor selecciona "Ver estudiantes"
Then el sistema muestra la lista con nombre y correo de cada estudiante
```

---

### CP-STU-007b — Restricciones explícitas del rol Profesor

**Asociado a:** RF-13b | HU-STU-06

```gherkin
Feature: Restricciones del Profesor sobre estudiantes y materias
Como sistema
Quiero impedir que el profesor acceda a operaciones que no le corresponden
Para mantener el control de acceso por rol

Scenario: Profesor no puede editar un estudiante
Given el profesor "prof@colegio.edu.co" está autenticado
When intenta invocar la operación de editar estudiante
Then el sistema debe mostrar "Acceso no autorizado para este rol"
And no modificar ningún dato

Scenario: Profesor no puede eliminar un estudiante
Given el profesor "prof@colegio.edu.co" está autenticado
When intenta invocar la operación de eliminar estudiante
Then el sistema debe mostrar "Acceso no autorizado para este rol"
And no eliminar ningún dato

Scenario: Menú del Profesor no contiene opciones de gestión de materias
Given el profesor está autenticado
When el sistema muestra su menú principal
Then no debe existir ninguna opción relacionada con "Materias"
And las únicas opciones deben ser: Gestionar Estudiantes, Gestionar Tareas, Gestionar Notas, Cerrar sesión
```

---

## Módulo: Gestión de Profesores (PROF)

---

### CP-PROF-001 — Admin crea profesor

**Asociado a:** RF-34 | HU-PROF-01

```gherkin
Feature: Crear profesor (Admin)
Como administrador
Quiero crear cuentas de profesor
Para que puedan gestionar tareas y notas en el sistema

Scenario: Creación exitosa de profesor
Given el administrador está autenticado
And el correo "profe@colegio.edu.co" no está registrado
When el administrador selecciona "Gestionar Profesores" > "Crear"
And ingresa nombre "Laura Gómez"
And ingresa correo "profe@colegio.edu.co"
And ingresa contraseña temporal "Temp2025"
Then el sistema debe crear la cuenta con rol "PROFESOR"
And mostrar "Profesor creado exitosamente"
And el profesor debe aparecer en la lista de profesores

Scenario: Creación fallida por correo duplicado
Given existe un usuario con correo "duplicado@colegio.edu.co"
When el administrador intenta crear un profesor con ese mismo correo
Then el sistema debe mostrar "El correo ya está registrado"
And no crear la cuenta duplicada

Scenario: Creación fallida por correo no institucional
Given el administrador está autenticado
When intenta crear un profesor con correo "profe@gmail.com"
Then el sistema debe mostrar "El correo debe pertenecer al dominio @colegio.edu.co"
And no crear la cuenta
```

---

### CP-PROF-002 — Admin lista profesores

**Asociado a:** RF-35 | HU-PROF-02

```gherkin
Feature: Listar profesores (Admin)
Como administrador
Quiero ver la lista de todos los profesores
Para tener visibilidad del cuerpo docente registrado

Scenario: Lista con profesores registrados
Given existen 3 profesores registrados en el sistema
When el administrador selecciona "Gestionar Profesores" > "Ver todos"
Then el sistema muestra los 3 profesores con nombre, correo y estado (activo)

Scenario: Lista vacía de profesores
Given no hay profesores registrados (solo existe el Admin por defecto)
When el administrador selecciona "Ver todos" los profesores
Then el sistema debe mostrar "No hay profesores registrados"
```

---

### CP-PROF-003 — Admin edita profesor

**Asociado a:** RF-36 | HU-PROF-03

```gherkin
Feature: Editar profesor (Admin)
Como administrador
Quiero editar los datos de un profesor
Para corregir o actualizar su información

Scenario: Edición exitosa de nombre
Given existe un profesor con ID "u010" y nombre "Pedro Ruiz"
When el administrador edita su nombre a "Pedro Ruiz Montoya"
Then el sistema debe actualizar el registro
And mostrar "Profesor actualizado correctamente"
And el nuevo nombre debe aparecer en la lista

Scenario: Edición fallida por correo duplicado
Given existe un profesor con correo "otro@colegio.edu.co"
When el administrador intenta cambiar el correo de otro profesor a "otro@colegio.edu.co"
Then el sistema debe mostrar "El correo ya está en uso por otro usuario"
And no modificar el registro
```

---

### CP-PROF-004 — Admin elimina profesor

**Asociado a:** RF-37 | HU-PROF-04

```gherkin
Feature: Eliminar profesor (Admin)
Como administrador
Quiero eliminar un profesor del sistema
Para dar de baja cuentas inactivas o incorrectas

Scenario: Eliminación exitosa sin tareas asociadas
Given existe un profesor con correo "salida@colegio.edu.co" sin tareas creadas
When el administrador selecciona eliminar a ese profesor
And confirma la acción
Then el sistema debe eliminar al profesor
And mostrar "Profesor eliminado correctamente"
And el profesor no debe aparecer en la lista

Scenario: Eliminación con aviso por tareas asociadas
Given existe un profesor con correo "activo@colegio.edu.co" que tiene 5 tareas creadas
When el administrador intenta eliminarlo
Then el sistema debe mostrar el aviso:
"Este profesor tiene 5 tareas y notas asociadas. Al eliminarlo, quedarán huérfanas. ¿Desea continuar?"
And esperar confirmación antes de proceder

Scenario: Cancelar eliminación de profesor
Given existe un profesor con correo "activo@colegio.edu.co"
When el administrador intenta eliminarlo pero cancela la acción
Then el profesor debe permanecer en el sistema sin ningún cambio
```

---

### CP-PROF-005 — Tareas y notas huérfanas al eliminar profesor

**Asociado a:** RF-38, RN-10 | HU-PROF-04

```gherkin
Feature: Integridad de tareas y notas al eliminar profesor
Como sistema
Quiero conservar las tareas y notas aunque el profesor sea eliminado
Para mantener la trazabilidad histórica académica

Scenario: Tareas y notas conservadas como huérfanas tras eliminar profesor
Given el profesor "u010" tiene 3 tareas creadas con 15 notas registradas en total
When el administrador confirma la eliminación del profesor "u010"
Then las 3 tareas deben permanecer en el sistema con `profesorId` apuntando a un profesor inexistente
And las 15 notas deben permanecer con su valor intacto
And ninguna nota ni tarea debe ser eliminada automáticamente
And el ranking y promedios de estudiantes no se ven afectados

Scenario: Las tareas huérfanas no aparecen en el menú del profesor
Given existen tareas con `profesorId` de un profesor eliminado
When cualquier profesor activo accede a "Gestionar Tareas"
Then las tareas huérfanas no deben aparecer en su lista de tareas
And solo el administrador puede visualizarlas si fuera necesario (futura versión)
```

---

## Módulo: Gestión de Materias (SUB)

---

### CP-SUB-001 — Carga de materias predeterminadas

**Asociado a:** RF-14 | HU-SUB-01

```gherkin
Feature: Materias predeterminadas
Como sistema
Quiero cargar las 5 materias predeterminadas al iniciar
Para que estén disponibles desde el primer uso

Scenario: Primera ejecución del sistema
Given el archivo de materias está vacío o no existe
When el sistema inicia por primera vez
Then debe crear las materias: "Matemáticas", "Español", "Ciencias Naturales", "Ciencias Sociales", "Inglés"
And marcarlas como predeterminadas

Scenario: Segunda ejecución no duplica materias
Given las 5 materias predeterminadas ya están cargadas
When el sistema inicia de nuevo
Then no debe crear duplicados
And mostrar las mismas 5 materias
```

---

### CP-SUB-002 — Admin crea materia

**Asociado a:** RF-15 | HU-SUB-02

```gherkin
Feature: Crear materia (Admin)
Como administrador
Quiero crear nuevas materias
Para ampliar la oferta académica

Scenario: Creación exitosa de materia nueva
Given el administrador está autenticado
When crea una materia con nombre "Educación Física"
Then la materia debe quedar registrada
And aparecer en la lista de materias

Scenario: No se permite nombre duplicado
Given existe una materia llamada "Arte"
When el administrador intenta crear otra materia llamada "Arte"
Then el sistema debe mostrar "Ya existe una materia con ese nombre"
```

---

### CP-SUB-003 — Admin lista materias

**Asociado a:** RF-16 | HU-SUB-03

```gherkin
Feature: Listar materias
Scenario: Listar todas las materias
Given existen al menos las 5 materias predeterminadas
When el administrador selecciona "Ver materias"
Then el sistema muestra todas las materias con su nombre y si son predeterminadas
```

---

### CP-SUB-004 — Admin edita materia

**Asociado a:** RF-17 | HU-SUB-04

```gherkin
Feature: Editar materia
Scenario: Editar nombre de materia no predeterminada
Given existe una materia personalizada "Robótica"
When el administrador cambia su nombre a "Robótica e IA"
Then el sistema actualiza el nombre
And muestra "Materia actualizada correctamente"
```

---

### CP-SUB-005 — Admin elimina materia no predeterminada

**Asociado a:** RF-18 | HU-SUB-05

```gherkin
Feature: Eliminar materia
Scenario: Eliminar materia personalizada exitosamente
Given existe una materia personalizada "Teatro"
When el administrador la elimina
Then la materia no debe aparecer en la lista

Scenario: No se puede eliminar materia predeterminada
Given "Matemáticas" es una materia predeterminada
When el administrador intenta eliminarla
Then el sistema debe mostrar "Las materias predeterminadas no pueden eliminarse en esta versión"
And la materia debe permanecer en el sistema
```

---

## Módulo: Gestión de Tareas (TASK)

---

### CP-TASK-001 — Profesor crea tarea

**Asociado a:** RF-19 | HU-TASK-01

```gherkin
Feature: Crear tarea
Como profesor
Quiero crear tareas por materia
Para organizar las evaluaciones

Scenario: Creación exitosa de tarea
Given el profesor está autenticado
And existe la materia "Matemáticas"
When crea una tarea con título "Taller de álgebra", descripción "Capítulo 5" y fecha límite "2025-03-01"
And la asigna a "Matemáticas"
Then la tarea debe quedar registrada
And aparecer al listar tareas de "Matemáticas"

Scenario: Creación fallida sin título
When el profesor intenta crear una tarea sin título
Then el sistema debe mostrar "El título es obligatorio"
```

---

### CP-TASK-002 — Profesor lista tareas de una materia

**Asociado a:** RF-20 | HU-TASK-02

```gherkin
Feature: Listar tareas
Scenario: Ver tareas de una materia
Given existen 3 tareas para "Español"
When el profesor selecciona "Ver tareas" de "Español"
Then el sistema muestra las 3 tareas con título y fecha límite
```

---

### CP-TASK-003 — Profesor edita tarea

**Asociado a:** RF-21 | HU-TASK-03

```gherkin
Feature: Editar tarea
Scenario: Editar fecha límite de una tarea
Given existe la tarea "Taller de álgebra" con fecha "2025-03-01"
When el profesor cambia la fecha a "2025-03-10"
Then el sistema actualiza la tarea
And muestra "Tarea actualizada correctamente"
```

---

### CP-TASK-004 — Profesor elimina tarea

**Asociado a:** RF-22 | HU-TASK-04

```gherkin
Feature: Eliminar tarea
Scenario: Eliminar tarea sin notas asociadas
Given existe la tarea "Quiz de ortografía" sin notas
When el profesor la elimina
Then la tarea no aparece en la lista

Scenario: Eliminar tarea con notas asociadas
Given existe la tarea "Parcial 1" con 10 notas registradas
When el profesor la elimina
Then el sistema debe advertir "Esta tarea tiene notas registradas. ¿Desea continuar?"
And eliminar la tarea junto con sus notas si el profesor confirma
```

---

## Módulo: Gestión de Notas (GRADE)

---

### CP-GRADE-001 — Profesor registra nota

**Asociado a:** RF-23 | HU-GRADE-01

```gherkin
Feature: Registrar nota
Como profesor
Quiero registrar la nota de un estudiante en una tarea
Para evaluar su desempeño

Scenario: Nota registrada exitosamente
Given el profesor está autenticado
And existe el estudiante "est@colegio.edu.co"
And existe la tarea "Parcial 1" en "Matemáticas"
When el profesor registra la nota 4.5 para ese estudiante en esa tarea
Then la nota debe quedar guardada
And mostrar "Nota registrada correctamente"

Scenario: Nota fuera de rango rechazada (mayor a 5.0)
When el profesor intenta registrar la nota 6.0
Then el sistema debe mostrar "La nota debe estar entre 0.0 y 5.0"

Scenario: Nota fuera de rango rechazada (menor a 0)
When el profesor intenta registrar la nota -1
Then el sistema debe mostrar "La nota debe estar entre 0.0 y 5.0"
```

---

### CP-GRADE-002 — Profesor lista notas de una tarea

**Asociado a:** RF-24 | HU-GRADE-02

```gherkin
Feature: Listar notas de una tarea
Scenario: Ver notas de todos los estudiantes en una tarea
Given la tarea "Parcial 1" tiene notas de 5 estudiantes
When el profesor selecciona "Ver notas" de "Parcial 1"
Then el sistema muestra los 5 estudiantes con sus notas
```

---

### CP-GRADE-003 — Profesor edita nota

**Asociado a:** RF-25 | HU-GRADE-03

```gherkin
Feature: Editar nota
Scenario: Corrección de nota exitosa
Given el estudiante "est@colegio.edu.co" tiene una nota de 3.0 en "Parcial 1"
When el profesor la cambia a 4.0
Then el sistema actualiza la nota
And recalcula el promedio del estudiante en esa materia
```

---

### CP-GRADE-004 — Profesor elimina nota

**Asociado a:** RF-26 | HU-GRADE-04

```gherkin
Feature: Eliminar nota
Scenario: Eliminar nota exitosamente
Given existe una nota para el estudiante "est@colegio.edu.co" en "Quiz 1"
When el profesor la elimina
Then la nota no aparece al consultar
And el promedio del estudiante se recalcula sin esa nota
```

---

### CP-GRADE-005 — Estudiante ve sus notas por tarea

**Asociado a:** RF-27 | HU-GRADE-05

```gherkin
Feature: Ver notas por tarea (Estudiante)
Como estudiante
Quiero ver mis notas por tarea
Para conocer mi desempeño en cada actividad

Scenario: Estudiante ve sus propias notas
Given el estudiante "est@colegio.edu.co" tiene notas en 3 tareas
When selecciona "Ver mis notas por tarea"
Then el sistema muestra cada tarea con su nota correspondiente

Scenario: Estudiante no puede ver notas de otro
Given el estudiante "est1@colegio.edu.co" está autenticado
When intenta acceder a notas del estudiante "est2@colegio.edu.co"
Then el sistema debe mostrar "Acceso no autorizado"
```

---

### CP-GRADE-006 — Estudiante ve promedio por materia

**Asociado a:** RF-28 | HU-GRADE-06

```gherkin
Feature: Ver promedio por materia
Scenario: Promedio calculado correctamente
Given el estudiante tiene notas [4.0, 3.5, 5.0] en "Matemáticas"
When selecciona "Ver promedio por materia"
Then el sistema debe mostrar "Matemáticas: 4.17"

Scenario: Materia sin notas
Given el estudiante no tiene notas en "Inglés"
When consulta el promedio por materia
Then el sistema debe mostrar "Inglés: Sin notas registradas"
```

---

### CP-GRADE-007 — Estudiante ve promedio general

**Asociado a:** RF-29, RN-04 | HU-GRADE-07

```gherkin
Feature: Ver promedio general
Como estudiante
Quiero ver mi promedio general
Para conocer mi rendimiento académico global

Scenario: Promedio general con todas las materias con notas
Given el estudiante tiene promedios por materia:
| Materia | Promedio |
| Matemáticas | 4.0 |
| Español | 3.5 |
| Ciencias Naturales| 4.5 |
| Ciencias Sociales | 3.0 |
| Inglés | 4.0 |
When selecciona "Ver mi promedio general"
Then el sistema debe mostrar "Promedio general: 3.80"
And la nota aclaratoria indica que se calculó sobre 5 materias

Scenario: Promedio general excluyendo materias sin notas (RN-04)
Given el estudiante tiene promedios registrados solo en 3 materias:
| Materia | Promedio |
| Matemáticas | 4.0 |
| Español | 3.0 |
| Inglés | 5.0 |
And "Ciencias Naturales" y "Ciencias Sociales" no tienen notas registradas
When selecciona "Ver mi promedio general"
Then el sistema debe mostrar "Promedio general: 4.00"
And una nota aclaratoria indica "Calculado sobre 3 materias con notas registradas"
And NO debe calcular las materias sin notas como 0.0

Scenario: Ninguna materia tiene notas
Given el estudiante no tiene ninguna nota registrada en ninguna materia
When selecciona "Ver mi promedio general"
Then el sistema debe mostrar "Promedio general: Sin datos — aún no tienes notas registradas"
```

---

## Módulo: Ranking Trimestral (RANK)

---

### CP-RANK-001 — Calcular promedio al cierre de trimestre

**Asociado a:** RF-30 | HU-RANK-01

```gherkin
Feature: Cálculo de promedio trimestral
Como sistema
Quiero calcular el promedio de cada estudiante al cerrar un trimestre
Para generar el ranking correctamente

Scenario: Promedio calculado correctamente al cierre
Given el trimestre 1 tiene fecha de cierre "2025-03-31"
And el estudiante "Ana" tiene promedios por materia: 4.5, 4.0, 3.5, 4.5, 5.0
When el sistema cierra el trimestre
Then el promedio de "Ana" debe ser 4.30
And debe quedar guardado en el período trimestral
```

---

### CP-RANK-002 — Admin consulta ranking trimestral

**Asociado a:** RF-31 | HU-RANK-02

```gherkin
Feature: Consultar ranking trimestral
Como administrador
Quiero consultar el ranking de estudiantes
Para reconocer a los más destacados

Scenario: Ranking con 3 ganadores distintos en trimestre cerrado
Given el trimestre 1 está cerrado
And los promedios son: Ana=4.8, Luis=4.5, María=4.2, Juan=3.9
When el administrador consulta el ranking
Then el sistema muestra los 3 o más primeros lugares con nombre y promedio:
| Posición | Estudiante | Promedio |
| 1 | Ana | 4.80 |
| 2 | Luis | 4.50 |
| 3 | María | 4.20 |

Scenario: Sin datos suficientes para ranking
Given no existe ningún trimestre cerrado
When el administrador consulta el ranking
Then el sistema muestra "Aún no hay trimestres cerrados con datos suficientes para generar el ranking"
```

---

### CP-RANK-002b — Consulta de ranking con trimestre en curso

**Asociado a:** RF-31b | HU-RANK-02

```gherkin
Feature: Ranking con trimestre aún abierto
Como sistema
Quiero mostrar el ranking del último trimestre cerrado
cuando el trimestre actual todavía no ha finalizado
Para que el administrador siempre tenga información útil disponible

Scenario: Admin consulta ranking y el trimestre actual está en curso
Given el trimestre 2 está en curso y aún no ha cerrado
And el trimestre 1 está cerrado con datos de ranking disponibles
When el administrador selecciona "Ver Ranking Trimestral"
Then el sistema muestra el ranking del trimestre 1
And muestra el aviso "Mostrando ranking del trimestre anterior. El trimestre actual aún está en curso."

Scenario: Admin consulta ranking y nunca ha cerrado un trimestre
Given el sistema nunca ha cerrado un trimestre
When el administrador selecciona "Ver Ranking Trimestral"
Then el sistema muestra "Aún no hay trimestres cerrados con datos suficientes para generar el ranking"
And no muestra datos parciales ni datos de estudiantes
```

---

### CP-RANK-003 — Empate en ranking trimestral

**Asociado a:** RF-32 | HU-RANK-03

```gherkin
Feature: Empate en ranking
Como sistema
Quiero mostrar todos los estudiantes empatados
Para no excluir a nadie con el mismo mérito

Scenario: Empate en tercer lugar
Given los promedios son: Ana=4.8, Luis=4.5, María=4.3, Juan=4.3
When el sistema genera el ranking
Then el ranking debe mostrar:
| Posición | Estudiante | Promedio |
| 1 | Ana | 4.80 |
| 2 | Luis | 4.50 |
| 3 (empate)| María | 4.30 |
| 3 (empate)| Juan | 4.30 |

Scenario: Empate en primer lugar
Given los promedios son: Ana=4.8, Luis=4.8, María=4.5
When el sistema genera el ranking
Then el ranking muestra a Ana y Luis en posición 1 (empate)
And a María en posición 2
```

---

### CP-RANK-004 — Ranking basado en 5 materias predeterminadas

**Asociado a:** RF-33 | HU-RANK-01

```gherkin
Feature: Materias consideradas en el ranking
Scenario: Ranking solo incluye materias predeterminadas
Given existen materias predeterminadas y una materia adicional "Teatro"
And un estudiante tiene notas en todas ellas
When el sistema calcula el promedio para el ranking
Then solo debe considerar: Matemáticas, Español, Ciencias Naturales, Ciencias Sociales e Inglés
And no incluir "Teatro" en el cálculo
```
