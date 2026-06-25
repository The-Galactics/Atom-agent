# Reporte de pruebas — Atom Agent

> Rama: `feat/ai-web-and-date-access` · Commit base: `5ff3744`
> Fecha de ejecución: 2026-06-23 · Python 3.12.3 · pytest 9.1.1 · pytest-cov
> Foco: validar el flujo completo de la IA con la feature de **acceso a internet
> (Google Search grounding)** y **fecha actual inyectada**, más el cambio de
> modelo a `gemini-3.1-flash-lite`, y subir la cobertura de forma honesta.

---

## 0. Actualización — caché de acciones + fix de embeddings

> Rama: `feat/action-cache-and-embeddings` (base `develop`) · Fecha: 2026-06-25

Cambios de esta iteración:
- **Fix de embeddings (causa raíz):** el fallo era un **mismatch de dimensión**
  (`models/embedding-001`=768 vs `qdrant_vector_size`=3072). Se consolida el modelo a
  `models/gemini-embeddings-2` en los 3 sitios divergentes y `QdrantAdapter` ahora
  **auto-detecta la dimensión** del primer embedding (`qdrant_vector_size=0` ⇒ auto),
  eliminando esa clase de bug.
- **Caché de acciones (`CachingIntentRecognizer`):** decorador sobre `IntentRecognizerPort`.
  Cachea en Qdrant (colección `skills`) solo comandos de un disparo e independientes de
  pantalla (`open_app`/`set_alarm`/`set_timer`/`toggle_setting`) en el **primer paso ReAct**;
  un comando repetido se resuelve **sin llamar al LLM**. Multi-paso, dependientes de pantalla
  y sensibles → siempre al LLM. El orquestador ReAct no se tocó.
- **Memoria conversacional vectorial desactivada** (`memory_enabled=False`) e historial
  corto 50 → **20**.

Tests de esta iteración:

| Archivo | Tests | Cubre |
| --- | --- | --- |
| `test_caching_intent_recognizer.py` *(nuevo)* | 7 | hit en 1er paso sin LLM; miss delega+memoriza solo cacheables; no-cacheable/sensible no se memoriza; `history` salta la caché; hit obsoleto ignorado; fallo de store degrada |
| `test_container.py` *(ampliado)* | +3 | readiness `vector_store=disabled`/`skills=enabled`; recognizer envuelto en caché según `skills_enabled`; firma `_build_intent_use_case(settings, embedding_adapter)` |

Resultado: **`tests/unit` → 104 passed, 0 failed** (Docker `atom-agent-api:latest` + `pytest`,
`PYTHONPATH=/app`). El orquestador ReAct y la suite previa siguen en verde.

**Verificación viva PENDIENTE (bloqueada):** el `.env` con `GOOGLE_API_KEY` ya no está en el
repo, así que falta (a) confirmar que el id `models/gemini-embeddings-2` existe y su dimensión
real, y (b) el E2E (comando repetido → `cache_hit` sin LLM; colección `skills` poblada). Se
hará al restaurar `.env`.

---

## 1. Cómo reproducir

```bash
# entorno (las dependencias de voz son opcionales, ver §5)
python3 -m venv .venv && source .venv/bin/activate
pip install pydantic pydantic-settings requests python-multipart pytest pytest-cov \
            httpx anyio fastapi "uvicorn[standard]" grpcio==1.81.1 protobuf==6.33.6 \
            langchain langgraph langchain-google-genai langchain-community qdrant-client

# suite + cobertura (term)
PYTHONPATH=. pytest -q --cov --cov-report=term-missing

# cobertura navegable (HTML)
PYTHONPATH=. pytest -q --cov --cov-report=html:tests/coverage_html
# abrir tests/coverage_html/index.html
```

La configuración de cobertura vive en `pyproject.toml` (`[tool.coverage.run]` /
`[tool.coverage.report]`): se omiten `proto/*` (stubs generados), `tests/*` y los
`__init__.py`, y se excluyen del cómputo los cuerpos de métodos abstractos y las
guardas `if __name__ == "__main__"`. Por eso `--cov` solo, sin `=.`, ya aplica el
alcance correcto.

---

## 2. Resultado global

| Métrica | Valor |
| --- | --- |
| Tests ejecutados | **67** |
| Resultado | **67 passed, 0 failed** |
| Duración | ~6 s |
| Cobertura global de líneas | **74 %** (1075 sentencias medidas, 277 sin cubrir) |
| Tests añadidos en esta sesión | 42 |

Evolución de la cobertura en la sesión: 63 % (baseline) → 66 % (regresiones de la
feature) → 70 % (adapter de intents + contenedor) → 71 % (`GeminiAdapter`) →
**74 %** (heurística de memoria + nodos del grafo + degradación sin API key).

Distribución: 57 unit + 10 integración (FastAPI + gRPC sobre stubs y use cases falsos).

---

## 3. Inventario de pruebas

### Unitarias (`tests/unit/`)

| Archivo | Tests | Cubre |
| --- | --- | --- |
| `test_content.py` *(nuevo)* | 7 | `extract_text`: string plano, bloques Gemini 3.x, no-texto, **regresión `content==[]` → `""`** |
| `test_datetime_context.py` *(nuevo)* | 4 | `current_datetime_sentence`: fecha real, 24h + UTC-5, español, fallback de tz inválida |
| `test_intent_adapter.py` *(nuevo)* | 6 | `GeminiFunctionCallingAdapter` con SDK mockeado: tool-call→Action, acción sensible, fallback conversacional, tool desconocido, `ProviderError`, inyección de fecha |
| `test_gemini_adapter.py` *(nuevo)* | 5 | `GeminiAdapter`: mapeo de roles, **grounding con `google_search`**, **fallback ungrounded** ante fallo, modo sin grounding |
| `test_container.py` *(nuevo)* | 5 | `build_container`: cableado chat+intent, voz degradada, `shutdown` seguro, intent sin API key, **degradación completa sin `GOOGLE_API_KEY` (regresión §7.2)** |
| `test_nodes.py` *(nuevo)* | 7 | `GraphNodes`: retrieve (join / disabled / degradación), generate (fecha+contexto), store (disabled / trivial / persistencia en background) |
| `test_importance.py` *(nuevo)* | 7 | `is_memorable`: vacío, trivial, normalización de puntuación, marcadores de hecho, umbral de palabras |
| `test_intent.py` | 9 | Catálogo, contrato `openai_tools`, acciones sensibles, ruteo de `ExecuteCommandUseCase` |
| `test_use_cases.py` | 5 | Chat, transcribe y synthesize (con puertos falsos) |
| `test_domain_value_objects.py` | 3 | `AudioFormat`, `Language`, payload de audio |

### Integración (`tests/integration/`)

| Archivo | Tests | Cubre |
| --- | --- | --- |
| `test_grpc_connection.py` | 7 | Flujo gRPC completo + rutas de error (UNAVAILABLE / INTERNAL), incluido **chat no disponible** (LLM caído) |
| `test_api.py` | 3 | Endpoints HTTP de salud, transcribe y synthesize |

---

## 4. Cobertura por módulo (lo relevante)

| Módulo | Cobertura | Nota |
| --- | --- | --- |
| `adapters/llm/content.py` | **100 %** | helper corregido; regresión `"[]"` bloqueada |
| `adapters/llm/gemini_adapter.py` | **100 %** | grounding + fallback web cubiertos |
| `adapters/intent/gemini_function_calling_adapter.py` | **100 %** | SDK mockeado |
| `domain/datetime_context.py` | **100 %** | inyección de fecha |
| `domain/memory/importance.py` | **100 %** | heurística de memoria |
| `application/agents/nodes.py` | 96 % | solo el log de error de `_persist` (97-98) |
| `application/use_cases/chat.py` | 100 % | |
| `infrastructure/config.py` | 98 % | |
| `infrastructure/container.py` | 85 % | falta rama de construcción de voz habilitada |
| `infrastructure/grpc/server.py` | 82 % | |
| `application/use_cases/execute_command.py` | 88 % | falta rama de fallback a chat (36-39) |
| `domain/intent/catalog.py` | 97 % | |

### Módulos con cobertura baja/nula (ver §5)

`main.py` (0 %), `infrastructure/logging.py` (0 %), `infrastructure/provider_clients.py`
(39 %), `adapters/vector_store/qdrant_adapter.py` (41 %), `api/controllers.py` (53 %),
`adapters/speech/*` (35-45 %), `adapters/history/in_memory_history_adapter.py` (50 %).

---

## 5. Datos importantes / limitaciones

1. **Adaptadores de voz parcialmente cubiertos.** `faster_whisper` no está instalado;
   sus métodos no se ejecutan (solo el import), por eso `adapters/speech/*` queda al
   35-45 %. El contenedor degrada STT/TTS correctamente — verificado.
2. **Bootstrap/IO sin cubrir por diseño.** `main.py` (arranque uvicorn/gRPC) y
   `logging.py` (configuración) son entrypoints; `provider_clients.py` y
   `qdrant_adapter.py` requieren los servicios vivos (Kokoro, Qdrant). Se validaron
   **manualmente end-to-end** (ver §6). No se inflan con mocks artificiales.
3. **La suite NO consume red ni claves.** Todo corre con fakes/SDK mockeado y
   `_env_file=None` para aislarse del `.env` real, por eso es determinista.
4. **`tests/coverage_html/`** es artefacto regenerable; está en `.gitignore`.

---

## 6. Validación manual end-to-end de la feature (fuera de la suite automática)

Ejecutada contra **Gemini real** (`gemini-3.1-flash-lite`, `WEB_SEARCH_ENABLED=true`,
`ASSISTANT_TIMEZONE=America/Bogota`) el 2026-06-23:

| Aspecto | Resultado |
| --- | --- |
| Fecha inyectada | "¿qué día es hoy?" → **"martes 23 de junio de 2026"** (coincide con la fecha real) |
| Grounding web | Respuesta de actualidad **con URL de grounding** `vertexaisearch.../grounding-api-redirect/...` → el tool `google_search` disparó realmente |
| Comandos (function calling) | `OPEN_APP`, `MAKE_CALL` (con confirmación), `SET_ALARM` (07:00), `TOGGLE_SETTING` — todos `conf=1.0` |
| Fallback conversacional | Orden no-acción enrutada al chat con grounding + fecha |
| Degradación | STT (sin faster_whisper) y Qdrant (`localhost:6333` caído) degradan sin romper el turno |

---

## 7. Bugs encontrados durante las pruebas

1. **Corregido — `adapters/llm/content.py`:** devolvía el literal `"[]"` cuando Gemini
   respondía con un tool call (`content == []`), anulando el reply por defecto
   `"De acuerdo."` del camino de comandos. Corregido y blindado con
   `test_content.py::test_extract_text_empty_list_returns_empty_not_repr`.
2. **Corregido — `infrastructure/container.py`:** `build_container` construía
   `GeminiAdapter`/`GeminiEmbeddingAdapter` con `settings.google_api_key or ""`, y el SDK
   `ChatGoogleGenerativeAI`/`GoogleGenerativeAIEmbeddings` lanza `ValidationError` con clave
   vacía → **sin `GOOGLE_API_KEY` el arranque reventaba** en lugar de degradar. Solución:
   se extrajo la construcción a un helper defensivo `_build_llm_stack` (espejo de
   `_build_voice_adapters`/`_build_intent_use_case`); ahora `llm_adapter`, `vector_store`,
   `embedding_adapter` y `chat_use_case` son opcionales y quedan en `None` cuando falta la
   clave o el SDK falla. `readiness()` reporta `llm.status = "missing_key"`, y los
   consumidores degradan limpiamente: gRPC `StreamChat` → `UNAVAILABLE`, HTTP `POST /chat`
   → `503 CHAT_UNAVAILABLE`. Blindado con
   `test_container.py::test_build_container_degrades_without_api_key_instead_of_crashing` y
   `test_grpc_connection.py::test_grpc_stream_chat_unavailable_when_use_case_missing`.

---

## 8. Recomendaciones de siguientes pasos

- Cubrir la rama de fallback a chat en `ExecuteCommandUseCase` (36-39) con un `chat_use_case` falso.
- Tests de `provider_clients.py` (cliente Kokoro) con `requests` mockeado y de
  `qdrant_adapter.py` con un `QdrantClient` falso (dedup/TTL/upsert/search).
- Si la voz entra en alcance de CI: instalar `faster_whisper` y mockear Kokoro para cubrir
  `adapters/speech/*`.
- Test de integración opcional (marcado `@pytest.mark.live`, desactivado por defecto) que
  ejerza grounding + fecha contra Gemini real cuando haya `GOOGLE_API_KEY`.
