# ⚙️ Tareas Técnicas por Issue — Atom AI Assistant
**Versión:** 1.2.0  
**Proyecto:** Atom — Asistente de IA para Dispositivos Móviles  
**Stack:** Java 21 · Python 3.13 · TypeScript (Landing) · FastAPI · Gemma 4.0 · Room SQL · ChromaDB  
**Arquitectura:** Hexagonal (Domain – Application – Infrastructure) aplicada en Java, Python y TypeScript.

---

## 📐 Dependencias principales

- **Java 21**: Spring Boot 3.x, Retrofit, Room, JUnit 5, Mockito.
- **Python 3.13**: FastAPI, Pydantic, Google Generative AI (Gemma 4.0), ChromaDB, pytest.
- **TypeScript**: Vite + React, CSS Modules, ESLint, Jest.

---

# 🚀 FEAT-SETUP — Configuración del proyecto

## ISSUE-001 — Creación del repositorio y estructura base
**Asignado a:** `@dev1` | **Prioridad:** 🔴 Alta

### Tarea 1.1 — Inicializar monorepo con sub‑proyectos (`backend/`, `frontend/`, `mobile/`)
### Tarea 1.2 — Configurar gestores de paquetes (npm, pip, Maven)
### Tarea 1.3 — CI básico con GitHub Actions (build, test)

---

# 🌐 FEAT-LANDING — Landing Page (TypeScript)

## ISSUE-002 — Botón de descarga funcional
**Asignado a:** `@dev1` | **Prioridad:** Alta

### Tarea 2.1 — Diseño del botón CTA
- Color Lavanda (`#B794F4`), efecto hover, accesibilidad ARIA.
### Tarea 2.2 — Implementación de lógica de descarga
- En `src/infrastructure/adapters/out/static-data/DownloadAdapter.ts` crear método `downloadApk(): Promise<void>` que redirija a `assets/atom.apk`.
### Tarea 2.3 — Tests unitarios (Jest) y pruebas de integración (Cypress).

---

# 🏛️ FEAT-CORE — Arquitectura Hexagonal Java (Android)

## ISSUE-007 — Entidades + Puertos hexagonales (Domain Layer)
**Asignado a:** `@dev2` | **Prioridad:** Crítica

### Tarea 7.1 — Modelos puros (`User.java`, `Intent.java`, `Action.java`)
### Tarea 7.2 — Puertos de Entrada (`ProcessVoiceCommandUseCase.java`)
### Tarea 7.3 — Puertos de Salida (`UserRepository.java`, `AIServicePort.java`)

## ISSUE-008 — Persistencia y Seguridad (Infrastructure Layer)
**Asignado a:** `@dev2` | **Prioridad:** Alta

### Tarea 8.1 — Adaptador Room (`RoomUserRepository.java`)
### Tarea 8.2 — Cifrado AES‑256‑GCM (`CryptoUtil.java`)
### Tarea 8.3 — Tests de integración (JUnit + Robolectric)

---

# 🤖 FEAT-AI — Backend Python (FastAPI)

## ISSUE-006 — Orquestador de NLP con Gemma 4.0
**Asignado a:** `@dev3` | **Prioridad:** Alta

### Tarea 6.1 — Definir dominio y puertos (`Intent.py`, `NLPUseCase.py`, `AIModelPort.py`)
### Tarea 6.2 — Adaptador Gemma (`gemma_adapter.py`)
### Tarea 6.3 — Vector DB ChromaDB (MemoryService)
- **Nuevo sub‑issue:** `ISSUE-010` – Implementar `MemoryService` con ChromaDB.
### Tarea 6.4 — API FastAPI (`/nlp`, `/health`)

---

# 🎤 FEAT-AUDIO — Captura y STT

## ISSUE-009 — Captura de audio y transcripción
**Asignado a:** `@dev3` | **Prioridad:** Alta

### Tarea 9.1 — Adaptador Android (`AudioRecorderAdapter.java`)
### Tarea 9.2 — Servicio STT en Python (`stt_service.py` usando Whisper o Google Speech‑to‑Text)

---

# 🔐 FEAT-AUTH — Autenticación con Google Auth

## ISSUE-011 — Integrar Google Sign‑In (OAuth 2.0)
**Asignado a:** `@dev4` | **Prioridad:** Alta

### Tarea 11.1 — Configurar proyecto Google Cloud y obtener `client_id`.
### Tarea 11.2 — Implementar flujo Android (`GoogleSignInClient`), backend (`/auth/google` endpoint) y unión al dominio (`UserRepository`).
### Tarea 11.3 — Guardar token JWT en SecureStorage y validar en cada request.
### Tarea 11.4 — Tests de autenticación (Mockito, pytest‑asyncio).

---

# 📚 FEAT-DOCUMENTACIÓN — Casos de prueba Gherkin

## ISSUE‑010 — Generar suite de pruebas Gherkin
**Asignado a:** `@dev1` | **Prioridad:** Media

### Tarea 10.1 — Mapear cada ISSUE a CP‑ATOM‑XXX (actualizado)
- **CP‑ATOM-001…010** (existentes).
- **CP‑ATOM-011** – *Perfil de usuario*:
  ```gherkin
  Feature: Visualizar y editar perfil de usuario
    Scenario: Usuario visualiza su perfil completo
      Given el usuario está autenticado con Google Auth
      When solicita la vista de perfil
      Then se muestra nombre, avatar y preferencias
  ```
- **CP‑ATOM-012** – *Bridge Java↔Python*:
  ```gherkin
  Feature: Comunicación entre Android y backend AI
    Scenario: Android envía comando y recibe respuesta
      Given el dispositivo Android está conectado al backend
      When envía texto "Abrir calendario"
      Then recibe intención "OPEN_CALENDAR" y datos JSON válidos
  ```
- **CP‑ATOM-013** – *Gestión de sesión (session_id)*:
  ```gherkin
  Feature: Mantener sesión entre turnos
    Scenario: Conversación continua con session_id
      Given el usuario inicia una conversación
      When envía segunda petición sin nuevo token
      Then el backend reutiliza el mismo `session_id` y mantiene contexto
  ```

---

# 📋 Resumen de tareas por developer

| Developer | Issues asignados | Nº de tareas | Comentario |
|-----------|------------------|--------------|-----------|
| `@dev1` | ISSUE‑001, ISSUE‑002, ISSUE‑010 | 7 | Setup, Landing, Gherkin, botón descarga |
| `@dev2` | ISSUE‑007, ISSUE‑008 | 6 | Core Java hexagonal, persistencia, seguridad |
| `@dev3` | ISSUE‑006, ISSUE‑009 | 8 | Backend AI, ChromaDB MemoryService, STT |
| `@dev4` | ISSUE‑011 | 4 | Google Auth integración |

---

*Este documento ahora unifica la numeración de issues entre `issues.md` y `Tareas‑issues‑Atom.md`, agrega las tareas técnicas que faltaban (botón de descarga, MemoryService, Google Auth) y completa los escenarios Gherkin pendientes.*
