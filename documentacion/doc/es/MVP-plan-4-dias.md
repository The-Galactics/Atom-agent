# Plan de Trabajo MVP — 4 días (Atom)

> **Objetivo del MVP:** Demostrar la tubería completa de decisión de Atom:
> **comando de texto → IA (Gemini) decide una acción → acción estructurada → ejecución/visualización.**
> Consumible vía `curl`/Postman. Demostrable end-to-end al final del día 4.

---

## 0. Alcance y decisiones congeladas

### En alcance (4 días)
1. `Atom-agent` (Python): adaptador **Gemini** con **function calling** que devuelve, en una sola llamada, `texto + acción estructurada`.
2. `Atom-app` (Spring Boot/JVM): **absorbe** la lógica de seguridad/validación/persistencia de `/atom`, añade el **cliente HTTP** hacia Python y expone `POST /api/v1/command`.
3. **3 acciones (sin visión, deep-link/Intent):** `DIAL`, `WHATSAPP`, `OPEN_APP`.
4. Contrato compartido congelado (sección 1) usado como **fixture de prueba en ambos repos** → cero inconsistencia de sincronización.

### Fuera de alcance (post-MVP, fase 5+)
- App **Android nativa** + Accessibility Service + inyección de toques (la parte frágil).
- Visión de pantalla (árbol de accesibilidad → Gemini).
- Migración a **Supabase** (el MVP reutiliza Mongo + Argon2 ya construidos).
- gRPC (el MVP usa REST; gRPC es optimización posterior).
- Memoria vectorial (Qdrant) en la ruta de acción.

### Decisiones de arquitectura congeladas
| Tema | Decisión MVP | Razón |
|---|---|---|
| Tipo de `Atom-app` | Spring Boot JVM (no Android aún) | Android+Accessibility en 4 días = inviable |
| Transporte App↔IA | **REST** (`POST /chat`) | Ya existe el contrato; tolerante a red |
| Cerebro IA | **Gemini** vía `langchain-google-genai` | Mantiene consistencia con LangChain/LangGraph existente |
| Persistencia | **MongoDB Atlas** (migrada de `/atom`) | Ya está construida y funcionando |
| Seguridad auth | **Argon2** (migrada de `/atom`) | Ya construida; Supabase es post-MVP |
| Acciones MVP | `DIAL`, `WHATSAPP`, `OPEN_APP` | Deep-links confiables, sin visión |

---

## 1. CONTRATO COMPARTIDO v1 — *fuente única de verdad* 🔒

> **Regla anti-inconsistencia:** este contrato se congela el **Día 1 antes de escribir lógica**. Se copia **idéntico** en ambos repos como `CONTRACT.md`. Los ejemplos de payload (§1.4) se guardan como **archivos JSON de fixture** y se usan en los tests de los dos lados. Cualquier cambio = nueva versión (`v2`) acordada por ambos responsables.

### 1.1 Endpoint
```
POST {AGENT_BASE_URL}/chat
Content-Type: application/json
X-Request-Id: <uuid>   (recomendado, para trazas)
```

### 1.2 Request (App → Python)
```jsonc
{
  "text": "string, requerido, min 1 char",
  "session_id": "string, opcional, default 'default'"
}
```
> Compatible con el `ChatRequest` actual de `Atom-agent`. **No se rompe nada.**

### 1.3 Response (Python → App)
```jsonc
{
  "text": "string — respuesta natural para el usuario",
  "session_id": "string",
  "action": {
    "type": "DIAL | WHATSAPP | OPEN_APP | NONE",
    "params": { /* depende de type, ver §1.4 */ }
  }
}
```
> Cambio respecto al actual: se **añade** el objeto `action`. Cuando no hay acción, `type = "NONE"` y `params = {}`. Los flujos `/voice/*` existentes **no se tocan**.

### 1.4 Esquema de `action.params` por tipo (estricto) + payloads canónicos

**`DIAL`**
```json
{ "type": "DIAL", "params": { "phone_number": "+573001112233" } }
```
**`WHATSAPP`**
```json
{ "type": "WHATSAPP", "params": { "phone_number": "+573001112233", "message": "Hola, llego en 10 min" } }
```
**`OPEN_APP`** (`app` = clave canónica, NO el package; el mapeo a package vive en `Atom-app`)
```json
{ "type": "OPEN_APP", "params": { "app": "spotify" } }
```
**`NONE`**
```json
{ "type": "NONE", "params": {} }
```

**Tabla de mapeo `app` → package (vive SOLO en Atom-app):**
| `app` (canónico) | Android package |
|---|---|
| `spotify` | `com.spotify.music` |
| `whatsapp` | `com.whatsapp` |
| `youtube` | `com.google.android.youtube` |
| `maps` | `com.google.android.apps.maps` |

### 1.5 Forma de error (reusar la existente de `Atom-agent`)
```json
{ "detail": { "error": { "code": "STRING_CODE", "message": "...", "request_id": "uuid|null" } } }
```
| HTTP | code | Significado |
|---|---|---|
| 400 | `INVALID_REQUEST` | Campo inválido |
| 422 | (FastAPI/Pydantic) | Request malformado |
| 500 | `CHAT_ERROR` | Error interno / LLM |
| 503 | `LLM_PROVIDER_UNAVAILABLE` | Gemini caído / sin key |

### 1.6 Invariantes del contrato (ambos lados deben respetar)
- `action` **siempre** está presente (nunca `null`); ausencia de acción se modela como `NONE`.
- `phone_number` siempre en formato E.164 (`+<código país><número>`), sin espacios.
- `type` es un enum cerrado. Un `type` desconocido en el App ⇒ tratarlo como `NONE` + loguear warning (tolerancia hacia adelante).
- Idempotencia: el App **no** ejecuta la acción dos veces para el mismo `request_id`.

---

## 2. Cronograma 4 días (ambos issues en paralelo + checkpoints)

| Día | Atom-agent (Issue #1) | Atom-app (Issue #2) | Checkpoint de integración |
|---|---|---|---|
| **1** | Congelar contrato. `GeminiAdapter` devolviendo `action=NONE`. `/chat` ya responde con la forma nueva. | Congelar contrato. Scaffolding hexagonal. Migrar User+Argon2+validación+Mongo desde `/atom`. | `curl /chat` devuelve `{text, action:{type:NONE}}` |
| **2** | Acción `DIAL` end-to-end vía function calling. Tests unit del mapeo. | `DeviceAction` (dominio) + `AiAgentHttpAdapter` + `CommandController`. Ejecuta/loguea `DIAL`. | App llama a Python → recibe `DIAL` → lo materializa |
| **3** | Añadir `WHATSAPP` + `OPEN_APP`. Selección de provider por config. | Mapear `WHATSAPP`/`OPEN_APP` (+ tabla package). Tests con `MockWebServer` contra fixtures. | Prueba cruzada de las 3 acciones con fixtures compartidos |
| **4** | (Opc.) Encadenar `/voice/transcribe` → `/chat`. Hardening + `/health`. Docs. | Validación + seguridad en el caso de uso. Hardening. Docs. Demo. | **Demo end-to-end** (script §6) |

**Regla de oro de sincronización:** nadie cambia el contrato después del Día 1 sin acuerdo escrito. Si surge necesidad, se versiona a `v2` y se comunica en ambos issues.

---

# ISSUE #1 — `Atom-agent` (Python): Integración Gemini + Acciones

**Rama:** `feature/ATOM-XX-gemini-actions`
**Responsable:** [IA-Python]

## HU (Historias de Usuario)

- **HU-A1** — *Como* usuario, *quiero* que Atom entienda mi instrucción en lenguaje natural y decida si requiere una acción, *para* que no solo converse sino que actúe.
- **HU-A2** — *Como* cliente (`Atom-app`), *quiero* recibir la acción en un formato estructurado y estable, *para* ejecutarla sin ambigüedad.
- **HU-A3** — *Como* equipo, *quiero* poder cambiar de proveedor LLM por configuración, *para* no acoplarme a un solo proveedor (Open/Closed).

## Criterios de Aceptación

- **CA-A1:** `POST /chat` responde **siempre** con `text`, `session_id` y `action` (§1.3). `action` nunca es `null`.
- **CA-A2:** "Llama a mi mamá al +57 300 111 2233" ⇒ `action.type = "DIAL"`, `params.phone_number = "+573001112233"`.
- **CA-A3:** "¿Qué es la fotosíntesis?" ⇒ `action.type = "NONE"` y `text` con la respuesta.
- **CA-A4:** "Mándale WhatsApp a +57 300 111 2233 diciendo que llego" ⇒ `type = "WHATSAPP"` con `phone_number` y `message`.
- **CA-A5:** "Abre Spotify" ⇒ `type = "OPEN_APP"`, `params.app = "spotify"`.
- **CA-A6:** Si falta `GEMINI_API_KEY`, `/chat` responde `503 LLM_PROVIDER_UNAVAILABLE` (no 500 genérico).
- **CA-A7:** Cambiar `LLM_PROVIDER=nvidia` hace funcionar el chat sin acciones (`NONE`) sin tocar código (solo `.env`).

## Tareas específicas de ejecución (archivo por archivo)

> Respeta la arquitectura hexagonal existente. **No** modifiques `NvidiaGemmaAdapter` (LSP/OCP): se añade un proveedor nuevo, no se altera el viejo.

**T-A1 · Dominio: modelo de acción (puro, sin dependencias externas)**
`domain/action/models.py` (nuevo)
```python
from dataclasses import dataclass, field
from enum import Enum

class ActionType(str, Enum):
    DIAL = "DIAL"
    WHATSAPP = "WHATSAPP"
    OPEN_APP = "OPEN_APP"
    NONE = "NONE"

@dataclass(frozen=True)            # inmutable → seguro en concurrencia
class Action:
    type: ActionType
    params: dict = field(default_factory=dict)

    @staticmethod
    def none() -> "Action":
        return Action(ActionType.NONE, {})
```

**T-A2 · Puerto: planificador de acciones (ISP — interfaz segregada, no se mete en `LLMPort`)**
`ports/action_planner_port.py` (nuevo)
```python
from abc import ABC, abstractmethod
from domain.conversation.models import ChatMessage
from domain.action.models import Action

class ActionPlannerPort(ABC):
    @abstractmethod
    async def plan(self, messages: list[ChatMessage]) -> tuple[str, Action]:
        """Devuelve (texto_para_usuario, accion). Una sola llamada al LLM."""
```

**T-A3 · Adaptador Gemini (implementa el puerto con function calling)**
`adapters/llm/gemini_action_adapter.py` (nuevo). Usar `langchain-google-genai` + `bind_tools`.
```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from domain.conversation.models import ChatMessage
from domain.action.models import Action, ActionType
from ports.action_planner_port import ActionPlannerPort

# Declaración de tools = contrato §1.4 expresado como funciones
@tool
def make_call(phone_number: str) -> str:
    """Inicia una llamada telefónica. phone_number en formato E.164 (+57...)."""
    return "ok"

@tool
def send_whatsapp(phone_number: str, message: str) -> str:
    """Envía un WhatsApp. phone_number en E.164, message es el texto."""
    return "ok"

@tool
def open_app(app: str) -> str:
    """Abre una app. app ∈ {spotify, whatsapp, youtube, maps}."""
    return "ok"

_TOOLS = [make_call, send_whatsapp, open_app]
_TOOL_TO_ACTION = {
    "make_call":    (ActionType.DIAL,     lambda a: {"phone_number": a["phone_number"]}),
    "send_whatsapp":(ActionType.WHATSAPP, lambda a: {"phone_number": a["phone_number"], "message": a["message"]}),
    "open_app":     (ActionType.OPEN_APP, lambda a: {"app": a["app"]}),
}

class GeminiActionAdapter(ActionPlannerPort):
    def __init__(self, api_key: str, model: str):
        self._llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key).bind_tools(_TOOLS)

    async def plan(self, messages: list[ChatMessage]) -> tuple[str, Action]:
        lc = [(m.role, m.content) for m in messages]   # mapear a formato LC
        resp = await self._llm.ainvoke(lc)
        if resp.tool_calls:                            # Gemini decidió actuar
            call = resp.tool_calls[0]
            atype, mapper = _TOOL_TO_ACTION[call["name"]]
            return (resp.content or "", Action(atype, mapper(call["args"])))
        return (resp.content, Action.none())           # solo conversación
```
> **Rendimiento:** una sola llamada al LLM resuelve texto **y** acción (no dos pasadas). Cliente reutilizable (no se recrea por request).

**T-A4 · Fallback para NVIDIA (Liskov-safe, permite `LLM_PROVIDER=nvidia`)**
`adapters/llm/no_action_planner_adapter.py` (nuevo): envuelve un `LLMPort` y siempre devuelve `Action.none()`.

**T-A5 · Config: añadir Gemini + selector de proveedor**
`infrastructure/config.py` — añadir a `Settings`:
```python
llm_provider: str = Field("gemini", env="LLM_PROVIDER")        # gemini | nvidia
gemini_api_key: str | None = Field(None, env="GEMINI_API_KEY")
gemini_model: str = Field("gemini-2.5-flash", env="GEMINI_MODEL")
```

**T-A6 · Wiring en el contenedor (OCP: el selector elige, no se modifican adaptadores)**
`infrastructure/container.py` — construir `action_planner` según `settings.llm_provider` e inyectarlo en `GraphNodes`. Validar key de Gemini en `readiness()`.

**T-A7 · Nodo del grafo usa el planner**
`application/agents/state.py` — añadir `action: Action | None`.
`application/agents/nodes.py` — `generate_response` llama a `self.action_planner.plan(...)` y devuelve `{"response": ChatMessage(...), "action": accion, "messages": [...]}`.
`application/use_cases/chat.py` — `execute()` retorna `(texto, accion)` (tupla) en lugar de solo texto.

**T-A8 · Schema de salida = contrato §1.3**
`api/schemas.py`:
```python
class ActionDTO(BaseModel):
    type: str
    params: dict = {}

class ChatResponse(BaseModel):
    text: str
    session_id: str
    action: ActionDTO            # nuevo, requerido
```
`api/controllers.py` — `chat()` mapea `(texto, accion)` → `ChatResponse(...)`. Si `settings.gemini_api_key` ausente y provider=gemini ⇒ `HTTPException(503, code="LLM_PROVIDER_UNAVAILABLE")`.

**T-A9 · Dependencias**
`requirements.txt` / `pyproject.toml`: añadir `langchain-google-genai`. Fijar versión.

## Casos de Prueba (pytest)

| ID | Test | Entrada | Esperado |
|---|---|---|---|
| TC-A1 | `test_dial_mapping` | mock Gemini → tool_call `make_call(+573001112233)` | `Action(DIAL, {phone_number:"+573001112233"})` |
| TC-A2 | `test_none_when_no_toolcall` | mock Gemini → sin tool_calls | `Action.none()`, `text` no vacío |
| TC-A3 | `test_whatsapp_mapping` | tool_call `send_whatsapp` | `WHATSAPP` con `phone_number` + `message` |
| TC-A4 | `test_open_app_mapping` | tool_call `open_app(spotify)` | `OPEN_APP` con `app:"spotify"` |
| TC-A5 | `test_chat_endpoint_contract` | `POST /chat` (TestClient) | JSON cumple §1.3, `action` presente |
| TC-A6 | `test_missing_key_returns_503` | sin `GEMINI_API_KEY` | HTTP 503, `code=LLM_PROVIDER_UNAVAILABLE` |
| TC-A7 | `test_unknown_tool_is_none` | tool_call con nombre no mapeado | `Action.none()` (no excepción) |

Fixtures: `tests/fixtures/contract/dial.json`, `whatsapp.json`, `open_app.json`, `none.json` (= payloads §1.4).

---

# ISSUE #2 — `Atom-app` (Spring Boot): Backend + migración de `/atom` + cliente IA

**Rama:** `feature/ATOM-XX-app-backend-ai-client`
**Responsable:** [Java-Backend]

## HU (Historias de Usuario)

- **HU-B1** — *Como* usuario, *quiero* enviar un comando y recibir la respuesta + la acción a ejecutar, *para* que Atom haga algo útil.
- **HU-B2** — *Como* sistema, *quiero* validar y registrar al usuario de forma segura (Argon2), *para* proteger sus datos (RNF-05).
- **HU-B3** — *Como* arquitecto, *quiero* que el acceso a la IA esté detrás de un puerto, *para* poder cambiar REST→gRPC sin tocar la lógica de negocio (DIP).

## Criterios de Aceptación

- **CA-B1:** `POST /api/v1/command` con `{sessionId, text}` devuelve `{reply, action:{type, params}}` (mapeo fiel del contrato §1.3).
- **CA-B2:** El `DeviceAction` del dominio refleja exactamente los 4 `type` del contrato; un `type` desconocido se mapea a `NONE` con warning (invariante §1.6).
- **CA-B3:** El registro de usuario persiste en Mongo con contraseña **hasheada con Argon2** (nunca en claro).
- **CA-B4:** Texto vacío o nulo ⇒ `400` con cuerpo de error consistente (no 500).
- **CA-B5:** Si Python no responde / timeout ⇒ `503` controlado (no excepción cruda al cliente).
- **CA-B6:** `OPEN_APP` con `app="spotify"` se materializa con package `com.spotify.music` (tabla §1.4).

## Tareas específicas de ejecución (archivo por archivo)

> Paquete base `com.atom.app`. Replicar la estructura hexagonal de `/atom`. **Migrar = mover + re-empaquetar + re-testear**, no reescribir desde cero.

**T-B1 · Dependencias** — `build.gradle.kts`: añadir
```kotlin
implementation("org.springframework.boot:spring-boot-starter-web")
implementation("org.springframework.boot:spring-boot-starter-validation")
implementation("org.springframework.boot:spring-boot-starter-data-mongodb")
implementation("org.springframework.security:spring-security-crypto")
implementation("org.bouncycastle:bcprov-jdk15on:1.70")
implementation("org.projectlombok:lombok"); annotationProcessor("org.projectlombok:lombok")
testImplementation("org.springframework.boot:spring-boot-starter-test")
testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
```

**T-B2 · Migrar dominio de usuario y seguridad desde `/atom`**
Copiar y re-empaquetar a `com.atom.app.*`:
- `domain/model/User.java`, `domain/model/security/*`, `domain/utils/RiskLevel.java`
- `application/port/in/UserPortIn.java`, `application/port/out/{UserPortOut, security/PasswordEncoderPortOut}.java`
- `application/usecase/UserUseCase.java`
- `infrastructure/security/encoder/Argon2PasswordEncoderAdapter.java`
- `infrastructure/entity/UserEntity.java`, `infrastructure/mapper/UserMapper.java`, `infrastructure/adapter/out/UserOutAdapter.java`
- DTOs de request/response de usuario.
> Validación: la entidad de usuario usa anotaciones `jakarta.validation` (`@NotBlank`, `@Email`).

**T-B3 · Dominio: acción de dispositivo (lado Java del contrato §1.4)**
`domain/model/action/DeviceAction.java` + `ActionType.java` (enum: DIAL, WHATSAPP, OPEN_APP, NONE).
```java
public record DeviceAction(ActionType type, Map<String, String> params) {
    public static DeviceAction none() { return new DeviceAction(ActionType.NONE, Map.of()); }
}
```
`domain/model/AgentReply.java` → `record AgentReply(String reply, DeviceAction action)`.

**T-B4 · Puerto de salida hacia la IA (DIP)**
`application/port/out/AiAgentPort.java`
```java
public interface AiAgentPort {
    AgentReply sendCommand(String sessionId, String text);   // abstracción, sin HTTP
}
```

**T-B5 · Adaptador HTTP (infra) que cumple el contrato**
`infrastructure/adapter/out/ai/AiAgentHttpAdapter.java` — usar `RestClient` (Spring 6+) o OkHttp.
- Lee `app.agent.base-url` de config.
- POST `{base}/chat` con `{text, session_id}`; header `X-Request-Id`.
- Mapea JSON → `AgentReply`. `type` desconocido → `ActionType.NONE` + `log.warn`.
- Timeout configurable; en timeout/IO → lanza excepción de dominio traducida a 503.
```java
@Component
public class AiAgentHttpAdapter implements AiAgentPort {
    private final RestClient client;          // reutilizable, no se crea por request (rendimiento)
    // ... constructor con @Value("${app.agent.base-url}")
    @Override public AgentReply sendCommand(String sessionId, String text) { /* ver CA-B2/B5 */ }
}
```

**T-B6 · Caso de uso de comando (orquestación pura, testeable)**
`application/usecase/CommandUseCase.java`
```java
public class CommandUseCase {
    private final AiAgentPort agent;
    public CommandUseCase(AiAgentPort agent) { this.agent = agent; }
    public AgentReply handle(String sessionId, String text) {
        if (text == null || text.isBlank())
            throw new IllegalArgumentException("text must not be blank");   // → 400
        return agent.sendCommand(sessionId, text);
    }
}
```

**T-B7 · Mapeo `app`→package (vive solo aquí, §1.4)**
`infrastructure/adapter/out/intent/AppPackageResolver.java` — `Map<String,String>` inmutable + método `resolve(String app)`.

**T-B8 · Controlador de entrada**
`infrastructure/adapter/in/web/CommandController.java` — `POST /api/v1/command`, `@Valid CommandRequestDto`, devuelve `CommandResponseDto(reply, action)`.

**T-B9 · Manejo de errores global**
`infrastructure/config/GlobalExceptionHandler.java` (`@RestControllerAdvice`): `IllegalArgumentException`→400, `AiUnavailableException`→503, genérica→500. Cuerpo consistente con §1.5.

**T-B10 · Config**
`src/main/resources/application.yml`:
```yaml
app:
  agent:
    base-url: ${AGENT_BASE_URL:http://localhost:8000}
    timeout-ms: 8000
spring:
  data:
    mongodb:
      uri: ${MONGODB_URI}
```

## Casos de Prueba (JUnit 5 + MockWebServer)

| ID | Test | Entrada | Esperado |
|---|---|---|---|
| TC-B1 | `commandUseCase_blankText_throws` | text="" | `IllegalArgumentException` |
| TC-B2 | `httpAdapter_parsesDialAction` | `MockWebServer` sirve `dial.json` | `AgentReply` con `DeviceAction(DIAL,…)` |
| TC-B3 | `httpAdapter_parsesNone` | sirve `none.json` | `DeviceAction.none()` |
| TC-B4 | `httpAdapter_unknownType_mapsToNone` | type="FLY" | `NONE` + warning |
| TC-B5 | `httpAdapter_timeout_throws503` | server delay > timeout | `AiUnavailableException` |
| TC-B6 | `controller_returnsContractShape` | `POST /api/v1/command` (MockMvc) | JSON `{reply, action:{type,params}}` |
| TC-B7 | `argon2_hashesAndVerifies` | password plano | hash ≠ plano, `verify`=true |
| TC-B8 | `appResolver_spotify` | `"spotify"` | `"com.spotify.music"` |

Fixtures: `src/test/resources/contract/{dial,whatsapp,open_app,none}.json` = **los mismos payloads §1.4** que usa Python (esto es lo que garantiza la sincronización).

---

## 3. Checklist SOLID / Rendimiento / Buenas prácticas (transversal)

**SOLID**
- **S** — Cada clase una responsabilidad: planner ≠ adapter HTTP ≠ use case ≠ controller.
- **O** — Nuevo proveedor LLM o nueva acción **se añade**, no modifica lo existente (`_TOOL_TO_ACTION`, selector de provider).
- **L** — `NoActionPlannerAdapter` y `GeminiActionAdapter` son intercambiables tras `ActionPlannerPort`.
- **I** — `ActionPlannerPort` separado de `LLMPort` (no se obliga a NVIDIA a implementar acciones).
- **D** — Casos de uso dependen de **puertos** (`AiAgentPort`, `ActionPlannerPort`), no de HTTP/SDK concretos.

**Rendimiento**
- Clientes HTTP/LLM **reutilizables** (singletons), nunca creados por request.
- **Una** llamada al LLM por comando (texto+acción juntos).
- Gemini **Flash** (latencia baja) + payloads mínimos (texto, no imágenes).
- Timeouts explícitos en el cliente HTTP del App (evita hilos colgados).
- Modelos de dominio **inmutables** (`record`, `frozen=True`) → seguros sin locks.

**Buenas prácticas**
- Sin secretos en código: `GEMINI_API_KEY`, `MONGODB_URI` solo en `.env`/variables de entorno; `.env` en `.gitignore`.
- Logs con `X-Request-Id` correlacionado en ambos repos.
- Validación en el borde (Pydantic / `jakarta.validation`).
- Errores tipados → HTTP correcto (nunca 500 genérico para fallos esperables).

---

## 4. Definition of Done (MVP)
- [ ] `curl POST /chat` (Python) cumple §1.3 para las 4 acciones + NONE.
- [ ] `curl POST /api/v1/command` (App) devuelve `reply` + `action` correctos llamando a Python real.
- [ ] Las 3 acciones (`DIAL`, `WHATSAPP`, `OPEN_APP`) y `NONE` verificadas end-to-end.
- [ ] Registro de usuario persiste en Mongo con Argon2.
- [ ] Tests verdes en ambos repos (incluyendo los de contrato sobre fixtures compartidos).
- [ ] `CONTRACT.md` idéntico commiteado en ambos repos.
- [ ] README de cada repo con cómo levantar y probar.

## 5. Flujo Git (evitar conflictos entre repos)
- 1 rama por issue: `feature/ATOM-XX-...` saliendo de `develop` en **cada** repo.
- Commits convencionales (`feat:`, `fix:`, `test:`, `docs:`).
- **Orden de merge:** primero Python (Issue #1) hasta tener `/chat` con `action`; el App (#2) integra contra esa versión. Si #2 necesita el endpoint antes, Python entrega primero el stub `action=NONE` (Día 1).
- PRs pequeños, auto-revisados (`/code-review`) antes de pedir revisión humana.

## 6. Script de demo (Día 4)
```bash
# 1) Python responde con acción
curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"text":"Llama al +57 300 111 2233","session_id":"demo"}' | jq

# 2) App orquesta (valida + llama a Python + devuelve acción)
curl -s -X POST localhost:8080/api/v1/command -H 'Content-Type: application/json' \
  -d '{"sessionId":"demo","text":"Abre Spotify"}' | jq

# 3) Conversación sin acción
curl -s -X POST localhost:8080/api/v1/command -H 'Content-Type: application/json' \
  -d '{"sessionId":"demo","text":"¿Qué es la fotosíntesis?"}' | jq
```
</content>
