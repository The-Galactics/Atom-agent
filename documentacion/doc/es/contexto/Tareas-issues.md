# ⚙️ Tareas Técnicas por Issue — ManageVenus
**Versión:** 1.0.0  
**Proyecto:** ManageVenus  
**Stack:** Java 21 · Maven · Jackson · jBCrypt · JUnit 5  
**Arquitectura:** Capas por dominio — `Controller → Service → Repository → Model`  
**Persistencia:** Archivos JSON locales leídos/escritos con Jackson (sin servidor HTTP)

---

> **Convención de tareas:**  
> Cada tarea es la unidad mínima de trabajo que puede ser implementada y commiteada de forma independiente.  
> Formato de commit sugerido: `feat(dominio): descripción` · `fix(dominio): descripción` · `test(dominio): descripción`

---

## 📐 Dependencias de `pom.xml` requeridas

```xml
<!-- Jackson para serialización/deserialización JSON -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
    <version>2.17.0</version>
</dependency>

<!-- jBCrypt para hashing de contraseñas -->
<dependency>
    <groupId>org.mindrot</groupId>
    <artifactId>jbcrypt</artifactId>
    <version>0.4</version>
</dependency>

<!-- JUnit 5 para tests unitarios -->
<dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <version>5.10.2</version>
    <scope>test</scope>
</dependency>
```

---

---

# 🚀 FEAT-SETUP — Configuración del Proyecto

---

## ISSUE-001 — Configuración inicial del proyecto Maven
**Asignado a:** `@dev1` | **Prioridad:** 🔴 Alta

### Tarea 1.1 — Crear el `pom.xml` raíz con dependencias
**Archivo:** `schoolapp-cli/pom.xml`  
**Qué hacer:**
- Crear proyecto Maven con `groupId=com.school`, `artifactId=schoolapp-cli`, `version=1.0.0`
- Java 21 como compiler source/target: `<maven.compiler.source>21</maven.compiler.source>`
- Agregar las 3 dependencias del bloque anterior (Jackson, jBCrypt, JUnit 5)
- Agregar plugin `maven-surefire-plugin` versión 3.x para que JUnit 5 funcione con `mvn test`
- Agregar plugin `exec-maven-plugin` para ejecutar `App.java` con `mvn exec:java`

**Verificación:** `mvn clean install` sin errores de compilación.

---

### Tarea 1.2 — Crear el punto de entrada `App.java`
**Archivo:** `src/main/java/com/school/App.java`  
**Qué hacer:**
- Clase con método `main(String[] args)`
- Por ahora solo imprime `"SchoolApp CLI v1.0 iniciando..."` y llama a `MenuHelper.mostrarMenuPrincipal()`
- Importa `com.school.shared.util.MenuHelper`
- Anotación `@SuppressWarnings("unused")` no necesaria; el código debe compilar limpio

**Verificación:** `mvn exec:java -Dexec.mainClass="com.school.App"` imprime el mensaje.

---

### Tarea 1.3 — Crear la estructura de paquetes vacía por dominio
**Directorios a crear** (con un `.gitkeep` o clase placeholder):
```
src/main/java/com/school/
    auth/controller/  auth/service/  auth/repository/  auth/model/
    student/controller/  student/service/  student/repository/  student/model/
    professor/controller/  professor/service/  professor/repository/  professor/model/
    subject/controller/  subject/service/  subject/repository/  subject/model/
    task/controller/  task/service/  task/repository/  task/model/
    grade/controller/  grade/service/  grade/repository/  grade/model/
    ranking/controller/  ranking/service/  ranking/repository/  ranking/model/
    shared/util/  shared/exception/
src/test/java/com/school/
    auth/  grade/  ranking/  professor/
```
**Qué hacer:** Crear cada paquete. Maven requiere al menos un `.java` por paquete para que compile; crear clases placeholder vacías si es necesario.

**Verificación:** `mvn clean compile` sin errores.

---

## ISSUE-002 — Persistencia JSON local con Jackson
**Asignado a:** `@dev1` | **Prioridad:** 🔴 Alta

### Tarea 2.1 — Crear `JsonFileManager.java`
**Archivo:** `src/main/java/com/school/shared/util/JsonFileManager.java`  
**Qué hacer:**
```java
// Clase genérica con métodos estáticos:

// Lee todos los objetos de un archivo JSON como lista
public static <T> List<T> readAll(String fileName, Class<T> clazz)

// Escribe la lista completa sobreescribiendo el archivo
public static <T> void writeAll(String fileName, List<T> items)
```
- Usar `ObjectMapper` de Jackson con `JavaType` para listas genéricas
- Los archivos JSON se guardan en `data/` relativo al directorio de ejecución (ej. `data/users.json`)
- Si el archivo no existe, `readAll` devuelve lista vacía (no lanza excepción)
- Todas las excepciones de `IOException` deben capturarse y relanzar como `AppException`
- El `ObjectMapper` debe configurarse con `SerializationFeature.INDENT_OUTPUT` para legibilidad

**Verificación:** Test manual: crear una lista de objetos, escribirla, leerla, comparar.

---

### Tarea 2.2 — Crear los archivos JSON vacíos iniciales
**Archivos a crear en `data/`:**
```
data/users.json      → []
data/subjects.json   → []
data/tasks.json      → []
data/grades.json     → []
data/periods.json    → []
```
**Qué hacer:** Crear el directorio `data/` y los 5 archivos con un array vacío `[]`. Agregar `data/` al `.gitignore` excepto los archivos vacíos iniciales (usar `!data/*.json` en el `.gitignore`).

---

### Tarea 2.3 — Crear `AppException.java`
**Archivo:** `src/main/java/com/school/shared/exception/AppException.java`  
**Qué hacer:**
```java
public class AppException extends RuntimeException {
    public AppException(String message) { super(message); }
    public AppException(String message, Throwable cause) { super(message, cause); }
}
```
- Es `RuntimeException` para no obligar a declarar `throws` en toda la cadena de llamadas
- Se usa en todo el sistema para errores de negocio y de I/O

---

### Tarea 2.4 — Crear `Validator.java`
**Archivo:** `src/main/java/com/school/shared/util/Validator.java`  
**Qué hacer:**
```java
public class Validator {
    private static final String EMAIL_REGEX = "^[a-zA-Z0-9._%+-]+@colegio\\.edu\\.co$";

    // Devuelve true si el correo termina en @colegio.edu.co
    public static boolean isValidEmail(String email)

    // Devuelve true si la nota está entre 0.0 y 5.0 inclusive
    public static boolean isValidGrade(double value)

    // Devuelve true si el string no es null ni vacío tras trim()
    public static boolean isNotEmpty(String value)
}
```
- `isValidEmail` usa `Pattern.matches(EMAIL_REGEX, email)`
- `isValidGrade` verifica `value >= 0.0 && value <= 5.0`

---

---

# 🔐 FEAT-AUTH — Autenticación

---

## ISSUE-003 — Admin por defecto y creación de cuentas
**Asignado a:** `@dev1` | **Prioridad:** 🔴 Alta

### Tarea 3.1 — Crear el modelo `User.java` (POJO Java 8 style)
**Archivo:** `src/main/java/com/school/auth/model/User.java`  
**Qué hacer:**
```java
public class User {
    private String id;           // UUID generado al crear
    private String nombre;
    private String correo;
    private String contrasena;   // Almacenada como hash BCrypt
    private String rol;          // "ADMIN" | "PROFESOR" | "ESTUDIANTE"
    private boolean activo;
    private String fechaCreacion; // formato "yyyy-MM-dd"

    // Constructor vacío obligatorio para Jackson
    public User() {}

    // Constructor completo
    public User(String id, String nombre, String correo,
                String contrasena, String rol, boolean activo, String fechaCreacion) { ... }

    // Getters y setters para todos los campos (Java 8 style)
}
```
- Usar `UUID.randomUUID().toString()` para generar IDs
- La fecha de creación se genera con `LocalDate.now().toString()`
- Jackson necesita el constructor vacío para deserializar

---

### Tarea 3.2 — Crear el DTO `CreateUserRequest.java` (Record Java 21)
**Archivo:** `src/main/java/com/school/auth/model/CreateUserRequest.java`  
**Qué hacer:**
```java
public record CreateUserRequest(
    String nombre,
    String correo,
    String contrasena,
    String rol
) {}
```
- Es inmutable, usado solo para transportar datos de entrada al `AuthService`
- No se serializa a JSON, es solo un objeto de transferencia interno

---

### Tarea 3.3 — Crear `AuthRepository.java`
**Archivo:** `src/main/java/com/school/auth/repository/AuthRepository.java`  
**Qué hacer:**
```java
public class AuthRepository {
    private static final String FILE = "users.json";

    // Devuelve todos los usuarios del archivo
    public List<User> findAll()

    // Busca un usuario por su correo (ignora mayúsculas)
    public Optional<User> findByEmail(String correo)

    // Devuelve todos los usuarios con un rol específico
    public List<User> findByRole(String rol)

    // Guarda un nuevo usuario (agrega al archivo)
    public void save(User user)

    // Actualiza un usuario existente (busca por id y reemplaza)
    public void update(User user)

    // Elimina un usuario por id
    public void deleteById(String id)

    // Verifica si existe un usuario con ese correo
    public boolean existsByEmail(String correo)
}
```
- Todos los métodos delegan la lectura/escritura a `JsonFileManager`
- `findAll()` llama `JsonFileManager.readAll("users.json", User.class)`
- Los métodos de escritura leen la lista completa, la modifican y llaman a `writeAll`

---

### Tarea 3.4 — Crear `AuthService.java`
**Archivo:** `src/main/java/com/school/auth/service/AuthService.java`  
**Qué hacer:**
```java
public class AuthService {
    private final AuthRepository repo = new AuthRepository();

    // Crea el admin por defecto si no existe ningún usuario con rol ADMIN
    // Correo: admin@colegio.edu.co | Contraseña: Admin2025 (hasheada con BCrypt)
    public void seedDefaultAdmin()

    // Autentica un usuario. Devuelve el User si las credenciales son válidas.
    // Lanza AppException si el correo no existe o la contraseña no coincide.
    public User login(String correo, String contrasena)

    // Crea una cuenta nueva con el rol indicado.
    // Valida: correo institucional, correo no duplicado, campos no vacíos.
    // Hashea la contraseña con BCrypt antes de guardar.
    public User createAccount(CreateUserRequest request)
}
```
- `seedDefaultAdmin()`: verificar con `repo.findByEmail("admin@colegio.edu.co").isEmpty()` antes de crear
- `login()`: buscar por correo → verificar hash con `BCrypt.checkpw(contrasena, user.getContrasena())`
- `createAccount()`: validar con `Validator.isValidEmail()`, luego `repo.existsByEmail()`, luego hashear con `BCrypt.hashpw(contrasena, BCrypt.gensalt())`
- Lanzar `AppException` con mensajes claros en español en cada fallo

---

### Tarea 3.5 — Crear `AuthController.java`
**Archivo:** `src/main/java/com/school/auth/controller/AuthController.java`  
**Qué hacer:**
```java
public class AuthController {
    private final AuthService service = new AuthService();

    // Muestra el formulario de login, lee correo y contraseña del Scanner,
    // llama a service.login() y devuelve el User autenticado.
    // Si falla, muestra el error y repite el flujo (no cierra el programa).
    public User mostrarLogin(Scanner scanner)

    // Lógica para que el Admin cree una cuenta nueva.
    // Solicita nombre, correo, contraseña y rol por consola.
    // Imprime confirmación o error.
    public void crearCuenta(Scanner scanner, String rol)
}
```
- Usar `try-catch AppException` para mostrar errores sin crashear
- El `Scanner` se pasa como parámetro desde `App.java` (un solo Scanner en toda la app)

---

## ISSUE-004 — Inicio de sesión y menú por rol
**Asignado a:** `@dev1` | **Prioridad:** 🔴 Alta

### Tarea 4.1 — Crear `MenuHelper.java`
**Archivo:** `src/main/java/com/school/shared/util/MenuHelper.java`  
**Qué hacer:**
```java
public class MenuHelper {
    // Imprime el menú principal (sin sesión) y retorna la opción elegida (1 o 2)
    public static int mostrarMenuPrincipal(Scanner scanner)

    // Imprime el menú según el rol y retorna la opción elegida
    public static int mostrarMenuPorRol(Scanner scanner, String rol)

    // Lee un entero del scanner. Si la entrada no es número,
    // imprime "Opción inválida, intente de nuevo" y reintenta (sin lanzar excepción)
    public static int leerOpcion(Scanner scanner)

    // Limpia la consola (funciona en Windows y Unix)
    public static void limpiarPantalla()

    // Imprime una línea separadora visual
    public static void imprimirSeparador()
}
```
- `leerOpcion()` usa un loop `while(true)` con `try-catch NumberFormatException`
- `limpiarPantalla()` usa `System.out.print("\033[H\033[2J")` + `System.out.flush()`
- Los menús deben mostrarse con el formato de caja definido en el SRS

---

### Tarea 4.2 — Implementar flujo de sesión en `App.java`
**Archivo:** `src/main/java/com/school/App.java`  
**Qué hacer:**
- Al arrancar: llamar `authService.seedDefaultAdmin()` y `subjectService.seedDefaultSubjects()`
- Loop principal: mostrar menú principal → si elige "Iniciar sesión" → llamar `AuthController.mostrarLogin()` → obtener `User` autenticado
- Según `user.getRol()` → redirigir al menú correspondiente (`ADMIN`, `PROFESOR`, `ESTUDIANTE`)
- El loop continúa hasta que el usuario elige "Salir" o "Cerrar sesión"
- Usar `switch` con `String` (Java 21 permite switch expressions con patrones)

---

## ISSUE-005 — Cierre de sesión
**Asignado a:** `@dev1` | **Prioridad:** 🟡 Media

### Tarea 5.1 — Implementar cierre de sesión en el flujo de `App.java`
**Qué hacer:**
- La opción "Cerrar sesión" en cualquier menú de rol debe retornar el control al menú principal
- La variable `User usuarioActual` se pone a `null` al cerrar sesión
- Imprimir `"Sesión cerrada correctamente."` antes de redirigir
- No cerrar el `Scanner`; el programa sigue corriendo en el menú principal

---

---

# 👨‍🎓 FEAT-STU — Gestión de Estudiantes

---

## ISSUE-006 — Admin crea estudiante
**Asignado a:** `@dev2` | **Prioridad:** 🔴 Alta

### Tarea 6.1 — Crear el modelo `Student.java` (POJO)
**Archivo:** `src/main/java/com/school/student/model/Student.java`  
**Qué hacer:**
```java
// Student es una vista de User filtrada por rol = "ESTUDIANTE"
// No se persiste por separado; los datos viven en users.json
public class Student {
    private String id;
    private String nombre;
    private String correo;
    private boolean activo;

    // Constructor vacío + constructor completo + getters y setters
    // Método estático de fábrica:
    public static Student fromUser(User user) {
        return new Student(user.getId(), user.getNombre(), user.getCorreo(), user.isActivo());
    }
}
```

---

### Tarea 6.2 — Crear `StudentRepository.java`
**Archivo:** `src/main/java/com/school/student/repository/StudentRepository.java`  
**Qué hacer:**
```java
public class StudentRepository {
    private final AuthRepository authRepo = new AuthRepository();

    // Devuelve todos los usuarios con rol ESTUDIANTE como lista de Student
    public List<Student> findAll()

    // Busca un estudiante por id
    public Optional<Student> findById(String id)

    // Crea un nuevo estudiante delegando a AuthRepository.save()
    // El User ya debe tener rol = "ESTUDIANTE" y contraseña hasheada
    public void save(User user)

    // Actualiza nombre y correo de un estudiante (busca en users.json por id)
    public void update(String id, String nuevoNombre, String nuevoCorreo)

    // Marca al estudiante como inactivo (activo = false) en lugar de borrarlo físicamente
    // Pero sí lo elimina de la lista visible (el borrado real es en users.json)
    public void deleteById(String id)
}
```

---

### Tarea 6.3 — Crear `StudentService.java`
**Archivo:** `src/main/java/com/school/student/service/StudentService.java`  
**Qué hacer:**
```java
public class StudentService {
    private final StudentRepository repo = new StudentRepository();
    private final AuthRepository authRepo = new AuthRepository();

    // Crea un estudiante nuevo. Valida correo institucional y duplicados.
    // Hashea la contraseña. Puede ser llamado por Admin y Profesor.
    public Student create(String nombre, String correo, String contrasena)

    // Devuelve todos los estudiantes activos
    public List<Student> listAll()

    // Actualiza nombre y/o correo. Valida que el nuevo correo no esté duplicado.
    public Student update(String id, String nuevoNombre, String nuevoCorreo)

    // Elimina el estudiante. Sus notas en grades.json quedan con estudianteId
    // apuntando a un id inexistente (huérfanas). NO eliminar las notas.
    public void delete(String id)
}
```
- `create()`: validar con `Validator.isValidEmail()` → verificar duplicado → hashear → crear `User` con rol `ESTUDIANTE` → `repo.save()`
- `delete()`: llamar `repo.deleteById()` sin tocar `grades.json`

---

### Tarea 6.4 — Crear `StudentController.java`
**Archivo:** `src/main/java/com/school/student/controller/StudentController.java`  
**Qué hacer:**
```java
public class StudentController {
    private final StudentService service = new StudentService();

    // Submenú CRUD completo de estudiantes para Admin y Profesor
    // Muestra opciones: 1.Crear 2.Listar 3.Editar (solo Admin) 4.Eliminar (solo Admin) 5.Volver
    public void mostrarMenu(Scanner scanner, String rolActual)

    // Flujo de creación: solicita nombre, correo, contraseña temporal
    private void flujoCrear(Scanner scanner)

    // Flujo de listado: imprime tabla con id, nombre, correo
    private void flujoListar()

    // Flujo de edición: solicita id, nuevo nombre, nuevo correo
    private void flujoEditar(Scanner scanner)

    // Flujo de eliminación: solicita id, pide confirmación "¿Está seguro? (s/n)"
    private void flujoEliminar(Scanner scanner)
}
```
- Si `rolActual` es `"PROFESOR"`, ocultar opciones 3 y 4 del menú
- Capturar `AppException` en cada flujo y mostrar su mensaje

---

## ISSUE-007 — Admin lista estudiantes
*(Implementado dentro de `StudentController.flujoListar()` — Tarea 6.4)*

### Tarea 7.1 — Implementar tabla de listado en consola
**Qué hacer:**
- Usar `MenuHelper` para imprimir columnas alineadas: `ID | NOMBRE | CORREO | ESTADO`
- Si la lista está vacía: imprimir `"No hay estudiantes registrados."`
- Truncar nombres largos a 20 caracteres con `...` si superan el ancho de columna

---

## ISSUE-008 — Admin edita estudiante
*(Implementado dentro de `StudentController.flujoEditar()` — Tarea 6.4)*

### Tarea 8.1 — Validaciones de edición
**Qué hacer:**
- Solicitar el ID del estudiante a editar (mostrar lista primero para que el Admin elija)
- Si el estudiante no existe: `"Estudiante no encontrado."`
- Si el nuevo correo ya existe en otro usuario: `"El correo ya está en uso."`
- Mostrar `"Estudiante actualizado correctamente."` al éxito

---

## ISSUE-009 — Admin elimina estudiante
*(Implementado dentro de `StudentController.flujoEliminar()` — Tarea 6.4)*

### Tarea 9.1 — Confirmación y eliminación con notas huérfanas
**Qué hacer:**
- Solicitar ID → mostrar nombre del estudiante → pedir `"¿Confirmar eliminación? (s/n): "`
- Si confirma: llamar `service.delete(id)` → imprimir `"Estudiante eliminado correctamente."`
- Si cancela: imprimir `"Operación cancelada."` sin cambiar nada
- Las notas en `grades.json` NO se tocan (quedan con `estudianteId` apuntando al id eliminado)

---

## ISSUE-010 — Profesor crea estudiante
*(Reutiliza `StudentController.flujoCrear()` — Tarea 6.4)*

### Tarea 10.1 — Restringir edición/eliminación para Profesor
**Qué hacer:**
- En `StudentController.mostrarMenu()`: si `rolActual.equals("PROFESOR")`, no mostrar opciones 3 y 4
- Si por algún motivo se intenta llamar directamente: lanzar `AppException("Acceso no autorizado para este rol")`

---

## ISSUE-011 — Profesor lista estudiantes y restricciones
*(Reutiliza `StudentController.flujoListar()` — Tarea 6.4)*

### Tarea 11.1 — Verificar restricción de acceso a materias desde el Profesor
**Qué hacer:**
- En `App.java`, el menú del Profesor no debe incluir ninguna opción que llame a `SubjectController`
- Verificar en el switch de menú que el caso `"Materias"` no existe para rol `PROFESOR`

---

---

# 👨‍🏫 FEAT-PROF — Gestión de Profesores

---

## ISSUE-027 — Admin crea profesor
**Asignado a:** `@dev2` | **Prioridad:** 🔴 Alta

### Tarea 27.1 — Crear el modelo `Professor.java` (POJO)
**Archivo:** `src/main/java/com/school/professor/model/Professor.java`  
**Qué hacer:**
```java
// Igual que Student, Professor es una vista de User filtrada por rol = "PROFESOR"
public class Professor {
    private String id;
    private String nombre;
    private String correo;
    private boolean activo;

    public static Professor fromUser(User user) { ... }
    // Constructor vacío + constructor completo + getters y setters
}
```

---

### Tarea 27.2 — Crear `ProfessorRepository.java`
**Archivo:** `src/main/java/com/school/professor/repository/ProfessorRepository.java`  
**Qué hacer:**
```java
public class ProfessorRepository {
    private final AuthRepository authRepo = new AuthRepository();

    public List<Professor> findAll()           // filtra por rol = "PROFESOR"
    public Optional<Professor> findById(String id)
    public void save(User user)                // delega a authRepo.save()
    public void update(String id, String nombre, String correo)
    public void deleteById(String id)
}
```

---

### Tarea 27.3 — Crear `ProfessorService.java`
**Archivo:** `src/main/java/com/school/professor/service/ProfessorService.java`  
**Qué hacer:**
```java
public class ProfessorService {
    private final ProfessorRepository repo = new ProfessorRepository();
    private final AuthRepository authRepo = new AuthRepository();

    public Professor create(String nombre, String correo, String contrasena)
    public List<Professor> listAll()
    public Professor update(String id, String nuevoNombre, String nuevoCorreo)

    // Antes de eliminar, verificar si el profesor tiene tareas en tasks.json.
    // Si tiene tareas: lanzar AppException con mensaje que incluya el conteo:
    // "Este profesor tiene N tareas. Al eliminarlo quedarán huérfanas. Use confirmarEliminar()."
    // El controlador captura esto y muestra la advertencia + pide confirmación.
    public int countTasksByProfessor(String profesorId)

    // Elimina el profesor. Las tareas y notas quedan en sus archivos con profesorId huérfano.
    public void delete(String id)
}
```
- `countTasksByProfessor()`: leer `tasks.json` y contar los que tienen `profesorId == id`
- `delete()`: solo eliminar de `users.json`; NO tocar `tasks.json` ni `grades.json`

---

### Tarea 27.4 — Crear `ProfessorController.java`
**Archivo:** `src/main/java/com/school/professor/controller/ProfessorController.java`  
**Qué hacer:**
```java
public class ProfessorController {
    private final ProfessorService service = new ProfessorService();

    // Submenú CRUD de profesores (solo Admin puede acceder)
    // Opciones: 1.Crear 2.Listar 3.Editar 4.Eliminar 5.Volver
    public void mostrarMenu(Scanner scanner)

    private void flujoCrear(Scanner scanner)
    private void flujoListar()
    private void flujoEditar(Scanner scanner)

    // Flujo de eliminación con advertencia si tiene tareas:
    // 1. Verificar conteo de tareas con service.countTasksByProfessor()
    // 2. Si > 0: mostrar "Este profesor tiene N tareas y sus notas quedarán huérfanas. ¿Continuar? (s/n)"
    // 3. Si == 0: pedir confirmación simple "¿Confirmar eliminación? (s/n)"
    // 4. Si confirma: llamar service.delete()
    private void flujoEliminar(Scanner scanner)
}
```

---

## ISSUE-028 — Admin lista profesores
*(Implementado en `ProfessorController.flujoListar()` — Tarea 27.4)*

### Tarea 28.1 — Tabla de listado de profesores
**Qué hacer:**
- Imprimir columnas: `ID | NOMBRE | CORREO | ACTIVO`
- Si no hay profesores: `"No hay profesores registrados."`

---

## ISSUE-029 — Admin edita profesor
*(Implementado en `ProfessorController.flujoEditar()` — Tarea 27.4)*

### Tarea 29.1 — Validaciones específicas de edición
**Qué hacer:**
- Validar que el nuevo correo siga siendo `@colegio.edu.co`
- Validar que el nuevo correo no esté en uso por cualquier otro usuario (cualquier rol)
- Mensaje de éxito: `"Profesor actualizado correctamente."`

---

## ISSUE-030 — Admin elimina profesor
*(Implementado en `ProfessorController.flujoEliminar()` — Tarea 27.4)*

### Tarea 30.1 — Verificación de tareas huérfanas antes de eliminar
**Qué hacer:**
- Llamar `service.countTasksByProfessor(id)` antes de proceder
- Si el conteo es > 0: mostrar el aviso con el número exacto de tareas
- Tras confirmar y eliminar: imprimir `"Profesor eliminado. Sus N tareas quedan en el sistema como huérfanas."`

---

---

# 📚 FEAT-SUB — Gestión de Materias

---

## ISSUE-012 — Carga automática de materias predeterminadas
**Asignado a:** `@dev2` | **Prioridad:** 🔴 Alta

### Tarea 12.1 — Crear el modelo `Subject.java` (POJO)
**Archivo:** `src/main/java/com/school/subject/model/Subject.java`  
**Qué hacer:**
```java
public class Subject {
    private String id;
    private String nombre;
    private boolean predeterminada;
    private boolean activa;
    // Constructor vacío + constructor completo + getters y setters
}
```

---

### Tarea 12.2 — Crear `SubjectRepository.java`
**Archivo:** `src/main/java/com/school/subject/repository/SubjectRepository.java`  
**Qué hacer:**
```java
public class SubjectRepository {
    public List<Subject> findAll()
    public Optional<Subject> findById(String id)
    public boolean existsByNombre(String nombre)   // para validar duplicados
    public void save(Subject subject)
    public void update(Subject subject)
    public void deleteById(String id)
}
```
- Todos los métodos delegan a `JsonFileManager` con `"subjects.json"`

---

### Tarea 12.3 — Crear `SubjectService.java` con seed de materias
**Archivo:** `src/main/java/com/school/subject/service/SubjectService.java`  
**Qué hacer:**
```java
public class SubjectService {
    private final SubjectRepository repo = new SubjectRepository();

    private static final List<String> DEFAULT_SUBJECTS = List.of(
        "Matemáticas", "Español", "Ciencias Naturales", "Ciencias Sociales", "Inglés"
    );

    // Carga las 5 materias predeterminadas si no existen aún en subjects.json
    // Verificar por nombre antes de insertar para evitar duplicados en reinicios
    public void seedDefaultSubjects()

    // Crea una nueva materia personalizada (predeterminada = false)
    // Valida que el nombre no esté duplicado
    public Subject create(String nombre)

    // Devuelve todas las materias activas
    public List<Subject> listAll()

    // Edita el nombre de una materia. Solo permite editar las NO predeterminadas.
    // Si es predeterminada: lanzar AppException("Las materias predeterminadas no pueden editarse.")
    public Subject update(String id, String nuevoNombre)

    // Elimina una materia. Solo permite eliminar las NO predeterminadas.
    // Si es predeterminada: lanzar AppException("Las materias predeterminadas no pueden eliminarse en v1.0.")
    public void delete(String id)
}
```

---

## ISSUE-013 — Admin crea materia
## ISSUE-014 — Admin gestiona materias (leer, editar, eliminar)

### Tarea 13-14.1 — Crear `SubjectController.java`
**Archivo:** `src/main/java/com/school/subject/controller/SubjectController.java`  
**Qué hacer:**
```java
public class SubjectController {
    private final SubjectService service = new SubjectService();

    // Submenú: 1.Crear 2.Listar 3.Editar 4.Eliminar 5.Volver
    public void mostrarMenu(Scanner scanner)

    private void flujoCrear(Scanner scanner)
    private void flujoListar()
    // flujoEditar: mostrar lista → pedir id → pedir nuevo nombre
    // flujoEliminar: mostrar lista → pedir id → confirmar → si predeterminada, mostrar error
    private void flujoEditar(Scanner scanner)
    private void flujoEliminar(Scanner scanner)
}
```
- El listado muestra: `ID | NOMBRE | TIPO (Predeterminada / Personalizada)`

---

---

# 📝 FEAT-TASK — Gestión de Tareas

---

## ISSUE-015 — Profesor crea tarea
**Asignado a:** `@dev3` | **Prioridad:** 🔴 Alta

### Tarea 15.1 — Crear el modelo `Task.java` (POJO)
**Archivo:** `src/main/java/com/school/task/model/Task.java`  
**Qué hacer:**
```java
public class Task {
    private String id;
    private String titulo;
    private String descripcion;
    private String fechaLimite;  // formato "yyyy-MM-dd"
    private String materiaId;
    private String profesorId;
    // Constructor vacío + constructor completo + getters y setters
}
```

---

### Tarea 15.2 — Crear `TaskRepository.java`
**Archivo:** `src/main/java/com/school/task/repository/TaskRepository.java`  
**Qué hacer:**
```java
public class TaskRepository {
    public List<Task> findAll()
    public List<Task> findBySubjectId(String materiaId)
    public List<Task> findByProfessorId(String profesorId)
    public Optional<Task> findById(String id)
    public void save(Task task)
    public void update(Task task)
    public void deleteById(String id)
}
```

---

### Tarea 15.3 — Crear `TaskService.java`
**Archivo:** `src/main/java/com/school/task/service/TaskService.java`  
**Qué hacer:**
```java
public class TaskService {
    private final TaskRepository repo = new TaskRepository();

    // Crea una tarea. Valida que el título no esté vacío.
    // Guarda el profesorId del profesor autenticado.
    public Task create(String titulo, String descripcion, String fechaLimite,
                       String materiaId, String profesorId)

    // Lista las tareas de una materia. Solo muestra tareas del profesor autenticado.
    public List<Task> listBySubject(String materiaId, String profesorId)

    // Edita título, descripción y/o fecha límite de una tarea.
    // Verifica que la tarea pertenezca al profesorId (seguridad RNF-06).
    public Task update(String taskId, String titulo, String descripcion,
                       String fechaLimite, String profesorId)

    // Elimina la tarea y TODAS sus notas en grades.json.
    // Verifica que la tarea pertenezca al profesorId.
    public void delete(String taskId, String profesorId)

    // Cuenta cuántas notas tiene una tarea (para el aviso de eliminación)
    public int countGradesByTask(String taskId)
}
```
- `delete()`: primero leer `grades.json`, filtrar las que NO tienen ese `tareaId`, sobreescribir
- `countGradesByTask()`: leer `grades.json` y contar los que tienen `tareaId == taskId`

---

## ISSUE-016 — Profesor gestiona tareas (leer, editar, eliminar)

### Tarea 16.1 — Crear `TaskController.java`
**Archivo:** `src/main/java/com/school/task/controller/TaskController.java`  
**Qué hacer:**
```java
public class TaskController {
    private final TaskService service = new TaskService();
    private final SubjectService subjectService = new SubjectService();

    // Submenú: 1.Crear tarea 2.Ver tareas de una materia 3.Editar tarea
    //          4.Eliminar tarea 5.Volver
    public void mostrarMenu(Scanner scanner, String profesorId)

    // Flujo de creación: mostrar lista de materias → elegir → ingresar título,
    // descripción (opcional), fecha límite (opcional, formato yyyy-MM-dd)
    private void flujoCrear(Scanner scanner, String profesorId)

    // Flujo de listado: elegir materia → mostrar tareas en tabla
    // Tabla: ID | TÍTULO | FECHA LÍMITE
    private void flujoListar(Scanner scanner, String profesorId)

    // Flujo de edición: mostrar tareas del profesor → elegir → ingresar nuevos datos
    private void flujoEditar(Scanner scanner, String profesorId)

    // Flujo de eliminación con advertencia si tiene notas:
    // Si tiene notas: "Esta tarea tiene N notas. Se eliminarán también. ¿Continuar? (s/n)"
    private void flujoEliminar(Scanner scanner, String profesorId)
}
```

---

---

# 🏅 FEAT-GRADE — Gestión de Notas

---

## ISSUE-017 — Profesor registra nota
**Asignado a:** `@dev3` | **Prioridad:** 🔴 Alta

### Tarea 17.1 — Crear el modelo `Grade.java` (POJO)
**Archivo:** `src/main/java/com/school/grade/model/Grade.java`  
**Qué hacer:**
```java
public class Grade {
    private String id;
    private String estudianteId;
    private String tareaId;
    private String materiaId;
    private double valor;          // 0.0 a 5.0
    private String fechaRegistro;  // formato "yyyy-MM-dd"
    private String profesorId;
    // Constructor vacío + constructor completo + getters y setters
}
```

---

### Tarea 17.2 — Crear `GradeRepository.java`
**Archivo:** `src/main/java/com/school/grade/repository/GradeRepository.java`  
**Qué hacer:**
```java
public class GradeRepository {
    public List<Grade> findAll()
    public List<Grade> findByStudentId(String estudianteId)
    public List<Grade> findByTaskId(String tareaId)
    public List<Grade> findByStudentAndSubject(String estudianteId, String materiaId)
    public Optional<Grade> findById(String id)
    // Verifica si ya existe una nota para ese estudiante en esa tarea
    public boolean existsByStudentAndTask(String estudianteId, String tareaId)
    public void save(Grade grade)
    public void update(Grade grade)
    public void deleteById(String id)
    public void deleteByTaskId(String tareaId)   // para eliminación en cascada
}
```

---

### Tarea 17.3 — Crear `GradeService.java`
**Archivo:** `src/main/java/com/school/grade/service/GradeService.java`  
**Qué hacer:**
```java
public class GradeService {
    private final GradeRepository repo = new GradeRepository();

    // Registra una nota. Valida rango 0.0–5.0 (Validator.isValidGrade).
    // Si ya existe nota para ese estudiante en esa tarea: lanzar AppException
    // "Ya existe una nota para este estudiante en esta tarea. Use editar."
    public Grade create(String estudianteId, String tareaId,
                        String materiaId, double valor, String profesorId)

    // Lista todas las notas de una tarea específica
    public List<Grade> listByTask(String tareaId)

    // Edita el valor de una nota. Valida rango 0.0–5.0.
    public Grade update(String gradeId, double nuevoValor)

    // Elimina una nota por id
    public void delete(String gradeId)

    // Calcula el promedio de un estudiante en una materia
    // (media aritmética de todas sus notas en esa materia)
    // Devuelve OptionalDouble.empty() si no tiene notas en esa materia
    public OptionalDouble calcularPromedioPorMateria(String estudianteId, String materiaId)

    // Calcula el promedio general del estudiante
    // Solo considera materias que tengan al menos una nota (RN-04)
    // Devuelve OptionalDouble.empty() si no tiene ninguna nota
    public OptionalDouble calcularPromedioGeneral(String estudianteId, List<String> materiasIds)

    // Lista las notas de un estudiante (para la vista del estudiante)
    public List<Grade> listByStudent(String estudianteId)
}
```
- `calcularPromedioPorMateria()`: `repo.findByStudentAndSubject()` → hacer media → `OptionalDouble`
- `calcularPromedioGeneral()`: iterar `materiasIds` → para cada una llamar `calcularPromedioPorMateria()` → solo incluir las que devuelven valor → hacer media del conjunto

---

## ISSUE-018 — Profesor gestiona notas (leer, editar, eliminar)

### Tarea 18.1 — Crear `GradeController.java` (flujos del Profesor)
**Archivo:** `src/main/java/com/school/grade/controller/GradeController.java`  
**Qué hacer:**
```java
public class GradeController {
    private final GradeService service = new GradeService();

    // Submenú para Profesor:
    // 1.Registrar nota 2.Ver notas de una tarea 3.Editar nota 4.Eliminar nota 5.Volver
    public void mostrarMenuProfesor(Scanner scanner, String profesorId)

    // Flujo de registro: elegir materia → tarea → estudiante → ingresar valor
    private void flujoRegistrar(Scanner scanner, String profesorId)

    // Flujo de listado: elegir tarea → mostrar tabla: ESTUDIANTE | NOTA | FECHA
    private void flujoListarPorTarea(Scanner scanner)

    // Flujo de edición: mostrar notas de una tarea → elegir nota por id → ingresar nuevo valor
    private void flujoEditar(Scanner scanner)

    // Flujo de eliminación con confirmación
    private void flujoEliminar(Scanner scanner)
}
```

---

## ISSUE-019 — Estudiante ve sus notas por tarea

### Tarea 19.1 — Crear `GradeController` (flujos del Estudiante)
**Qué hacer:** Agregar al mismo `GradeController.java`:
```java
// Submenú para Estudiante (solo lectura):
// 1.Ver mis notas por tarea 2.Ver promedio por materia 3.Ver promedio general 4.Volver
public void mostrarMenuEstudiante(Scanner scanner, String estudianteId)

// Muestra tabla: MATERIA | TAREA | NOTA | FECHA
private void flujoVerNotasPorTarea(String estudianteId)
```
- `flujoVerNotasPorTarea()`: llamar `service.listByStudent(estudianteId)` → enriquecer con nombre de tarea y materia leyendo `tasks.json` y `subjects.json` → imprimir tabla

---

## ISSUE-020 — Estudiante ve promedios

### Tarea 20.1 — Flujos de promedios en `GradeController`
**Qué hacer:** Agregar:
```java
// Muestra: MATERIA | PROMEDIO (o "Sin notas registradas")
private void flujoVerPromedioPorMateria(String estudianteId)

// Muestra: "Promedio general: X.XX (calculado sobre N materias)"
// Si no hay notas: "Promedio general: Sin datos"
private void flujoVerPromedioGeneral(String estudianteId)
```
- `flujoVerPromedioPorMateria()`: iterar las 5 materias predeterminadas → para cada una llamar `service.calcularPromedioPorMateria()` → formatear con 2 decimales usando `String.format("%.2f", valor)`
- `flujoVerPromedioGeneral()`: llamar `service.calcularPromedioGeneral()` con los IDs de las 5 materias predeterminadas → formatear resultado

---

---

# 🏆 FEAT-RANK — Ranking Trimestral

---

## ISSUE-021 — Cálculo automático de promedio trimestral
**Asignado a:** `@dev4` | **Prioridad:** 🔴 Alta

### Tarea 21.1 — Crear el modelo `Period.java` (POJO)
**Archivo:** `src/main/java/com/school/ranking/model/Period.java`  
**Qué hacer:**
```java
public class Period {
    private String id;
    private String nombre;           // "Trimestre 1 - 2026"
    private String fechaInicio;      // "yyyy-MM-dd"
    private String fechaFin;         // "yyyy-MM-dd"
    private boolean cerrado;
    // Mapa de promedios por estudiante al momento del cierre:
    // clave = estudianteId, valor = promedio calculado
    private Map<String, Double> promediosPorEstudiante;
    // Constructor vacío + constructor completo + getters y setters
}
```

---

### Tarea 21.2 — Crear `RankingRepository.java`
**Archivo:** `src/main/java/com/school/ranking/repository/RankingRepository.java`  
**Qué hacer:**
```java
public class RankingRepository {
    public List<Period> findAll()
    public Optional<Period> findLatestClosed()   // último período con cerrado=true
    public Optional<Period> findCurrent()        // período con cerrado=false
    public void save(Period period)
    public void update(Period period)
}
```

---

### Tarea 21.3 — Crear `RankingService.java`
**Archivo:** `src/main/java/com/school/ranking/service/RankingService.java`  
**Qué hacer:**
```java
public class RankingService {
    private final RankingRepository repo = new RankingRepository();
    private final GradeService gradeService = new GradeService();
    private final StudentRepository studentRepo = new StudentRepository();
    private final SubjectService subjectService = new SubjectService();

    // Verifica si han pasado 90 días desde el inicio del período actual.
    // Si es así, cierra el período: calcula promedios de todos los estudiantes
    // y los guarda en period.promediosPorEstudiante. Crea el siguiente período.
    public void checkAndClosePeriodIfDue()

    // Calcula el promedio trimestral de un estudiante sobre las 5 materias predeterminadas
    // (usando RN-04: solo materias con notas)
    public double calcularPromedioEstudiante(String estudianteId)

    // Genera el ranking del último trimestre cerrado.
    // Devuelve lista de entradas ordenadas por promedio descendente.
    // Gestiona empates: todos los estudiantes con el mismo promedio tienen la misma posición.
    // Si no hay trimestre cerrado: devuelve lista vacía.
    public List<RankingEntry> generarRanking()

    // Devuelve true si el trimestre actual aún está en curso (no cerrado)
    public boolean isCurrentPeriodOpen()
}
```

---

### Tarea 21.4 — Crear `RankingEntry.java` (Record Java 21)
**Archivo:** `src/main/java/com/school/ranking/model/RankingEntry.java`  
**Qué hacer:**
```java
public record RankingEntry(
    int posicion,
    String estudianteId,
    String nombreEstudiante,
    double promedio
) {}
```
- Es inmutable, se genera al momento de consultar el ranking, no se persiste

---

## ISSUE-022 — Admin consulta ranking trimestral
## ISSUE-023 — Manejo de empates en el ranking

### Tarea 22-23.1 — Crear `RankingController.java`
**Archivo:** `src/main/java/com/school/ranking/controller/RankingController.java`  
**Qué hacer:**
```java
public class RankingController {
    private final RankingService service = new RankingService();

    // Punto de entrada desde el menú Admin
    public void mostrarRanking(Scanner scanner)
}
```
**Lógica de `mostrarRanking()`:**
1. Llamar `service.checkAndClosePeriodIfDue()` (cierra automáticamente si corresponde)
2. Si `service.isCurrentPeriodOpen()`: imprimir aviso `"Mostrando ranking del trimestre anterior. El trimestre actual aún está en curso."`
3. Llamar `service.generarRanking()`
4. Si la lista está vacía: `"Aún no hay trimestres cerrados con datos suficientes."`
5. Si tiene datos: imprimir tabla con posición, nombre y promedio (2 decimales)
6. **Lógica de empate:** al generar el ranking, si dos estudiantes tienen el mismo promedio (comparar con `Math.abs(a - b) < 0.001`), asignarles la misma posición; el siguiente estudiante salta la posición correspondiente

**Ejemplo de tabla de salida:**
```
╔══════════════════════════════════════════╗
║   RANKING TRIMESTRAL — Trimestre 1 2026  ║
╠══════╦═════════════════════╦═════════════╣
║  POS ║ ESTUDIANTE          ║ PROMEDIO    ║
╠══════╬═════════════════════╬═════════════╣
║  1   ║ Ana García          ║    4.80     ║
║  2   ║ Luis Martínez       ║    4.50     ║
║  3   ║ María López         ║    4.30     ║
║  3   ║ Juan Pérez          ║    4.30     ║
╚══════╩═════════════════════╩═════════════╝
```

---

---

# 🛠️ FEAT-SHARED — Utilidades e Integración

---

## ISSUE-024 — Menú de consola interactivo y navegación
**Asignado a:** `@dev4` | **Prioridad:** 🔴 Alta

### Tarea 24.1 — Completar `MenuHelper.java` con todos los menús del sistema
*(La clase base se creó en Tarea 4.1; aquí se completa)*  
**Qué hacer:**
- Agregar constantes para las opciones de cada menú (evitar magic numbers)
```java
public class MenuHelper {
    // Menú principal
    public static final int MENU_LOGIN = 1;
    public static final int MENU_SALIR = 2;

    // Menú Admin
    public static final int ADMIN_ESTUDIANTES = 1;
    public static final int ADMIN_PROFESORES  = 2;
    public static final int ADMIN_MATERIAS    = 3;
    public static final int ADMIN_RANKING     = 4;
    public static final int ADMIN_SALIR       = 5;

    // Menú Profesor
    public static final int PROF_ESTUDIANTES = 1;
    public static final int PROF_TAREAS      = 2;
    public static final int PROF_NOTAS       = 3;
    public static final int PROF_SALIR       = 4;

    // Menú Estudiante
    public static final int EST_NOTAS_TAREA  = 1;
    public static final int EST_PROM_MATERIA = 2;
    public static final int EST_PROM_GENERAL = 3;
    public static final int EST_SALIR        = 4;

    // Métodos: mostrarMenuPrincipal, mostrarMenuAdmin,
    // mostrarMenuProfesor, mostrarMenuEstudiante,
    // leerOpcion, limpiarPantalla, imprimirSeparador, imprimirTabla
}
```
- `imprimirTabla(String[] headers, List<String[]> rows)`: alinea columnas con padding dinámico

---

## ISSUE-025 — Manejo global de excepciones y validaciones
**Asignado a:** `@dev4` | **Prioridad:** 🟡 Media

### Tarea 25.1 — Completar `Validator.java` con validaciones adicionales
*(La clase base se creó en Tarea 2.4; aquí se amplía)*  
**Qué hacer:**
```java
// Agrega estos métodos:

// Valida formato de fecha "yyyy-MM-dd". Devuelve true si es válido o si es vacío (opcional).
public static boolean isValidDateOrEmpty(String fecha)

// Valida que el ID no sea null ni vacío
public static boolean isValidId(String id)
```

### Tarea 25.2 — Manejo global de excepciones en `App.java`
**Qué hacer:**
- Envolver el loop principal en `try-catch (Exception e)` para capturar errores inesperados
- Si se captura algo que no es `AppException`: imprimir `"Error inesperado: " + e.getMessage()` y continuar el loop sin cerrar el programa
- Agregar `Runtime.getRuntime().addShutdownHook()` para cerrar el `Scanner` limpiamente al salir

---

## ISSUE-026 — Tests unitarios para servicios críticos
**Asignado a:** `@dev4` (coordinar con el equipo) | **Prioridad:** 🟡 Media

### Tarea 26.1 — Tests para `AuthService`
**Archivo:** `src/test/java/com/school/auth/AuthServiceTest.java`  
**Qué hacer:**
```java
@Test void seedDefaultAdmin_createsAdminOnFirstRun()
@Test void seedDefaultAdmin_doesNotDuplicateOnSecondRun()
@Test void login_returnsUserOnValidCredentials()
@Test void login_throwsOnInvalidPassword()
@Test void login_throwsOnNonExistentUser()
@Test void createAccount_throwsOnNonInstitutionalEmail()
@Test void createAccount_throwsOnDuplicateEmail()
@Test void createAccount_hashesPasswordWithBCrypt()
```
- Usar archivos JSON temporales en `src/test/resources/` para no contaminar datos reales
- Limpiar los archivos antes de cada test con `@BeforeEach`

---

### Tarea 26.2 — Tests para `GradeService`
**Archivo:** `src/test/java/com/school/grade/GradeServiceTest.java`  
**Qué hacer:**
```java
@Test void calcularPromedioPorMateria_returnsCorrectAverage()
@Test void calcularPromedioPorMateria_returnsEmptyWhenNoGrades()
@Test void calcularPromedioGeneral_excludesSubjectsWithNoGrades()
@Test void calcularPromedioGeneral_returnsEmptyWhenNoGradesAtAll()
@Test void create_throwsWhenGradeOutOfRange()
@Test void create_throwsWhenGradeAlreadyExists()
```

---

### Tarea 26.3 — Tests para `RankingService`
**Archivo:** `src/test/java/com/school/ranking/RankingServiceTest.java`  
**Qué hacer:**
```java
@Test void generarRanking_returnsEmptyWhenNoClosedPeriod()
@Test void generarRanking_assignsSamePositionOnTie()
@Test void generarRanking_skipsPositionAfterTie()
@Test void generarRanking_correctlyOrdersByAverageDescending()
@Test void checkAndClosePeriodIfDue_closesPeriodAfter90Days()
@Test void checkAndClosePeriodIfDue_doesNotCloseBeforeDue()
```

---

### Tarea 26.4 — Tests para `ProfessorService`
**Archivo:** `src/test/java/com/school/professor/ProfessorServiceTest.java`  
**Qué hacer:**
```java
@Test void create_throwsOnNonInstitutionalEmail()
@Test void create_throwsOnDuplicateEmail()
@Test void countTasksByProfessor_returnsCorrectCount()
@Test void delete_doesNotDeleteOrphanedTasks()
@Test void delete_doesNotDeleteOrphanedGrades()
```

---

---

# 📊 Resumen de Tareas por Developer

| Developer | Issues | Nº Tareas | Tareas clave |
|-----------|--------|-----------|--------------|
| `@dev1` | ISSUE-001 a 005 | 13 | Estructura Maven, `JsonFileManager`, `Validator`, `AppException`, `User` POJO, `AuthService` (seed + login), `AuthController`, `MenuHelper`, flujo de sesión en `App.java` |
| `@dev2` | ISSUE-006 a 014, 027 a 030 | 22 | `Student`, `Professor`, `Subject` POJOs + repos + services + controllers, seed de materias, eliminación con huérfanas |
| `@dev3` | ISSUE-015 a 020 | 14 | `Task`, `Grade` POJOs + repos + services + controllers, cálculo de promedios por materia y general, flujos de vista del estudiante |
| `@dev4` | ISSUE-021 a 026 | 13 | `Period` POJO, `RankingService` (cierre automático + empates), `RankingController`, `MenuHelper` completo, tests unitarios de los 4 servicios críticos |

---

# 🔗 Orden de implementación recomendado (dependencias entre tareas)

```
Semana 1
  @dev1: ISSUE-001 → ISSUE-002 → ISSUE-003 → ISSUE-004 → ISSUE-005
         (base del proyecto + auth completo + menú principal)

Semana 2
  @dev2: ISSUE-006 a 011 (estudiantes) + ISSUE-027 a 030 (profesores)
  @dev3: ISSUE-015 a 016 (tareas) — depende de subjects (seed de @dev2)
  @dev4: ISSUE-024 + ISSUE-025 (shared utils — no dependen de nadie)

Semana 3
  @dev2: ISSUE-012 a 014 (materias)
  @dev3: ISSUE-017 a 020 (notas + vista estudiante)
  @dev4: ISSUE-021 a 023 (ranking — depende de grades de @dev3)

Semana 4
  @dev4: ISSUE-026 (tests — depende de todos los services)
  Todos: integración final en App.java, pruebas end-to-end manuales
```