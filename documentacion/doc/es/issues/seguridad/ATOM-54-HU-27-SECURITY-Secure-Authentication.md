# ATOM-54 · HU-27 · SECURITY — Secure Authentication (Implementación)

## Metadata

| Campo | Valor |
|---|---|
| Issue | ATOM-54 |
| Historia de usuario | HU-27 |
| Tipo | Feature de seguridad (AuthN/AuthZ) |
| Repo principal | **`Atom-agent`** (backend Python/FastAPI/gRPC) |
| Repo secundario | `Atom-app` (cliente: canal TLS + envío de token) |
| Fecha | 2026-06-24 |
| ADRs | ADR-001 (hashing e identidad = backend) |
| Relacionadas | ATOM-49 (gate de seguridad runtime, cliente), auditoría `document.md` §9 |

> **Historia (HU-27).** *Como usuario de Atom, quiero poder iniciar sesión de forma segura
> con mi correo dentro de la aplicación, para sentir la confianza de que mi cuenta es
> privada y sincronizar mis ajustes personalizados al servidor de forma segura.*
>
> **Criterios de aceptación originales:**
> 1. Implementar el caso de uso de autenticación que valide credenciales de email y contraseñas cifradas.
> 2. Desarrollar el adapter de infraestructura en el backend para almacenar y consultar perfiles de usuario en una colección **MongoDB** nueva y dedicada.
> 3. Configurar la transferencia segura de datos de autenticación sobre el canal **gRPC** existente.
> 4. Implementar hashing robusto en el backend para almacenar contraseñas sin texto plano.
>
> **Extensión (este documento):** además de email/contraseña, se soporta **inicio de sesión con
> Google (OAuth 2.0 / OIDC)** por usuario, como **segundo proveedor** de autenticación. Google solo
> prueba la identidad inicial; a partir de ahí el sistema emite y usa **sus propios** tokens de sesión
> (igual que el login con contraseña). Ver **§7.5**.

---

## 1. Por qué esta issue es crítica (estado de seguridad actual)

Hoy **no existe autenticación ni autorización en ninguna parte del sistema** (verificado contra
código en ambos repos). El `user_id` lo pone el cliente como string sin firmar y todo el tráfico
viaja en texto plano. HU-27 es el cimiento que cierra el riesgo agregado **Crítico** del proyecto.

### 1.1 Análisis profundo de huecos de seguridad (todo el proyecto)

Consolidado de la auditoría doble (backend + cliente) y verificado `archivo:línea`. La columna
**HU-27** indica si esta issue lo cierra (✅), lo cierra parcialmente (🟡) o queda fuera de alcance (⬜).

#### Backend — `Atom-agent`

| Sev | Hueco | Ubicación | HU-27 |
|---|---|---|---|
| 🔴 CRÍTICO | Sin AuthN/AuthZ en gRPC ni HTTP | `infrastructure/grpc/server.py:35-159`, `api/controllers.py`, `main.py:46-84` | ✅ |
| 🔴 CRÍTICO | `user_id` controlado por el cliente → suplantación | `grpc/server.py:39,52-54,93`, `application/use_cases/execute_command.py:34` | ✅ |
| 🔴 CRÍTICO | Memoria Qdrant sin aislamiento multi-tenant (lectura/envenenamiento cruzado) | `adapters/vector_store/qdrant_adapter.py:147-166`, `application/agents/nodes.py:39,96` | ✅ |
| 🔴 CRÍTICO | gRPC en texto plano, `add_insecure_port`, bind `[::]` | `grpc/server.py:163-165` | ✅ |
| 🔴 CRÍTICO | `requires_confirmation` no impuesto en servidor (acciones sensibles) | `execute_command.py:113-125`, `catalog.py:80,91,169` | 🟡 (interceptor + base; gate completo = issue aparte) |
| 🟠 ALTO | HTTP/uvicorn sin TLS, bind `0.0.0.0` | `main.py:91,95` | 🟡 |
| 🟠 ALTO | Excepciones internas devueltas al cliente (`str(exc)`) | `grpc/server.py:59,97`, `api/controllers.py:60,124,193`, `api/exceptions.py` (vacío) | 🟡 |
| 🟠 ALTO | gRPC sin límite de mensaje / concurrencia / timeouts → DoS | `grpc/server.py:163` | ⬜ (recomendado junto) |
| 🟠 ALTO | Qdrant (6333) y Kokoro (8880) publicados al host sin auth | `docker-compose.yml:4-12` | ⬜ |
| 🟠 ALTO | Contenedor corre como root | `Dockerfile:1-17` | ⬜ |
| 🟡 MEDIO | Prompt injection: texto de pantalla/memoria entra al prompt sin saneo | `adapters/intent/gemini_function_calling_adapter.py:47-61`, `nodes.py:42-54` | 🟡 (aislamiento de memoria reduce el vector persistente) |
| 🟡 MEDIO | `/chat` sin `max_length`; sin límite de body; `/docs` abierto | `api/schemas.py:24`, `main.py:42` | ⬜ |
| 🔵 BAJO | `args` de la tool no validados contra `ParameterSpec` | `gemini_function_calling_adapter.py:122-147` | ⬜ |

#### Cliente — `Atom-app`

| Sev | Hueco | Ubicación | HU-27 |
|---|---|---|---|
| 🔴 CRÍTICO | gRPC en texto plano (`usePlaintext()`) | `infrastructure/adapter/grpc/InteractionGrpcAdapter.java:39-41` | ✅ |
| 🟠 ALTO | Cleartext habilitado para IP de **producción** (`167.233.32.146`) | `res/xml/network_security_config.xml:21` | ✅ |
| 🟠 ALTO | Identidad anónima falsificable (UUID en SharedPreferences, sin token) | `app/di/AppContainer.java:148-160`, `InteractionGrpcAdapter.java:52,130` | ✅ |
| 🟠 ALTO | `MAKE_CALL`/`SEND_MESSAGE` sin confirmación en el loop autónomo | `CommandRepository.java:136-153`, `DestructiveActionPolicy.java:30` | ⬜ (issue de acciones) |
| 🟠 ALTO | `DestructiveActionPolicy` evadible (gate por keywords) | `domain/action/DestructiveActionPolicy.java:16-30` | ⬜ |
| 🟠 ALTO | Release sin `minify`/R8 + logging de datos sensibles | `build.gradle.kts:35`, `AtomAccessibilityService.java:538`, `CommandRepository.java:132,164` | ⬜ |
| 🟡 MEDIO | `allowBackup="true"` (exfiltra DB de chat + identidad de sesión) | `AndroidManifest.xml:63` | 🟡 (excluir `atom_session`) |
| 🟡 MEDIO | Sin certificate pinning; backend por IP cruda | `network_security_config.xml:21`, `build.gradle.kts:38,44` | 🟡 |
| 🟡 MEDIO | Tapjacking en diálogos de confirmación overlay | `FloatingBubbleService.java:987-1015` | ⬜ |
| 🟡 MEDIO | Resolución de contacto por substring difuso → llamada equivocada | `ContactsContractResolver.java:65` | ⬜ |
| 🔵 BAJO | `userId` distinto entre chat y comandos | `AppContainer.java:70` vs `CommandRepository.java:48` | 🟡 |

> **Verificado OK (no son huecos):** servicios sensibles `exported="false"`; accesibilidad exige
> `BIND_ACCESSIBILITY_SERVICE`; sin secretos embebidos (`local.properties` solo `sdk.dir`, `BuildConfig`
> solo host/puerto); `.env` en `.gitignore`; el gate runtime de ATOM-49 está bien integrado y es
> fail-closed.

### 1.2 Qué cierra HU-27 (alcance de esta issue)

HU-27 entrega el **cimiento de identidad** del que dependen casi todos los huecos CRÍTICOS:

- ✅ AuthN real (registro + login con email/contraseña hasheada).
- ✅ Identidad verificada: el `user_id` se **deriva de un token**, no del payload.
- ✅ Transporte cifrado: **TLS** en gRPC (backend) + canal TLS en el cliente.
- ✅ Aislamiento de memoria por usuario (Qdrant filtrado) → "mi cuenta es privada".
- ✅ Persistencia segura de perfiles + ajustes en **MongoDB**, contraseñas con **Argon2id**.

Fuera de alcance (issues separadas, referenciadas en §9): gate de confirmación server-side completo,
endurecimiento de contenedor/puertos, R8/logging del cliente, pinning, DoS/rate-limiting.

---

## 2. Threat model de la autenticación

**Activos:** credenciales (email + hash), tokens de sesión, perfil y ajustes del usuario, memoria
semántica por usuario.

**Atacantes y vectores:**
- **MITM en la red** (hoy todo en claro): captura credenciales/tokens, reescribe respuestas que
  dirigen el loop de accesibilidad. → Mitiga: **TLS** (+ pinning como mejora).
- **Suplantación de identidad** (hoy `user_id` libre): leer/contaminar la memoria y la sesión de otro.
  → Mitiga: `user_id` derivado de **token firmado** + filtro de memoria por usuario.
- **Robo de base de credenciales** (si se filtra Mongo): cracking offline. → Mitiga: **Argon2id**
  (memory-hard), nunca texto plano, sin pepper en el repo.
- **Replay / token robado:** → Mitiga: access token de **vida corta** + refresh **revocable** (TTL).
- **Enumeración de usuarios / fuerza bruta:** respuestas genéricas + rate limiting por email/IP.

**Supuestos:** el hashing y la identidad viven en el backend (ADR-001); el cliente solo custodia el
token de forma segura y lo envía por TLS.

---

## 3. Diseño hexagonal (backend `Atom-agent`)

Regla de dependencias: `api/grpc → application → domain`; `adapters` implementan `ports`.

```
domain/
  user/models.py            User, Credentials, UserSettings (value objects puros)
  auth/models.py            AuthToken, TokenPair, Principal
  errors.py                 + AuthenticationError, UserAlreadyExistsError, InvalidTokenError
ports/
  user_repository_port.py   UserRepositoryPort   (CRUD/lookup de usuario)
  password_hasher_port.py   PasswordHasherPort    (hash/verify/needs_rehash)
  token_service_port.py     TokenServicePort      (issue/verify access + refresh)
application/use_cases/
  register_user.py          RegisterUserUseCase
  authenticate_user.py      AuthenticateUserUseCase  (login)
  refresh_session.py        RefreshSessionUseCase
adapters/
  user_store/mongo_user_repository.py    (motor, colección `users`)
  security/argon2_password_hasher.py     (argon2-cffi, Argon2id)
  security/jwt_token_service.py          (PyJWT RS256 + refresh opaco en Redis)
infrastructure/
  config.py                 + MONGO_URL/DB, JWT keys, TTLs, TLS cert paths, REDIS_URL
  container.py              + wire de los nuevos puertos/adapters/use cases
  grpc/auth_interceptor.py  (NUEVO) valida token en metadata → inyecta Principal en el contexto
  grpc/server.py            + handlers Register/Login/Refresh; TLS; interceptor
api/
  controllers.py + schemas.py   (opcional) /auth/register, /auth/login espejo HTTP
proto/atom_agent.proto      + RPCs y mensajes de auth (fuente de verdad → regenerar stubs)
```

### 3.1 Responsabilidad por pieza

| Pieza | Capa | Responsabilidad |
|---|---|---|
| `User`, `Credentials`, `UserSettings` | dominio | Estado puro; `User` solo guarda **hash**, nunca texto plano |
| `RegisterUserUseCase` | aplicación | Valida formato → verifica unicidad → hashea → persiste |
| `AuthenticateUserUseCase` | aplicación | Busca por email → verifica hash → emite `TokenPair` |
| `RefreshSessionUseCase` | aplicación | Valida refresh (revocable) → rota tokens |
| `PasswordHasherPort` | puerto | Abstrae Argon2id (testeable con fake) |
| `TokenServicePort` | puerto | Abstrae emisión/validación de tokens |
| `UserRepositoryPort` | puerto | Abstrae Mongo (lookup por email, save, settings) |
| `Argon2PasswordHasher` | adapter | `argon2-cffi`; expone `needs_rehash` para subir parámetros |
| `JwtTokenService` | adapter | Access JWT RS256 corto + refresh opaco en Redis (revocable) |
| `MongoUserRepository` | adapter | `motor`; índice único en `email` |
| `AuthInterceptor` | infra gRPC | Deriva el `Principal` del token; rechaza `UNAUTHENTICATED` |

---

## 4. Criterio 1 — Caso de uso de autenticación

```python
# application/use_cases/authenticate_user.py
class AuthenticateUserUseCase:
    def __init__(self, users: UserRepositoryPort, hasher: PasswordHasherPort,
                 tokens: TokenServicePort):
        self._users, self._hasher, self._tokens = users, hasher, tokens

    async def execute(self, email: str, password: str) -> TokenPair:
        user = await self._users.find_by_email(email.strip().lower())
        # Respuesta genérica e idéntica para "no existe" vs "password incorrecto"
        # (evita enumeración de usuarios). Verificar igual contra un hash dummy
        # para no filtrar la existencia por timing.
        if user is None or not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError("invalid_credentials")
        if self._hasher.needs_rehash(user.password_hash):
            await self._users.update_password_hash(user.id, self._hasher.hash(password))
        return self._tokens.issue_pair(user_id=user.id, email=user.email)
```

```python
# application/use_cases/register_user.py
class RegisterUserUseCase:
    async def execute(self, email: str, password: str, display_name: str) -> User:
        norm = email.strip().lower()
        _validate_email(norm); _validate_password_strength(password)   # longitud/clase, NO regex anti-inyección
        if await self._users.find_by_email(norm) is not None:
            raise UserAlreadyExistsError()
        user = User.new(email=norm, password_hash=self._hasher.hash(password),
                        display_name=display_name)
        return await self._users.save(user)
```

> **Nota:** la contraseña **no** pasa por el validador de inyección (`'`, `;`, `--` son válidos en
> passwords fuertes); se valida solo longitud/complejidad. Misma lección que ATOM-49 §3.2.

---

## 5. Criterio 2 — Adapter MongoDB (colección `users`)

### 5.1 Esquema de la colección

```jsonc
// db: atom, collection: users
{
  "_id": "ObjectId | uuid",          // user_id
  "email": "usuario@dominio.com",    // normalizado (lower/trim), ÚNICO
  "password_hash": "$argon2id$...",  // OPCIONAL (null en cuentas solo-Google); nunca texto plano
  "google_sub": "1078...e9",         // OPCIONAL: id estable de Google (único si presente)
  "auth_providers": ["password", "google"],   // métodos vinculados a esta cuenta
  "display_name": "Carlos",
  "active": true,
  "settings": { /* ajustes personalizados sincronizados desde el cliente */ },
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Índices:**
- `db.users.createIndex({ email: 1 }, { unique: true })` — unicidad garantizada por Mongo (evita carrera de doble registro).
- `db.users.createIndex({ google_sub: 1 }, { unique: true, sparse: true })` — único cuando existe; `sparse` para no chocar entre cuentas sin Google.

> Una cuenta puede tener **solo password**, **solo Google**, o **ambos** vinculados (`auth_providers`).
> Las cuentas solo-Google tienen `password_hash = null`.

### 5.2 Adapter (async, `motor`)

```python
# adapters/user_store/mongo_user_repository.py
class MongoUserRepository(UserRepositoryPort):
    def __init__(self, client: AsyncIOMotorClient, db: str):
        self._col = client[db]["users"]

    async def ensure_indexes(self) -> None:
        await self._col.create_index("email", unique=True)

    async def find_by_email(self, email: str) -> User | None:
        doc = await self._col.find_one({"email": email})
        return _to_domain(doc) if doc else None

    async def save(self, user: User) -> User:
        try:
            await self._col.insert_one(_to_doc(user))
        except DuplicateKeyError:
            raise UserAlreadyExistsError()
        return user
    # update_password_hash, update_settings, find_by_id ...
```

**Infra:** añadir `MONGO_URL`/`MONGO_DB` a `config.py`, servicio `mongo` en `docker-compose.yml`
(**sin** publicar el puerto al host — solo red interna), dependencia `motor` en `requirements.txt`/`pyproject.toml`,
y `await repo.ensure_indexes()` en el arranque (`container.build_container` / lifespan).

---

## 6. Criterio 4 — Hashing robusto (Argon2id)

```python
# adapters/security/argon2_password_hasher.py
from argon2 import PasswordHasher, exceptions

class Argon2PasswordHasher(PasswordHasherPort):
    def __init__(self):
        # Argon2id; parámetros de referencia OWASP (ajustar por benchmark del host)
        self._ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4,
                                  hash_len=32, salt_len=16)

    def hash(self, raw: str) -> str:
        return self._ph.hash(raw)                      # sal aleatoria embebida

    def verify(self, raw: str, encoded: str) -> bool:
        try:
            return self._ph.verify(encoded, raw)
        except exceptions.VerifyMismatchError:
            return False

    def needs_rehash(self, encoded: str) -> bool:
        return self._ph.check_needs_rehash(encoded)    # permite subir el costo con el tiempo
```

Dependencia: `argon2-cffi`. **Nunca** loguear la contraseña ni el hash. (Alternativa aceptable:
`bcrypt` vía `passlib`, pero Argon2id es la recomendación OWASP por ser memory-hard.)

---

## 7. Criterio 3 — Transferencia segura por gRPC

### 7.1 Contrato del proto (fuente de verdad: `Atom-agent/proto/atom_agent.proto`)

```proto
service AtomAgentService {
  // --- Auth: NO requieren token ---
  rpc Register               (RegisterRequest)   returns (AuthResponse);
  rpc Login                  (LoginRequest)      returns (AuthResponse);
  rpc AuthenticateWithGoogle (GoogleAuthRequest) returns (AuthResponse);
  rpc RefreshToken           (RefreshRequest)    returns (AuthResponse);

  // --- Existentes: ahora REQUIEREN metadata "authorization: Bearer <jwt>" ---
  rpc ExecuteCommand (CommandRequest) returns (CommandResponse);
  rpc StreamChat     (MessageRequest) returns (stream MessageResponse);
  rpc Transcribe     (TranscribeRequest) returns (TranscribeResponse);
  rpc Synthesize     (SynthesizeRequest) returns (stream SynthesizeResponse);
}

message RegisterRequest { string email = 1; string password = 2; string display_name = 3; }
message LoginRequest    { string email = 1; string password = 2; }
message GoogleAuthRequest { string id_token = 1; }   // ID token OIDC emitido por Google
message RefreshRequest  { string refresh_token = 1; }
message AuthResponse {
  string access_token  = 1;   // JWT corto (p. ej. 15 min)
  string refresh_token = 2;   // opaco, revocable (Redis, TTL ~30d)
  int64  expires_in    = 3;   // segundos
  string user_id       = 4;
}
```

> **Migración del `user_id`:** los `*Request` existentes (`CommandRequest.user_id`, etc.) **dejan de
> ser fuente de verdad**. El servidor ignora el `user_id` del body y usa el del token. Se mantiene el
> campo por compatibilidad temporal, marcado como deprecado en el proto.

Regenerar stubs y espejar en el cliente:
```bash
cd Atom-agent
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. --pyi_out=. proto/atom_agent.proto
# Luego sincronizar Atom-app/src/main/proto/ai.proto (mismo service/mensajes)
```

### 7.2 TLS en el servidor

```python
# infrastructure/grpc/server.py
with open(cfg.tls_key) as k, open(cfg.tls_cert) as c:
    creds = grpc.ssl_server_credentials([(k.read().encode(), c.read().encode())])
server.add_secure_port(f"{cfg.grpc_host}:{port}", creds)   # ya NO add_insecure_port([::])
```

### 7.3 Interceptor de autorización (deriva la identidad del token)

```python
# infrastructure/grpc/auth_interceptor.py  (NUEVO)
# El package del proto es `com.atom.proto`, por eso la ruta completa del método.
_PUBLIC = {"/com.atom.proto.AtomAgentService/Register",
           "/com.atom.proto.AtomAgentService/Login",
           "/com.atom.proto.AtomAgentService/AuthenticateWithGoogle",
           "/com.atom.proto.AtomAgentService/RefreshToken"}

class AuthInterceptor(grpc.aio.ServerInterceptor):
    def __init__(self, tokens: TokenServicePort): self._tokens = tokens
    async def intercept_service(self, continuation, handler_call_details):
        if handler_call_details.method in _PUBLIC:
            return await continuation(handler_call_details)
        md = dict(handler_call_details.invocation_metadata or ())
        token = (md.get("authorization", "")).removeprefix("Bearer ").strip()
        principal = self._tokens.verify_access(token)   # None si inválido/expirado
        if principal is None:
            return _deny(grpc.StatusCode.UNAUTHENTICATED, "missing/invalid token")
        # inyecta el Principal (user_id) en el contexto para los handlers
        return await continuation(handler_call_details)   # + propagación del principal
```

Cada handler de negocio toma el `user_id` **del Principal autenticado**, no del request.

### 7.4 Aislamiento de memoria por usuario (cierra el CRÍTICO de Qdrant)

`retrieve_memory`/`store_memory` deben usar el `user_id` autenticado y filtrar:

```python
# adapters/vector_store/qdrant_adapter.py — search()
flt = rest.Filter(must=[rest.FieldCondition(
        key="user_id", match=rest.MatchValue(value=user_id))])
hits = await client.search(collection, query_vector=vec, query_filter=flt, limit=k)
```
`store()` añade `user_id` al payload e indexa `user_id` como payload index. Sin esto, "mi cuenta es
privada" no se cumple aunque exista login.

---

## 7.5 · Autenticación con Google (OAuth 2.0 / OIDC) — segundo proveedor por usuario

**Modelo.** Google es un **método de autenticación adicional**, no un sistema de sesión paralelo. El
cliente obtiene un **ID token** de Google (JWT firmado por Google, OIDC); el backend lo **verifica** y
emite **su propio** `TokenPair` (el mismo access JWT + refresh que el login con contraseña). De ahí en
adelante todo el sistema usa nuestros tokens — Google solo prueba la identidad inicial.

### Flujo
1. **Android** (Credential Manager / Google Identity Services) → `id_token`, solicitado con el
   **Web client ID** del servidor como `audience`.
2. Cliente → `AuthenticateWithGoogle(id_token)` por **gRPC/TLS**.
3. **Backend verifica** el `id_token` contra las claves públicas de Google: firma, `exp`,
   `iss ∈ {accounts.google.com, https://accounts.google.com}`, `aud == GOOGLE_OAUTH_CLIENT_ID`, y
   **`email_verified == true`**.
4. **Provisioning / linking:** buscar por `google_sub`; si no existe, buscar por `email` verificado
   para **vincular** una cuenta email/password existente; si tampoco, **crear** usuario federado
   (`password_hash = null`).
5. Emitir `TokenPair` (idéntico al login normal).

### Componentes (hexagonal — se suman a §3)
- **Puerto** `GoogleIdTokenVerifierPort` (`ports/`) → **adapter** `GoogleIdTokenVerifier`
  (`adapters/security/google_id_token_verifier.py`, lib `google-auth`).
- **Use case** `AuthenticateWithGoogleUseCase` (`application/use_cases/authenticate_with_google.py`).
- **Dominio:** `User` soporta identidad federada (`password_hash` opcional, `google_sub`,
  `auth_providers`); `UserRepositoryPort` gana `find_by_google_sub` y `link_google`.

### Verificación del ID token
```python
# adapters/security/google_id_token_verifier.py
from google.oauth2 import id_token
from google.auth.transport import requests as g_requests

class GoogleIdTokenVerifier(GoogleIdTokenVerifierPort):
    def __init__(self, client_id: str):
        self._client_id, self._req = client_id, g_requests.Request()

    def verify(self, raw_id_token: str) -> GoogleIdentity:
        # Valida firma, iss, aud (== client_id) y exp; lanza si algo falla.
        claims = id_token.verify_oauth2_token(raw_id_token, self._req, self._client_id)
        if not claims.get("email_verified"):
            raise AuthenticationError("email_not_verified")
        return GoogleIdentity(sub=claims["sub"],
                              email=claims["email"].strip().lower(),
                              name=claims.get("name"))
```

### Use case (find / link / create)
```python
# application/use_cases/authenticate_with_google.py
class AuthenticateWithGoogleUseCase:
    async def execute(self, raw_id_token: str) -> TokenPair:
        gid = self._verifier.verify(raw_id_token)             # firma + aud + exp + email_verified
        user = await self._users.find_by_google_sub(gid.sub)
        if user is None:
            existing = await self._users.find_by_email(gid.email)
            if existing is not None:
                user = await self._users.link_google(existing.id, gid.sub)   # vincula
            else:
                user = await self._users.save(
                    User.federated(email=gid.email, google_sub=gid.sub, display_name=gid.name))
        return self._tokens.issue_pair(user_id=user.id, email=user.email)
```

### Seguridad específica de Google (crítica)
- **Validar `aud`** contra **nuestro** client ID. Sin esto, un `id_token` emitido para *otra* app de
  Google sería aceptado → suplantación.
- **Exigir `email_verified == true`** antes de vincular por email, o un atacante con un Google de email
  no verificado podría secuestrar una cuenta email/password ajena.
- **Clave de identidad = `sub`** (estable), no el email (el email puede cambiar/reasignarse).
- El `id_token` viaja **solo sobre TLS** (Fase 1C/1D). No se almacena; se verifica y se descarta.
- **Endurecimiento opcional del linking:** si ya existe cuenta email/password con ese email, pedir la
  contraseña (o confirmación explícita) antes de vincular Google, en vez de vincular automáticamente.

### Config
- `GOOGLE_OAUTH_CLIENT_ID` (Web client ID) en `infrastructure/config.py` — **distinto** de
  `GOOGLE_API_KEY` (que es de Gemini). No confundir.
- Dependencia backend: `google-auth`.
- Cliente Android: Android client ID + Web client ID (el `audience`); dependencia Credential Manager /
  Google Identity Services.

---

## 8. Lado cliente (`Atom-app`) — mínimo para HU-27

Por ADR-001 el cliente no hashea ni gestiona identidad; solo:

1. **Canal TLS:** reemplazar `usePlaintext()` por `TlsChannelCredentials` en
   `InteractionGrpcAdapter.java:39-41`; `usePlaintext()` solo bajo `BuildConfig.DEBUG` + loopback.
2. **Quitar cleartext de producción:** eliminar `167.233.32.146` de `network_security_config.xml:21`.
3. **Custodia del token:** guardar access/refresh en **`EncryptedSharedPreferences`** (no en claro),
   no en `atom_session` plano; añadir `authorization: Bearer <jwt>` a la metadata de cada RPC.
4. **`allowBackup`:** excluir `atom_session` y los tokens del backup (`AndroidManifest.xml:63`).
5. **Google Sign-In:** integrar **Credential Manager / Google Identity Services** para obtener el
   `id_token` (con el **Web client ID** como `audience`) y enviarlo por `AuthenticateWithGoogle`; el
   backend devuelve el `TokenPair` que se custodia igual que en email/password (paso 3).

> La **UI de login/registro** y el refresco automático de token son una **issue de cliente aparte**
> (front), no parte de estos 4 criterios. Aquí solo se habilita el contrato y el transporte.

---

## 9. Flujos paso a paso

**Registro:** cliente (TLS) → `Register(email,pwd,name)` → `RegisterUserUseCase` valida + `hash()` +
`save()` (índice único) → emite `TokenPair` → cliente guarda tokens cifrados.

**Login:** `Login(email,pwd)` → `find_by_email` → `verify()` (genérico ante fallo) → `needs_rehash?` →
`TokenPair`.

**Request autenticado:** cliente añade `Bearer <access>` → `AuthInterceptor` valida y deriva `user_id`
→ handler usa ese `user_id` → memoria/acciones aisladas por usuario.

**Refresh:** `RefreshToken(refresh)` → valida contra Redis (revocable) → rota par de tokens.

---

## 10. Mapeo criterios → implementación

| AC | Entregable | Archivos |
|---|---|---|
| 1. Use case de auth | `AuthenticateUserUseCase`, `RegisterUserUseCase` + dominio/puertos | `application/use_cases/*`, `domain/user/*`, `ports/*` |
| 2. Adapter MongoDB | `MongoUserRepository`, colección `users` + índice único | `adapters/user_store/mongo_user_repository.py`, `config.py`, `docker-compose.yml` |
| 3. Transferencia gRPC segura | RPCs de auth + TLS + interceptor + token en metadata | `proto/atom_agent.proto`, `grpc/server.py`, `grpc/auth_interceptor.py`, `jwt_token_service.py` |
| 4. Hashing robusto | `Argon2PasswordHasher` (Argon2id) | `adapters/security/argon2_password_hasher.py` |
| (extensión) Google Auth | `GoogleIdTokenVerifier` + `AuthenticateWithGoogleUseCase` + RPC | `adapters/security/google_id_token_verifier.py`, `application/use_cases/authenticate_with_google.py`, `proto/atom_agent.proto` |
| (privacidad) | Filtro de memoria por `user_id` | `adapters/vector_store/qdrant_adapter.py`, `application/agents/nodes.py` |

---

## 11. Plan de pruebas

**Unitarias (con fakes, sin Mongo/Redis reales — patrón `tests/fixtures/mocks.py`):**
- `RegisterUserUseCase`: éxito; email duplicado → `UserAlreadyExistsError`; password débil → error; el `User` guardado lleva **hash**, no texto plano.
- `AuthenticateUserUseCase`: credenciales válidas → `TokenPair`; password incorrecto y usuario inexistente → **mismo** `AuthenticationError` (anti-enumeración); `needs_rehash` dispara re-hash.
- `Argon2PasswordHasher`: `verify(hash(x), x)` True; `verify` con otra clave False; `hash(x) != x`.
- `JwtTokenService`: token válido verifica; expirado/firma inválida → None; refresh revocado → None.
- `AuthInterceptor`: método público pasa sin token; método protegido sin token o con token inválido → `UNAUTHENTICATED`; token válido inyecta el `user_id` correcto.
- `qdrant_adapter.search`: aplica `Filter(user_id=...)` (un usuario no recibe memoria de otro).

**Integración:** registro→login→llamada autenticada vía `grpc.aio` in-process; Mongo con `mongomock-motor` o testcontainer.

**Gherkin** a añadir junto a `ATOM-33`/`ATOM-35`: "Login con credenciales válidas", "Login rechaza password incorrecto sin revelar si el email existe", "Request sin token es rechazado", "Un usuario no puede leer la memoria de otro".

---

## 12. Criterios de aceptación / DoD

- [ ] Registro y login funcionando con email + Argon2id; el `User` nunca almacena texto plano.
- [ ] **Login con Google** funcionando: el backend verifica el `id_token` (firma, `aud`, `exp`, `email_verified`) y emite el `TokenPair`; soporta cuentas solo-Google, solo-password y vinculadas.
- [ ] Colección `users` en MongoDB con índice **único** en `email`; adapter async (`motor`) cableado en `container`.
- [ ] gRPC con **TLS** (`add_secure_port`); `add_insecure_port`/`[::]` eliminados.
- [ ] `AuthInterceptor` rechaza RPCs no-públicos sin token válido (`UNAUTHENTICATED`); el `user_id` se deriva del token, **no** del body.
- [ ] Memoria Qdrant filtrada por `user_id` (un usuario no lee ni contamina la de otro).
- [ ] Tokens: access corto + refresh revocable (Redis/TTL); logout revoca.
- [ ] Cliente: canal TLS, cleartext de producción eliminado, tokens en `EncryptedSharedPreferences`.
- [ ] Mensajes de error genéricos (sin `str(exc)`); credenciales/hash nunca en logs.
- [ ] Pruebas unitarias + integración en verde.

---

## 13. Decisiones y riesgos

- **JWT (access) + refresh opaco en Redis:** stateless para el camino caliente (valida sin DB) pero
  **revocable** vía el refresh (cierre de sesión, robo). Atar el refresh a Redis conecta con la
  recomendación de Redis ya presente en `document.md` (estado/sesión con TTL). **Mongo = quién eres;
  Redis = que tu sesión sigue viva.**
- **RS256 vs HS256:** preferir RS256 (clave privada solo en el servicio de auth); si se usa HS256,
  secreto fuerte fuera del repo (gestor de secretos), nunca en `.env` plano en prod.
- **Sin pepper en el repo:** si se añade pepper, debe vivir en el gestor de secretos, no versionado.
- **Anti fuerza-bruta/enumeración:** respuestas genéricas + rate limiting por email/IP (se apoya en
  el rate limiting global, hueco A-2 — issue de hardening).
- **Migración:** desplegar TLS + interceptor obliga a actualizar el cliente en el mismo release
  (romper el contrato en claro). Coordinar el bump de `ai.proto` en ambos repos.

---

## 14. Huecos relacionados que esta issue NO cierra (referencias)

Crear/enlazar issues separadas para: gate de confirmación **server-side** de acciones sensibles
(`execute_command.py:113`); endurecer contenedor + no publicar Qdrant/Kokoro (`Dockerfile`,
`docker-compose.yml`); rate limiting/límites de mensaje gRPC (DoS); R8/minify + purga de logs y
tapjacking en el cliente (`build.gradle.kts:35`, `FloatingBubbleService.java:987`); pinning de
certificado; validación de `args` de la tool contra el catálogo. Ver §1.1 para ubicaciones.
