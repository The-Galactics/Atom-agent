# ROLE

Act as a Senior Software Architect and AI Systems Engineer specialized in:

- Hexagonal Architecture
- FastAPI
- LangGraph
- Qdrant
- Conversational AI
- Multi-Agent Systems
- Production AI Applications
- Clean Architecture
- SOLID Principles

Your goal is to design Sprint 2 of an Android AI Assistant project.

The output must be practical, implementation-oriented, and suitable for a real development team.

---

# PROJECT CONTEXT

We are building an Android AI Assistant similar to Gemini Live.

Current stack:

- STT: Faster-Whisper
- TTS: Kokoro
- LLM: google/gemma-3n-e4b-it (NVIDIA API)
- Vector Database: Qdrant
- Backend: FastAPI
- Mobile: Java Android
- Architecture: Hexagonal Architecture
- Agent Framework: LangGraph

Sprint 1 has already been completed.

Implemented:

Audio
→ Faster Whisper
→ Text
→ LLM
→ Text
→ Kokoro
→ Audio

The Voice Module is already working and must not be redesigned.

---

# SPRINT 2 GOAL

Build the conversational intelligence layer.

Focus only on:

- Gemma integration
- Conversation management
- Semantic memory
- Qdrant integration
- LangGraph workflow
- Agent foundation

Do NOT design:

- PostgreSQL
- Android automation
- Accessibility Service
- Tool execution
- Habit prediction
- Device control

Those belong to future sprints.

---

# REQUIREMENTS

The architecture must:

- Follow Hexagonal Architecture
- Follow SOLID principles
- Be maintainable
- Be scalable
- Be easy to test
- Support future tool execution
- Support future memory expansion
- Support future agent growth

Avoid overengineering.

---

# TASKS

## 1. High-Level Architecture

Design the complete Sprint 2 architecture.

Include:

- Android Client
- Voice Module
- FastAPI
- LangGraph
- Conversation Layer
- Memory Layer
- Qdrant
- NVIDIA API

Explain responsibilities and interactions.

---

## 2. Project Structure

Design a professional folder structure.

Include:

- domain
- application
- ports
- adapters
- agents
- memory
- conversation
- infrastructure

Explain the responsibility of each folder.

---

## 3. Hexagonal Architecture Design

Define:

- Domain Layer
- Application Layer
- Ports
- Adapters

Explain allowed dependencies and boundaries.

---

## 4. Agent Design

Design only the agents required for Sprint 2.

Maximum two agents:

### Conversation Agent

Responsibilities:
- user interaction
- context management
- response generation

### Memory Agent

Responsibilities:
- memory storage
- memory retrieval
- memory ranking

For each agent provide:

- responsibilities
- inputs
- outputs
- state management

---

## 5. LangGraph Design

Design the workflow.

Include:

- State definition
- Nodes
- Edges
- Execution flow
- Error handling

Keep the graph simple and suitable for Sprint 2.

---

## 6. Conversation Management

Design:

- session context
- short-term memory
- conversation history
- context window strategy

Explain how context should be prepared before sending requests to Gemma.

---

## 7. Semantic Memory Design

Design a memory system using Qdrant.

Include:

- memory structure
- metadata
- embedding workflow
- retrieval workflow
- memory update strategy

Provide examples.

---

## 8. Qdrant Integration

Design:

- collections
- payload structure
- metadata schema
- similarity search workflow

Keep the design simple and production-ready.

---

## 9. LLM Integration Layer

Design:

- LLMPort
- NvidiaGemmaAdapter
- PromptBuilder
- ContextAssembler

Explain responsibilities and interactions.

---

## 10. API Design

Design only the necessary endpoints.

Examples:

POST /chat

POST /memory/store

POST /memory/search

Include request and response examples.

---

## 11. Sequence Diagrams

Create sequence diagrams for:

User
→ Voice Module
→ Conversation Agent
→ Memory Agent
→ Gemma
→ Response

and

User
→ Memory Storage
→ Qdrant

---

## 12. Testing Strategy

Design:

- Unit Tests
- Integration Tests
- Mock LLM
- Mock Qdrant

Explain how to test the system without external dependencies.

---

## 13. Sprint Backlog

Organize tasks as:

P0 (Required)

P1 (Important)

P2 (Optional)

Include:

- effort estimation
- dependencies
- deliverables

---

## 14. Definition of Done

Define exactly when Sprint 2 is complete.

Include:

- working conversations
- semantic memory
- Gemma integration
- LangGraph workflow
- testing requirements

---

# OUTPUT REQUIREMENTS

Provide a practical architecture document.

Focus on implementation.

Avoid theoretical explanations.

Design a solution that can be directly implemented by a development team.