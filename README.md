# Atom Agent - AI Conversational System (v0.2.0)

Atom Agent is a high-performance conversational intelligence layer designed for mobile integration (Android). It features a hexagonal architecture to support modularity and easy scaling of its conversational, memory, and voice capabilities.

## 🚀 Features

- **Conversational Intelligence:** Powered by **Google Gemini 1.5 Flash**.
- **Orchestration:** Complex flows managed by **LangGraph**.
- **Semantic Memory:** **Qdrant** integration with **Gemini text-embedding-004** (768 dimensions).
- **Voice Capabilities:**
  - **STT:** Faster Whisper for high-accuracy speech-to-text.
  - **TTS:** Kokoro for premium, natural-sounding synthesis (default voice: `af_heart`).
- **Hexagonal Architecture:** Decoupled domain logic from infrastructure (LLMs, Vector Stores, Voice Engines).

## 📂 Structure

- `api/`: FastAPI controllers, schemas, and error handling.
- `application/`:
  - `agents/`: LangGraph workflow definition (graph, nodes, state).
  - `use_cases/`: Core logic orchestration (Chat, Transcribe, Synthesize).
- `domain/`: Pure business entities (Models, Value Objects, Errors).
- `ports/`: Abstract interfaces for all external dependencies.
- `adapters/`: Concrete implementations (LLM, Embeddings, VectorStore, Speech, History).
- `infrastructure/`: Configuration, Dependency Injection (Container), Logging, and Clients.

## 🛠️ Requirements

- Python 3.10+
- Docker & Docker Compose
- Google API Key (for Gemini)

## ⬇️ Download Locally

Clone the repository and move into the project folder:

```bash
git clone https://github.com/The-Galactics/Atom-agent.git
cd Atom-agent
```

## ⚙️ Configuration

Create a `.env` file based on the following template:

```env
# Google Gemini
GOOGLE_API_KEY=your_google_key_here
LLM_MODEL=gemini-1.5-flash
EMBEDDING_MODEL=models/text-embedding-004

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=memory

# Voice
KOKORO_ENDPOINT=http://localhost:8880/v1/audio/speech
KOKORO_DEFAULT_VOICE=af_heart
FASTER_WHISPER_MODEL=small
```

## 🐳 Quick Start (with Docker Compose)

The easiest way to run the full stack (API + Qdrant + Kokoro):

```bash
docker-compose up --build -d
```

Check status:
```bash
docker-compose ps
```

## 🧪 Testing the Agent

### Chat Endpoint
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Hola Atom, mi nombre es Gemi.", "session_id": "user_001"}'
```

### Voice Endpoints
**Transcribe (STT):**
```bash
curl -X POST http://localhost:8000/voice/transcribe \
  -F "file=@audio.wav;type=audio/wav"
```

**Synthesize (TTS):**
```bash
curl -X POST http://localhost:8000/voice/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"Hola Gemi, ¿cómo puedo ayudarte?", "voice":"af_heart"}' \
  --output response.wav
```

## 📜 Android Integration
See `ANDROID_CONTRACT.md` for Java/OkHttp implementation details.
