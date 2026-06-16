# ROLE

Act as a Senior Software Architect and AI Systems Engineer.

Your task is NOT to redesign the project.

Your task is to perform a controlled migration from NVIDIA AI services to Google Gemini AI services while preserving the existing Hexagonal Architecture.

---

# CURRENT ARCHITECTURE

The project already implements:

* Hexagonal Architecture
* FastAPI
* LangGraph
* Qdrant
* Conversation Agent
* Memory Agent
* Faster-Whisper
* Kokoro

Current AI stack:

LLM:

* google/gemma-3n-e4b-it (NVIDIA API)

Embeddings:

* nv-embedqa-e5-v5

The system already contains:

* LLMPort
* EmbeddingPort
* NvidiaGemmaAdapter
* NvidiaEmbeddingAdapter
* QdrantAdapter
* Conversation Agent
* Memory Agent

The architecture is working.

Do NOT redesign components that are unrelated to the AI provider.

---

# MIGRATION GOAL

Replace NVIDIA services with Google Gemini services.

New stack:

LLM:

* Gemini API

Embeddings:

* Gemini Embedding API

Keep everything else unchanged.

---

# IMPORTANT CONSTRAINTS

Do NOT redesign:

* FastAPI
* LangGraph
* Qdrant
* Conversation Agent
* Memory Agent
* Hexagonal Architecture
* Voice Module
* Folder Structure
* Use Cases
* Domain Layer

Modify only the components affected by the provider change.

---

# TASKS

## 1. Migration Impact Analysis

Identify exactly which components must change.

Classify them as:

* Must Change
* Optional Changes
* No Changes Required

---

## 2. LLM Layer Migration

Replace:

* NvidiaGemmaAdapter

with:

* GeminiAdapter

Keep:

* LLMPort

unchanged if possible.

Design:

* GeminiAdapter
* Request Flow
* Response Flow
* Error Handling
* Retry Strategy

Explain the differences from NVIDIA integration.

---

## 3. Embedding Layer Migration

Replace:

* NvidiaEmbeddingAdapter
* nv-embedqa-e5-v5

with:

* Gemini Embedding API

Keep:

* EmbeddingPort

unchanged if possible.

Design:

* GeminiEmbeddingAdapter
* Embedding Workflow
* Error Handling

---

## 4. Qdrant Compatibility

Verify that no changes are required in:

* Qdrant collections
* payload structure
* retrieval workflow
* semantic search pipeline

If changes are required, explain them.

Otherwise keep everything unchanged.

---

## 5. LangGraph Compatibility

Verify whether:

* Conversation Agent
* Memory Agent
* State Model
* Graph Nodes

need modifications.

Minimize changes.

---

## 6. Configuration Changes

Design the new configuration.

Examples:

GOOGLE_API_KEY=
GEMINI_MODEL=
GEMINI_EMBEDDING_MODEL=

Explain environment variable management.

---

## 7. Dependency Changes

Identify:

* packages to remove
* packages to install

Provide migration commands.

---

## 8. Testing Impact

Explain:

* which tests remain valid
* which mocks must be updated
* which integration tests must be recreated

Keep testing strategy as stable as possible.

---

## 9. Migration Plan

Provide a step-by-step migration plan.

Goal:

Perform the migration with the minimum amount of code changes while preserving the existing architecture.

---

# OUTPUT REQUIREMENTS

Provide a migration-focused architecture document.

Do not redesign the project.

Do not propose alternative architectures.

Only modify the components affected by replacing NVIDIA services with Google Gemini services.
