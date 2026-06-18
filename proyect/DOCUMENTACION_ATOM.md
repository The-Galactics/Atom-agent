# Documentación Completa del Proyecto Atom

> Asistente de IA para Android compuesto por **dos repositorios que se integran**:
> **`Atom-agent`** (cerebro de IA en Python) y **`Atom-app`** (cliente/orquestador en Java/Spring Boot).
>
> Documento generado el 2026-06-17. Incluye: idea del proyecto, arquitecturas, código detallado,
> integración entre repos, y auditoría de seguridad, rendimiento y buenas prácticas.

---

## Tabla de contenidos

1. [Visión general del proyecto](#1-visión-general-del-proyecto)
2. [Glosario de tecnologías (para entender el stack)](#2-glosario-de-tecnologías)
3. [Mapa de los dos repositorios](#3-mapa-de-los-dos-repositorios)
4. [Arquitectura de `Atom-agent` (Python)](#4-arquitectura-de-atom-agent-python)
5. [Recorrido detallado del código de `Atom-agent`](#5-recorrido-detallado-del-código-de-atom-agent)
6. [Arquitectura y estado de `Atom-app` (Java/Spring Boot)](#6-arquitectura-y-estado-de-atom-app-javaspring-boot)
7. [La integración entre los dos repos](#7-la-integración-entre-los-dos-repos)
8. [Flujos completos de extremo a extremo](#8-flujos-completos-de-extremo-a-extremo)
9. [Auditoría de seguridad](#9-auditoría-de-seguridad)
10. [Auditoría de rendimiento](#10-auditoría-de-rendimiento)
11. [Calidad de código y buenas prácticas no aplicadas](#11-calidad-de-código-y-buenas-prácticas-no-aplicadas)
12. [Herramientas recomendadas para optimizar](#12-herramientas-recomendadas-para-optimizar)
13. [Plan de acción priorizado](#13-plan-de-acción-priorizado)

---

## 1. Visión general del proyecto

**Atom** es un **asistente de IA generativa para móviles Android**. Su idea central es eliminar la
complejidad que introducen las distintas capas de personalización de Android (HyperOS de Xiaomi,
OneUI de Samsung, Nothing OS, etc.), que elevan la curva de aprendizaje y crean barreras de
accesibilidad. (`Atom-app/.../docs/eng/technical/01-main-idea.md:3`)

### Qué pretende hacer para el usuario final

- Ser un **asistente conversacional en tiempo real** (por **voz o texto**) que se adapta y aprende.
- No limitarse a escuchar/responder: **crear, planificar y actuar**. Si el usuario no sabe enviar un
  correo, Atom "aprende" el proceso, lo planifica y lo **guarda** para ejecutarlo mejor la próxima vez.
- **Interactuar directamente con el dispositivo** (abrir apps, llamar, mensajear, alarmas, ajustes…)
  mediante automatización a nivel de sistema operativo.
- Mantener un entorno **seguro y privado**, donde **el usuario tiene la última palabra** sobre las
  acciones sensibles (confirmación antes de llamar o enviar mensajes).
- Incluir **tecnología asistiva** para personas con dificultades técnicas o con discapacidad.

### Objetivo y alcance

- **Objetivo general:** sistema **multi-agente** de IA generativa que centraliza tareas del usuario y
  automatiza el flujo manual de gestión del dispositivo. (`02-objectives.md:5`)
- **Alcance del ciclo (6 semanas):** un agente de acción capaz de crear flujos de automatización desde
  lenguaje natural, analizar la interfaz visual y ejecutar secuencias (clics, gestos, escritura) en al
  menos **dos capas de personalización** (OneUI y HyperOS). (`03-scope.md:3`)
- **Objetivos SMART** (`docs/eng/user/01-SMART-objectives.md`): ≥5 tareas de configuración con ≥70 % de
  éxito en distintas capas; aprender 3 flujos nuevos; reducir interacciones físicas ≥65 %; aplicar
  preferencias del usuario en ≥85 % de respuestas.
- **No funcionales clave:** respuesta **< 4 s**, cifrado **AES-256**, funcionar con red 3G, UI de baja
  carga cognitiva (máx. 3 elementos accionables por vista). (`docs/eng/user/02-requirements.md`)

> ⚠️ **Desfase documentación vs. código.** La documentación de `Atom-app` describe un stack de IA con
> **NVIDIA NIM + Gemma 4 + Qwen + ChromaDB**, pero el código real de `Atom-agent` ya **migró a Google
> Gemini**: LLM **Gemini 1.5 Flash**, embeddings **text-embedding-004**, y **Qdrant** (no ChromaDB)
> como base vectorial. La documentación va por detrás de la implementación.

---

## 2. Glosario de tecnologías

Para entender el proyecto necesitas conocer estas piezas. Explicación breve y para qué se usan aquí:

| Tecnología | Qué es | Rol en Atom |
|---|---|---|
| **Python / FastAPI** | Framework web async para construir APIs HTTP. | Expone la API REST de voz y chat del agente (`:8000`). |
| **gRPC** | Sistema de llamadas a procedimientos remotos (RPC) de Google sobre HTTP/2, con contratos binarios definidos en archivos `.proto`. Más rápido y tipado que REST. | Es el **transporte principal** entre el app Java y el agente Python (`:50051`). |
| **Protocol Buffers (`.proto`)** | Lenguaje de definición de mensajes/servicios que gRPC usa para generar código cliente y servidor. | `atom_agent.proto` es el **contrato compartido** entre ambos repos. |
| **Arquitectura Hexagonal (Ports & Adapters)** | Patrón donde la lógica de negocio (dominio) no depende de tecnologías concretas; se comunica con el exterior mediante **interfaces (ports)**, y cada tecnología es un **adaptador** intercambiable. | Es la arquitectura de `Atom-agent`. Permite cambiar de proveedor (p. ej. Gemini→otro LLM) sin tocar la lógica. |
| **Google Gemini** | Familia de LLMs de Google. | LLM conversacional (`gemini-1.5-flash`) + reconocimiento de intención por *function calling*. |
| **Function Calling** | Capacidad del LLM de, en vez de responder texto, "llamar" a una función/herramienta que tú defines, devolviendo argumentos estructurados. | Convierte una orden hablada ("llama a mamá") en una acción estructurada (`MAKE_CALL{target:"mamá"}`). |
| **Embeddings** | Vectores numéricos que representan el significado de un texto; textos similares producen vectores cercanos. | Permiten **memoria semántica**: buscar conversaciones pasadas por similitud. |
| **Qdrant** | Base de datos **vectorial**: almacena embeddings y busca por similitud (distancia coseno). | Memoria semántica de largo plazo del agente. |
| **LangChain** | Librería para orquestar LLMs (prompts, herramientas, modelos). | Envoltura sobre Gemini (`ChatGoogleGenerativeAI`). |
| **LangGraph** | Extensión de LangChain para construir **grafos de estado** (máquinas de estados) que orquestan pasos de un agente. | Orquesta el chat: `retrieve → generate → store`. |
| **Faster-Whisper** | Implementación optimizada del modelo Whisper de OpenAI para **Speech-to-Text (STT)**. | Transcribe el audio del usuario a texto. |
| **Kokoro** | Motor de **Text-to-Speech (TTS)** servido por HTTP con API compatible con OpenAI. | Convierte la respuesta de Atom en voz. |
| **Java 21 / Spring Boot** | Plataforma y framework para construir aplicaciones de servidor en Java. | Es el esqueleto del cliente/orquestador `Atom-app`. |
| **Gradle (Kotlin DSL)** | Herramienta de build para proyectos Java/Kotlin (`build.gradle.kts`). | Compila y gestiona dependencias de `Atom-app`. |
| **Project Loom / Virtual Threads** | Hilos ligeros de Java 21 para alta concurrencia. | Stack previsto (aún no implementado) del lado Java. |
| **Docker / Docker Compose** | Contenedores y orquestación local de varios servicios. | Levanta el stack del agente (API + Qdrant + Kokoro). |

---

## 3. Mapa de los dos repositorios

```
proyect/
├── Atom-agent/                  # CEREBRO DE IA — Python, FastAPI + gRPC, hexagonal
│   ├── main.py                  # Arranque FastAPI + tarea de fondo del servidor gRPC
│   ├── proto/atom_agent.proto   # CONTRATO compartido (gRPC) entre ambos repos
│   ├── domain/                  # Entidades puras de negocio (sin dependencias externas)
│   ├── ports/                   # Interfaces abstractas (LLM, STT, TTS, VectorStore…)
│   ├── adapters/                # Implementaciones concretas (Gemini, Qdrant, Whisper, Kokoro)
│   ├── application/             # Casos de uso + grafo LangGraph (orquestación)
│   ├── api/                     # Controladores/Schemas FastAPI (HTTP)
│   ├── infrastructure/          # Config, inyección de dependencias, logging, gRPC server
│   ├── tests/                   # unit + integration
│   ├── ai/*.md                  # Briefs de arquitectura (prompts), no código
│   ├── ANDROID_CONTRACT.md      # Contrato REST de voz para Android
│   ├── INTENT_ACTIONS_CONTRACT.md  # Contrato de acciones (gRPC ExecuteCommand)
│   ├── GRPC_CONNECTION_TEST.md  # Estado de los 4 RPCs
│   ├── Dockerfile, docker-compose.yml, requirements.txt, pyproject.toml
│
└── Atom-app/Atom-app/           # CLIENTE/ORQUESTADOR — Java 21, Spring Boot (ESQUELETO)
    ├── build.gradle.kts         # Build Gradle (Spring Boot 4.0.6, Java 21)
    ├── src/main/java/com/atom/app/AtomAppApplication.java  # Bootstrap @SpringBootApplication
    ├── src/main/resources/application.properties           # Solo el nombre de la app
    ├── docs/                    # Documentación del proyecto (eng + es)
    │   ├── eng/technical/        # idea, objetivos, alcance, stack, diseño
    │   ├── eng/user/             # objetivos SMART, requisitos
    │   └── eng/agile_methodology/# backlog, acuerdos, DoD, impedimentos
    └── .github/workflow/check-size.yml   # ⚠️ carpeta en singular: no la ejecuta GitHub
```

**Resumen del estado:** Hoy **toda la inteligencia vive en `Atom-agent`** (Python). `Atom-app` (Java)
es un **esqueleto recién generado**: solo arranca el contexto de Spring, **sin** cliente gRPC, sin el
`.proto`, sin controladores ni lógica de integración.

---

## 4. Arquitectura de `Atom-agent` (Python)

### 4.1 Arquitectura Hexagonal (Ports & Adapters)

La regla de oro: **el dominio y los casos de uso no conocen ninguna tecnología concreta**. Hablan con
el exterior a través de **puertos** (interfaces abstractas), y cada tecnología (Gemini, Qdrant, Whisper,
Kokoro) es un **adaptador** que implementa ese puerto. Beneficio: puedes cambiar de proveedor o mockear
todo en tests sin tocar la lógica.

```
            ┌─────────────────────────────────────────────────────┐
   HTTP ───►│  api/ (FastAPI)        infrastructure/grpc (gRPC)     │◄─── gRPC
            ├─────────────────────────────────────────────────────┤
            │  application/  (casos de uso + grafo LangGraph)       │
            ├─────────────────────────────────────────────────────┤
            │  ports/  (interfaces: LLMPort, STTPort, TTSPort, …)   │  ← frontera
            ├─────────────────────────────────────────────────────┤
            │  domain/  (entidades puras: Action, ChatMessage, …)   │  ← núcleo, sin deps
            └─────────────────────────────────────────────────────┘
                         ▲                ▲                ▲
            adapters/    │                │                │
        ┌────────────────┴───┐ ┌──────────┴────┐ ┌─────────┴───────┐
        │ Gemini (LLM/intent)│ │ Qdrant (vector)│ │ Whisper/Kokoro  │
        └────────────────────┘ └────────────────┘ └─────────────────┘
```

### 4.2 Capas

- **`domain/`** — Entidades puras (dataclasses/enums) sin dependencias externas: `ChatMessage`,
  `Action`/`ActionType`, `IntentResult`, `MemoryEntry`, `Transcription`, `SynthesisResult`,
  *value objects* (`AudioFormat`, `Language`, `AudioPayload`) y la jerarquía de errores
  (`DomainError → DomainValidationError`, `ProviderError`).
- **`ports/`** — Interfaces `ABC`: `LLMPort`, `EmbeddingPort`, `HistoryPort`, `IntentRecognizerPort`,
  `SpeechToTextPort`, `TextToSpeechPort`, `VectorStorePort`, `AudioStoragePort`. Convención: `async`
  cuando hay I/O de red (LLM, intent, vector store); síncrono para CPU/local (STT, TTS, embeddings).
- **`adapters/`** — Implementaciones concretas de cada puerto (ver §5.1).
- **`application/`** — Casos de uso (`ChatUseCase`, `ExecuteCommandUseCase`, `TranscribeAudioUseCase`,
  `SynthesizeSpeechUseCase`) y la orquestación con LangGraph (`agents/graph.py`, `nodes.py`, `state.py`).
- **`api/`** — Routers FastAPI (`/chat`, `/voice/transcribe`, `/voice/synthesize`, `/voice/health`),
  schemas Pydantic y mapeo de errores de dominio a códigos HTTP.
- **`infrastructure/`** — `config.py` (settings por entorno), `container.py` (inyección de dependencias),
  `logging.py` (middleware + `X-Request-Id`), `grpc/server.py` (servidor gRPC), `provider_clients.py`
  (cliente HTTP de Kokoro con reintentos).

### 4.3 Dos superficies de red simultáneas

`main.py` arranca **FastAPI (HTTP `:8000`)** y, dentro de su `lifespan`, lanza una **tarea de fondo con
el servidor gRPC (`:50051`)**. Ambas comparten el mismo `AppContainer` (grafo de dependencias).

### 4.4 Degradación elegante (graceful degradation)

El sistema se diseñó para **seguir funcionando aunque falten piezas**:
- Si falta la librería de voz (`faster-whisper`) o `VOICE_ENABLED=false` → los endpoints de voz
  devuelven `503/UNAVAILABLE`, pero el chat sigue.
- Si Qdrant/embeddings no están disponibles → el chat degrada a "solo LLM" (sin memoria).
- Si falta `GOOGLE_API_KEY` → la ruta de intención (`ExecuteCommand`) devuelve `UNAVAILABLE`.
- `readiness()` en `container.py:51-90` reporta el estado de cada proveedor (visible en `/voice/health`).

---

## 5. Recorrido detallado del código de `Atom-agent`

### 5.1 Adaptadores (`adapters/`)

**`adapters/llm/gemini_adapter.py` — `GeminiAdapter(LLMPort)`**
Adaptador del LLM conversacional. En `__init__` crea `ChatGoogleGenerativeAI` con `temperature=0.7`
(`:9-13`). `async chat(messages)` (`:15`) traduce los roles del dominio al formato de LangChain
(`system→system`, `user→human`, otros→`ai`, `:17-20`), invoca `await self.llm.ainvoke(...)` y devuelve
un `ChatMessage(role="assistant", …)`.
> Nota: `LLMPort.chat` declara `temperature`/`max_tokens` opcionales que **este adaptador ignora** (la
> temperatura queda fija en construcción).

**`adapters/embeddings/gemini_embedding_adapter.py` — `GeminiEmbeddingAdapter(EmbeddingPort)`**
`embed_text` y `embed_documents` delegan en `GoogleGenerativeAIEmbeddings.embed_query/embed_documents`.
Ambos métodos son **síncronos**. El modelo por defecto `text-embedding-004` produce vectores de **768**
dimensiones (relevante para el bug de dimensión, ver §10/§11).

**`adapters/embeddings/bge_m3_adapter.py`** — **Archivo vacío (0 bytes)**. Placeholder de un futuro
adaptador BGE-M3; hoy no aporta nada.

**`adapters/intent/gemini_function_calling_adapter.py` — `GeminiFunctionCallingAdapter(IntentRecognizerPort)`**
El reconocedor de intención. Usa `temperature=0.0` (enrutamiento determinista) y **enlaza el catálogo de
herramientas una sola vez** con `llm.bind_tools(openai_tools())` (`:36`). `async recognize(text, …)`:
- Sin tool calls → respuesta conversacional (`ActionType.NONE`, `confidence=0.0`).
- Con tool call → busca la spec con `spec_for_tool(tool_name)`; si la herramienta es desconocida
  (alucinada), degrada a `NONE`; si es válida, devuelve `Action(type, parameters=args)`, `confidence=1.0`
  y `requires_confirmation` heredado del catálogo.
- Cualquier excepción → `ProviderError` (encadenada).

**`domain/intent/catalog.py` — Catálogo de acciones (fuente única de verdad)**
Define `ActionSpec`/`ParameterSpec`. El método `to_openai_tool()` renderiza cada acción como una
definición de función estilo OpenAI que `bind_tools` acepta. El `ACTION_CATALOG` contiene 6 acciones:
`open_app`, `make_call` (confirmación), `send_message` (confirmación, param. opcional `app`), `set_alarm`,
`set_timer`, `toggle_setting` (con `enum` para `setting` y `state`). **Para añadir una acción nueva basta
con añadir un `ActionSpec` aquí e implementar el handler en Android** — nada más cambia en el backend.

**`adapters/vector_store/qdrant_adapter.py` — `QdrantAdapter(VectorStorePort)`**
Memoria semántica. Patrón clave: **conexión y creación de colección perezosas** (`client` como propiedad
lazy, `:33-38`) para que un Qdrant caído no bloquee el arranque. `_ensure_collection` verifica que la
colección tenga `vectors.size == 3072` y, si difiere, **borra y recrea** la colección (`:45-48`).
`store(content, metadata)` embebe el contenido, genera un **ID determinista** con
`uuid.uuid5(NAMESPACE_DNS, content+metadata)` (idempotencia) y hace `upsert`. `search(query, limit=5,
score_threshold=0.5)` embebe la consulta y mapea resultados a `MemoryEntry`.
> Observaciones: la dimensión **3072 está hardcodeada** (incompatible con los 768 del modelo por defecto,
> ver §11); `embed_text` es síncrono pero se llama dentro de métodos `async` (bloquea el event loop).

**`adapters/speech/faster_whisper_adapter.py` — `FasterWhisperAdapter(SpeechToTextPort)`**
STT. Import tolerante (si no está la librería, `WhisperModel=None`). `transcribe(...)` persiste los bytes
a un archivo temporal (`save_to_temp_file`), ejecuta la inferencia **bajo un `threading.Semaphore`**
(limita concurrencia, `MAX_STT_CONCURRENCY`), une los segmentos, extrae `confidence` de `avg_logprob`, y
en `finally` **borra el temporal**. Errores → `ProviderError`.

**`adapters/speech/kokoro_adapter.py` — `KokoroAdapter(TextToSpeechPort)`**
TTS "fino": delega la comunicación HTTP en `KokoroClient`. Aplica defaults de voz/formato, llama
`client.synthesize(...)` y construye `SynthesisResult`.

**`adapters/speech/in_memory_audio_storage_adapter.py`** — Almacén de audio volátil en `dict` (para
tests/local). No se usa en el container.

**`adapters/history/in_memory_history_adapter.py` — `InMemoryHistoryAdapter(HistoryPort)`**
Historial de conversación por sesión en un `dict` en memoria: `get_history`, `add_message`, `clear`.

### 5.2 Casos de uso (`application/use_cases/`)

- **`chat.py` — `ChatUseCase`**: carga historial, construye el `initial_state`, invoca
  `await graph.ainvoke(state)` y persiste los mensajes resultantes; devuelve `ChatOutputDTO`.
- **`execute_command.py` — `ExecuteCommandUseCase`**: ruta de "órdenes". Llama `recognize(...)`; si la
  acción es ejecutable pero sin texto, usa confirmación hablada por defecto `"De acuerdo."`; calcula
  `success` y mapea a `ExecuteCommandOutputDTO`.
- **`transcribe_audio.py` — `TranscribeAudioUseCase`**: valida payload no vacío, MIME en lista blanca
  (`ALLOWED_MIME_TYPES`), tamaño ≤ 10 MiB (mensaje "exceeds maximum size" → 413), `beam_size` 1–10.
- **`synthesize_speech.py` — `SynthesizeSpeechUseCase`**: valida texto no vacío, longitud ≤ 1000,
  `speed` 0.75–1.25.

### 5.3 Orquestación con LangGraph (`application/agents/`)

`build_graph` crea un grafo lineal **`retrieve → generate → store → END`**:
- **`retrieve_memory`**: si la memoria está activa, busca contexto en Qdrant; *best-effort* (errores se
  loguean y se sigue con `context=""`).
- **`generate_response`**: inyecta el contexto en un system prompt (`"Eres Atom. Contexto relevante:…"`),
  añade historial + mensaje de usuario, llama `await llm.chat(messages)`.
- **`store_memory`**: persiste `"Usuario: …\nAtom: …"` en Qdrant.
  > 🐞 **Bug confirmado** (`nodes.py:58-79`): el método **escribe en Qdrant dos veces** y la **primera
  > escritura ocurre ANTES** del `if not self.memory_enabled` y **fuera del `try/except`**. Resultado:
  > (1) escribe aunque la memoria esté deshabilitada; (2) duplica coste de embeddings/upsert; (3) un
  > fallo de Qdrant aquí **rompe el turno de chat** pese al diseño "best-effort".

### 5.4 API HTTP (`api/`)

`controllers.py` construye los routers con **inyección perezosa** (acepta instancia o callable):
- `POST /chat` — ejecuta `ChatUseCase`; captura todo como `500 CHAT_ERROR`.
- `POST /voice/transcribe` — multipart; `503` si STT no disponible; cascada de errores
  (`ValidationError→400`, `DomainValidationError→400/413/415`, `ProviderError→503`).
- `POST /voice/synthesize` — JSON; devuelve **audio binario** (`Response` con `media_type` y
  `Content-Disposition`).
- `GET /voice/health` — readiness por proveedor.
Propaga `X-Request-Id` en todas las respuestas.

### 5.5 Infraestructura (`infrastructure/`)

- **`config.py`** — `Settings` (pydantic-settings) carga todo desde variables de entorno / `.env`,
  cacheado con `@lru_cache`.
- **`container.py`** — Construye el `AppContainer` (todas las dependencias), de forma **defensiva**:
  construye voz/intención dentro de `try/except` y degrada a `None` si fallan; reporta `readiness()`.
- **`logging.py`** — `configure_logging()` (nivel INFO) y un middleware que genera/propaga `X-Request-Id`
  y registra latencia (`request_completed … elapsed_ms`).
- **`provider_clients.py` — `KokoroClient`** — Cliente HTTP (`requests.Session`) con payload compatible
  con OpenAI, **reintentos con backoff exponencial** y `health()`.
- **`grpc/server.py`** — Servidor gRPC `grpc.aio` con los 4 RPCs (ver §7).

### 5.6 Empaquetado

- **`Dockerfile`**: base `python:3.12-slim`, instala `requirements.txt` + `faster-whisper`, `EXPOSE 8000`
  (⚠️ **no expone 50051**), arranca con `uvicorn main:app`.
- **`docker-compose.yml`**: 3 servicios — `kokoro` (`:8880`), `qdrant` (`:6333`), `api` (build local,
  `:8000`); el `api` monta la caché de HuggingFace y depende de los otros dos.
- **`requirements.txt` vs `pyproject.toml`**: **desincronizados** (gRPC/LangChain/Qdrant solo están en
  `requirements.txt`); `langgraph` aparece **duplicado**.

---

## 6. Arquitectura y estado de `Atom-app` (Java/Spring Boot)

> **Estado actual: esqueleto casi vacío** generado por Spring Initializr. Sin lógica de negocio,
> controladores, entidades ni integración gRPC todavía.

- **`build.gradle.kts`**: plugins `java` + `org.springframework.boot` **4.0.6** + dependency-management.
  `group = "com.Atom.app"` (⚠️ `Atom` con mayúscula). **Java toolchain 21**. Dependencias mínimas: solo
  `spring-boot-starter` (¡ni `-web`!), `spring-boot-starter-test`, `junit-platform-launcher`. **No hay
  gRPC, ni LangChain4j, ni PostgreSQL, ni OkHttp.** Tarea `installGitHooks` que copia `scripts/commit-msg`
  a `.git/hooks` y de la que **depende `compileJava`**.
- **`settings.gradle.kts`**: `rootProject.name = "App"`.
- **`AtomAppApplication.java`**: clase `@SpringBootApplication` estándar. ⚠️ El paquete declarado es
  `com.atom.app.app` pero la carpeta es `com/atom/app/` y el `group` es `com.Atom.app` → **tres variantes
  del nombre** (riesgo de no compilar en build estricto).
- **`application.properties`**: una sola línea (`spring.application.name=Atom_app`). Sin puerto, sin
  datasource, sin config gRPC.
- **`AtomAppApplicationTests`**: único test (`@SpringBootTest contextLoads()` vacío).
- **CI/hooks**: `.github/workflow/check-size.yml` (⚠️ carpeta en **singular** → GitHub Actions **no lo
  ejecuta**) que bloquearía push > 500 líneas; `scripts/commit-msg` fuerza Conventional Commits en inglés
  y bloquea acentos/ñ.

### Stack técnico **previsto** (según docs, aún no implementado)

- **Frontend Android nativo**: Android 10+, Java 21, Material Design 3, View Binding, RxJava 3, modo
  oscuro OLED, Lottie.
- **Backend/orquestación**: Spring Boot + **LangChain4j**, **Virtual Threads (Loom)**, arquitectura
  hexagonal + **Dynamic Class Loading** (compilar/cargar skills `.class` generadas por la IA sin
  reiniciar — la base del "aprendizaje"), Python como puente.
- **Persistencia**: PostgreSQL/Supabase (AES-256) + base vectorial.
- **IA prevista**: NVIDIA NIM con **Gemma 4** (orquestadora) y **Qwen** (desarrolladora/visión). TTS
  híbrido (Google Cloud TTS → Android Native → ElevenLabs).

### Proceso ágil (Scrum)

Backlog con puntos Fibonacci. Sprint 1 = Fundación y Conectividad (destaca **US-10 "Python-Java Bridge
(gRPC/REST)", 8 SP** = la pieza de integración). Sprint 2 = Acción, Visión y Aprendizaje. Daily 9:00 AM,
ramas `feature/*`, Conventional Commits, DoD exige arquitectura hexagonal + AES-256 + tests + doc.
La sección de impedimentos del Sprint 1 está **vacía**.

> Nota: `docs/eng/technical/05-system-design.md` no es un diseño de sistema, sino una **Guía de Identidad
> Visual** (tipografías Geist/Lora, negro `#0A0A0C`, lavanda `#B794F4`, máx. 3 elementos por vista).

---

## 7. La integración entre los dos repos

Coexisten **dos canales** de integración App↔Agente:

### 7.1 REST (módulo de voz, Sprint 1) — `ANDROID_CONTRACT.md`

- `POST /voice/transcribe` (multipart) → STT → JSON `{text, language, duration_seconds, confidence,
  provider}`. Audio recomendado: **WAV mono 16 kHz PCM 16-bit**.
- `POST /voice/synthesize` (JSON) → TTS → **bytes `audio/wav`**.
- Header `X-Request-Id` para trazabilidad; errores con shape `{detail:{error:{code,message,request_id}}}`.
- Ejemplos de cliente Java con **OkHttp** (timeout 10 s).

### 7.2 gRPC (transporte principal) — `atom_agent.proto`

Servicio **`AtomAgentService`**, package `com.atom.proto`, `java_package =
"com.atom.infrastructure.adapter.grpc"`. El servidor arranca en **`:50051` en texto plano (inseguro)**.

| RPC | Tipo | Propósito | Estado backend |
|---|---|---|---|
| `ExecuteCommand` | unario | Interpretar una orden de dispositivo | **Conectado** a `ExecuteCommandUseCase` (Gemini function calling)* |
| `StreamChat` | server-streaming | IA conversacional | Conectado a `ChatUseCase`, pero **emite un solo mensaje** (no streamea de verdad) |
| `Transcribe` | unario | Speech-to-Text | Conectado a Faster-Whisper |
| `Synthesize` | server-streaming | Text-to-Speech | Conectado a Kokoro |

\* `GRPC_CONNECTION_TEST.md` lo describía como *placeholder*; el código actual de `server.py:21-55` ya lo
conecta al use case real (la doc va por detrás). Si falta `GOOGLE_API_KEY`/librería → `UNAVAILABLE`.

### 7.3 Contrato de acciones — `INTENT_ACTIONS_CONTRACT.md`

`ExecuteCommand(user_id, command)` devuelve `CommandResponse`:

```proto
message CommandResponse {
  bool   success = 1;
  string out_message = 2;            // texto a hablar/mostrar (listo para TTS)
  string action_type = 3;            // "OPEN_APP", "MAKE_CALL", … o "NONE"
  string parameters_json = 4;        // objeto JSON con los slots de la acción
  float  confidence = 5;             // 1.0 acción, 0.0 conversación
  bool   requires_confirmation = 6;  // confirmar antes de ejecutar si true
}
```

| `action_type` | Slots (`parameters_json`) | ¿Confirma? | API Android sugerida |
|---|---|:--:|---|
| `OPEN_APP` | `app_name` | no | `PackageManager.getLaunchIntentForPackage` |
| `MAKE_CALL` | `target` | **sí** | `Intent.ACTION_CALL` (perm. `CALL_PHONE`) |
| `SEND_MESSAGE` | `recipient`, `body`, `app?` | **sí** | `SmsManager` / deep link |
| `SET_ALARM` | `time` (`HH:MM`), `label?` | no | `AlarmClock.ACTION_SET_ALARM` |
| `SET_TIMER` | `duration_seconds`, `label?` | no | `AlarmClock.ACTION_SET_TIMER` |
| `TOGGLE_SETTING` | `setting` (wifi/bluetooth/flashlight/do_not_disturb), `state` (on/off/toggle) | no | `CameraManager.setTorchMode` / Quick Settings |
| `NONE` | `{}` | no | sin acción, solo hablar `out_message` |

**Expectativas del cliente Android**: enviar el texto reconocido como `command`; parsear
`parameters_json`; si `requires_confirmation` (o confianza baja) pedir confirmación con `out_message`;
despachar por `action_type`; tratar un `action_type` **desconocido como `NONE`** (compatibilidad).

### 7.4 Gaps de integración conocidos

- `Atom-app` (Java) **aún no tiene** el `.proto`, ni stubs, ni `ManagedChannel`, ni dependencias gRPC.
- gRPC sin TLS ni autenticación (solo desarrollo). El `user_id` lo elige el cliente (sin verificación).
- El Dockerfile/compose **no exponen el puerto 50051** → hoy el servidor gRPC no es accesible fuera del
  contenedor.

---

## 8. Flujos completos de extremo a extremo

### 8.1 Comando de voz que ejecuta una acción

```
[Android] graba audio
   └─(REST POST /voice/transcribe)─►[Agent] Faster-Whisper → texto
[Android] recibe texto
   └─(gRPC ExecuteCommand{user_id, command})─►[Agent]
        GeminiFunctionCallingAdapter.recognize → tool_call → Action
        ◄── CommandResponse{action_type, parameters_json, requires_confirmation, out_message}
[Android] si requires_confirmation → pide confirmación al usuario
[Android] ActionRouter despacha la acción (ej. Intent.ACTION_CALL)
   └─(opcional REST POST /voice/synthesize{out_message})─►[Agent] Kokoro → audio
[Android] reproduce la confirmación hablada
```

### 8.2 Conversación libre (chat con memoria)

```
[Android] (gRPC StreamChat{user_id, message}) ─►[Agent] ChatUseCase
   LangGraph: retrieve_memory (Qdrant search) → generate_response (Gemini) → store_memory (Qdrant upsert)
   ◄── MessageResponse{script_token = respuesta completa, finished=true}   (hoy NO streamea token a token)
```

---

## 9. Auditoría de seguridad

> Riesgo agregado actual: **Crítico**. El agente expone **dos superficies de red sin protección**
> (HTTP `:8000` y gRPC `:50051`): sin auth, sin TLS, sin autorización, sin rate limiting.
> Nota positiva: **no hay secretos hardcodeados**, `.env` está en `.gitignore`, y la capa de casos de uso
> ya valida tamaño de audio, MIME, longitud de texto y rangos.

### Críticos

- **C-1 · gRPC sin TLS ni auth** (`infrastructure/grpc/server.py:137`, `add_insecure_port`, bind a `[::]`).
  Cualquiera en la red puede invocar acciones del dispositivo o interceptar tráfico (MITM).
  → *Remediación:* `add_secure_port` con `ssl_server_credentials`; interceptor de auth (token en
  metadata); mTLS en prod; no bindear a `[::]`.
- **C-2 · Sin authn/authz; `user_id`/`session_id` los pone el cliente** (`server.py:21-76`,
  `dtos.py:57-59`, `schemas.py:24`). Permite **suplantación** y **fuga de memoria entre usuarios**:
  además `retrieve_memory` (`nodes.py:31`) busca en **toda** la colección **sin filtrar por sesión**.
  → *Remediación:* derivar la identidad de un token verificado (OAuth2/JWT/API key), nunca del cuerpo;
  filtrar Qdrant por `session_id`/`user_id` con `query_filter`.
- **C-3 · Acciones del dispositivo derivadas de la salida del LLM sin validar**
  (`gemini_function_calling_adapter.py:57-77` copia `dict(args)` crudo). No se validan tipos/enum contra
  el catálogo antes de entregar la acción a Android.
  → *Remediación:* validar `args` contra `ActionSpec`/`ParameterSpec`; imponer `requires_confirmation` en
  el servidor; listas de permitidos para `app_name`, formatos de hora/número.

### Altos

- **A-1 · Excepciones internas devueltas al cliente** (`server.py:41,68`; `controllers.py:51,115,131,168,184`
  con `f"…{exc}"`/`str(exc)`). Filtra rutas, versiones, URLs de proveedores, posibles fragmentos de claves.
  → *Remediación:* mensajes genéricos + `request_id`; el detalle solo en logs.
- **A-2 · Sin rate limiting ni concurrencia acotada → DoS** (HTTP y `grpc.aio.server()` sin
  `maximum_concurrent_rpcs`; sin timeout en llamadas a Gemini). → *Remediación:* `slowapi`/middleware,
  `maximum_concurrent_rpcs`, timeouts, colas con rechazo `429`.
- **A-3 · Validación de tamaño tardía; gRPC sin límite de mensaje** (`controllers.py:102` lee todo el
  multipart en RAM **antes** de validar; `server.py` sin `grpc.max_receive_message_length`).
  → *Remediación:* validar `Content-Length`/streaming antes de bufferizar; fijar límites de mensaje gRPC.
- **A-4 · Contenedor como root, imagen sin endurecer, `COPY . .`** (`Dockerfile:1-17`, sin `USER`, sin
  `.dockerignore`, `faster-whisper` sin pin). → *Remediación:* usuario no root, `.dockerignore`, pins,
  healthcheck, imagen distroless; pin de tags en compose (hoy `:latest`).
- **A-5 · Qdrant/Kokoro expuestos sin auth** (`docker-compose.yml` publica `6333`/`8880` al host; Qdrant
  sin API key). Lectura/borrado de la memoria de todos los usuarios; `_ensure_collection` puede **borrar
  la colección** ante mismatch de dimensión. → *Remediación:* no publicar esos puertos; API key/TLS en
  Qdrant.

### Medios / Bajos (resumen)

- **M-1** Prompt injection directa e **indirecta persistente** (el contexto de memoria, texto de otros
  usuarios, se inyecta sin saneo en el system prompt — `nodes.py:42-54`).
- **M-2** Logging de comandos/mensajes/PII a nivel INFO (`server.py:23-26,59-62`).
- **M-3** Sin CORS; `/docs` activo; `/voice/health` filtra config interna (URLs, modelos, estado de claves).
- **M-4** Secretos en variables de entorno con *fallback* `api_key or ""` (`container.py:174,178`).
- **M-5** Dependencias sin pin / duplicadas / Python inconsistente (3.10 vs 3.11 vs 3.12).
- **M-6** Audio escrito a disco temporal sin endurecer permisos.
- **M-7** `requires_confirmation` no impuesto en backend (frontera de seguridad recae en el cliente).
- **B-1** Bind `0.0.0.0` por defecto. **B-2** Bug de `store_memory` (también riesgo de fiabilidad).
  **B-3** `.idea/` versionado pese a `.gitignore`. **B-4** Sin cabeceras de seguridad HTTP.
- **J-1 (Java)** Sin secretos hardcodeados ni actuator hoy (bien); vigilar actuator al añadirlo; el hook
  acoplado a `compileJava` es un vector de cadena de suministro.

---

## 10. Auditoría de rendimiento

### Críticos

- **STT síncrono dentro de handler gRPC async** (`server.py:97` → `faster_whisper_adapter.py:47-52`):
  la inferencia CPU-bound de Whisper **bloquea el event loop entero**; ningún otro RPC avanza mientras
  transcribe. → *Fix:* `await asyncio.to_thread(use_case.execute, …)` / `run_in_executor` con un
  `ThreadPoolExecutor` dedicado; idealmente puerto STT async.
- **TTS síncrono (`requests` + `time.sleep`) dentro de handler async** (`server.py:125` →
  `provider_clients.py:73,87`): bloquea el loop durante todo el round-trip (hasta 30 s) + reintentos.
  → *Fix:* `httpx.AsyncClient` con `asyncio.sleep`, o `asyncio.to_thread`.

### Altos

- **`StreamChat` no streamea** (proto `:15` dice `stream`, pero `server.py:57-76` espera la respuesta
  completa y hace un único `yield`). El *time-to-first-token* = tiempo total de generación → mala UX.
  → *Fix:* `astream`/`astream_events` y `yield` incremental.
- **Qdrant/embeddings síncronos en métodos `async`** (`qdrant_adapter.py:62-97` sin un solo `await`
  real): "async cosmético" que bloquea el loop con I/O de red síncrona. → *Fix:* `AsyncQdrantClient` +
  `aembed_query`.
- **Embeddings duplicados / sin caché** (el input se embebe en `search` y de nuevo en `store`; 4
  round-trips de red por turno, todos seriales). → *Fix:* cachear embeddings (LRU/Redis), reutilizar el
  vector del input.
- **Historial/audio en memoria** (`in_memory_history_adapter.py:8`): **fuga de memoria** (crece sin TTL),
  **no multi-instancia** (cada réplica su propio historial), se pierde en cada reinicio; además
  `chat.py` envía **todo** el historial al LLM (coste de tokens creciente). → *Fix:* `HistoryPort` con
  Redis (TTL) + ventana de contexto (últimos N mensajes).
- **Desajuste de dimensión de embeddings 768 vs 3072** (`config.py:34` modelo de 768 dims vs
  `qdrant_adapter.py:45` exige 3072): con los defaults, **la memoria semántica nunca funciona** (error de
  Qdrant silenciado por el swallow). → *Fix:* derivar la dimensión del modelo o alinear el modelo
  configurado.

### Medios

- Whisper carga **eager** en el arranque (cold start + footprint permanente), inconsistente con el lazy
  de Qdrant. → *Fix:* lazy o warming en background.
- `MAX_STT_CONCURRENCY=1` serializa el STT. → *Fix:* subir tras corregir el bloqueo del loop.
- Sin cliente HTTP async compartido / pooling. → *Fix:* `httpx.AsyncClient` con límites de pool.

---

## 11. Calidad de código y buenas prácticas no aplicadas

- **🐞 Bug de `store_memory`** (`nodes.py:58-79`): código duplicado/muerto, escribe antes del guard
  `memory_enabled` y fuera del `try/except` (ver §5.3). *Es el fix de mayor prioridad.*
- **`print()` en vez de logging** (`server.py:138`, `main.py:27`).
- **Sin shutdown elegante de gRPC** (`server.py:133-140`: no llama `server.stop(grace=…)`); **sin health
  checking gRPC ni reflection** (no se puede sondear ni depurar con `grpcurl`).
- **`except Exception` demasiado amplio** (mapea todo a `INTERNAL`, ocultando `DomainValidationError` que
  debería ser `INVALID_ARGUMENT`); `qdrant_adapter.py:49` silencia errores de conexión.
- **Type hints faltantes** (`server.py:18` `container` sin tipo; uso de `getattr` por contrato no tipado).
- **Dependencias duplicadas/desincronizadas** (`langgraph` x2; gRPC/LangChain ausentes en
  `pyproject.toml`) y **números mágicos** (3072, 0.7, rangos).
- **Router `/chat` siempre 500** (no replica el mapeo de errores del router de voz).
- **Pydantic v1/v2 mezclado** (`config.py:3-7,43`: `class Config` + `Field(env=…)` estilo v1).
- **Parámetro `format` de STT ignorado**; `sample_rate`/`channels` siempre `None`.
- **Test gRPC desincronizado** (`test_grpc_connection.py:60` espera un literal que el código ya no
  produce; el fake no define `execute_command_use_case`).
- **Huecos de cobertura**: sin tests de `nodes.py` (el bug), `qdrant_adapter`, adaptadores Gemini,
  handlers gRPC reales, reintentos de Kokoro; tests async con `asyncio.run` en vez de `pytest-asyncio`.
- **Archivos/campos muertos**: `bge_m3_adapter.py` vacío, `in_memory_audio_storage` sin uso,
  `MessageRequest.chat_id` ignorado.
- **Java**: paquete inválido (`com.atom.app.app` vs carpeta `com/atom/app`), `group` con mayúscula, sin
  `-web`/`actuator`, `.github/workflow` en singular (CI no corre).

---

## 12. Herramientas recomendadas para optimizar

| Área | Herramienta | Para qué |
|---|---|---|
| **Async correcto** | `asyncio.to_thread`/`run_in_executor`, `httpx.AsyncClient`, `AsyncQdrantClient`, `aembed_query`, `astream` | Desbloquear el event loop (STT/TTS/Qdrant) y habilitar streaming real |
| **gRPC robusto** | `grpcio-health-checking`, `grpcio-reflection`, interceptores `grpc.aio` | Health probes, depuración con `grpcurl`, auth/logging/métricas centralizados |
| **Caché / estado** | **Redis** (`redis.asyncio`) | `HistoryPort` con TTL (multi-instancia), caché de embeddings, idempotencia |
| **Observabilidad** | **OpenTelemetry** (traces), **Prometheus** (`prometheus-fastapi-instrumentator`), **structlog** | Ver el span por turno, latencias P50/P95/P99, logging estructurado |
| **Calidad Python** | **Ruff** (lint+format), **mypy**/pyright, **pre-commit** (+ detect-secrets) | Lint, tipos, hooks pre-commit (hoy inexistentes) |
| **Calidad Java** | **Spotless** + google-java-format, **Checkstyle**, **SpotBugs/Error Prone** | Formato y análisis estático |
| **CI/CD** | **GitHub Actions** (ruff+mypy+pytest --cov / `gradlew build test`) | Pipeline de calidad; corregir `.github/workflows/` (plural) |
| **Carga / profiling** | **k6**/**ghz** (gRPC), **Locust**, **py-spy**, **Scalene**, `PYTHONASYNCIODEBUG=1` | Validar el fix del loop bajo carga; localizar cuellos de botella |
| **Seguridad / deps** | **pip-audit**/Safety, **OWASP Dependency-Check**, **Dependabot/Renovate**, **gitleaks**, **pip-tools** | Escaneo de vulnerabilidades, pins, lockfiles |
| **Docker** | Multi-stage, `HEALTHCHECK`, pre-descarga del modelo Whisper, exponer `:50051` | Imágenes reproducibles y arranque sin cold start |

---

## 13. Plan de acción priorizado

**Corrección inmediata (bugs que rompen funcionalidad)**
1. **Arreglar `store_memory`** (`nodes.py`) — eliminar la doble escritura y el store previo al guard.
2. **Alinear la dimensión de embeddings** (768 vs 3072) — o la memoria semántica nunca funcionará.

**Rendimiento (desbloquear el event loop)**
3. Offload de STT/TTS a hilos (`asyncio.to_thread`) y migrar Kokoro/Qdrant/embeddings a clientes **async**.
4. **Streaming real** en `StreamChat` con `astream`.
5. **Persistencia de historial** en Redis con TTL + ventana de contexto.

**Seguridad (antes de cualquier despliegue real)**
6. **TLS + autenticación** en gRPC y HTTP; derivar `user_id` del token; **filtrar memoria por usuario**.
7. **Validar la salida del LLM** contra el catálogo e **imponer `requires_confirmation`** en servidor.
8. No filtrar excepciones; rate limiting; límites de payload; endurecer contenedor; no exponer Qdrant/Kokoro.

**Calidad / tooling**
9. Ruff + mypy + pre-commit + CI (Python) y Spotless + Checkstyle (Java); fijar y unificar dependencias;
   añadir health/reflection y shutdown elegante a gRPC; observabilidad (OTel/Prometheus).

**Integración (lado Java)**
10. Implementar el cliente gRPC en `Atom-app`: añadir el `.proto`, el plugin protobuf de Gradle y las
    dependencias gRPC; generar stubs; crear el `ManagedChannel`; corregir nombres de paquete/grupo y la
    ruta del workflow de CI.

---

> **Conclusión.** Atom es un asistente Android con una **arquitectura hexagonal limpia y bien pensada** en
> el lado Python (degradación elegante, contrato de acciones extensible, separación de capas ejemplar),
> pero hoy con **tres frentes abiertos**: (1) defectos de concurrencia que anulan el async, (2) ausencia
> total de seguridad de red, y (3) un lado Java aún sin construir. El cerebro (Atom-agent) está maduro a
> nivel de diseño; la integración y el endurecimiento son el trabajo pendiente.
