# gRPC Connection Test & Integration Guide

This document explains how to run the Atom Agent gRPC server, how to test the
connection used by the Android client, the contract that binds the two repos,
and the known gaps left as future work.

It is the gRPC counterpart to `ANDROID_CONTRACT.md` (which covers the REST voice
endpoints). The Android-side mirror of this document lives in the app repo under
`docs/eng/technical/tests/gRPC/ATOM-31-grpc-connection-test.md` (Spanish mirror
under `docs/es/tecnico/pruebas/gRPC/`).

## 📜 The Contract

The gRPC contract is defined in `proto/atom_agent.proto` and is the **source of
truth**. The Android client mirrors it at `Atom_app/src/main/proto/ai.proto`.

- `package com.atom.proto`
- Service `AtomAgentService` with four RPCs:

| RPC | Kind | Purpose | Backend state |
|:----|:-----|:--------|:--------------|
| `ExecuteCommand` | unary | Run a device command | Placeholder — returns a canned acknowledgement |
| `StreamChat` | server-streaming | Conversational AI, token by token | Wired to `chat_use_case` (LangGraph + NVIDIA Gemma) |
| `Transcribe` | unary | Speech-to-text | Wired to `transcribe_use_case` (Faster Whisper) |
| `Synthesize` | server-streaming | Text-to-speech | Wired to `synthesize_use_case` (Kokoro) |

The two proto files were compared field by field and are **in sync** (same
service, RPCs, message fields, and tag numbers). The only differences are
explanatory comments on the Android side.

## 🚀 Running the gRPC server

The gRPC server starts automatically as a background task inside the FastAPI app
(`main.py` → `startup_event` → `infrastructure/grpc/server.py::serve`). It listens
on **port `50051`** with an **insecure (plaintext)** port — matching the Android
client's dev transport (`usePlaintext()`).

```bash
# 1) activate the virtualenv
source .venv/bin/activate

# 2) (optional) provide provider keys for the live AI path
cp .env.example .env   # then set NVIDIA_API_KEY, QDRANT_URL, KOKORO_ENDPOINT, ...

# 3) run the app (FastAPI on :8000, gRPC on :50051)
uvicorn main:app --host 0.0.0.0 --port 8000
```

Without `NVIDIA_API_KEY` / a reachable Qdrant, `ExecuteCommand` still works
(it has no external dependency), but `StreamChat` will fail when it reaches the
LLM.

## 🧪 Testing the connection (no API keys required)

A self-contained end-to-end test starts the **real** `AtomGrpcService` on a
loopback port and drives it with the generated stubs over an insecure channel.
It injects a stub container with a fake `chat_use_case`, so `StreamChat` runs
without any provider keys.

```bash
PYTHONPATH=. .venv/bin/python tests/integration/test_grpc_connection.py
```

Expected output:

```text
[server] AtomAgentService started on insecure port 33451
[ExecuteCommand] success=True out_message='Agent acknowledged command: open camera'
[StreamChat] token='Echo: Hello Atom, can you help me?' status='success' finished=True

RESULT: PASS
```

> The test is a plain `asyncio` runner rather than a `pytest.mark.asyncio` test
> because the project does not yet depend on `pytest-asyncio`. The rest of the
> suite (`pytest -q`, 11 tests) is unaffected and stays green.

### Testing the live AI path

To validate `StreamChat` against the real LangGraph/NVIDIA Gemma pipeline:

1. Set `NVIDIA_API_KEY` and a reachable `QDRANT_URL` in `.env`.
2. Start the server (`uvicorn main:app ...`).
3. Point a gRPC client (or the Android app) at `host:50051` and call `StreamChat`.

## ⚠️ Known gaps / future work

- **Live AI not yet covered by an automated test** — needs `NVIDIA_API_KEY` and a
  Qdrant instance in CI.
- **`Transcribe` / `Synthesize` connection tests** — defined in the contract but
  not yet exercised over gRPC; add once Faster Whisper / Kokoro are reliably
  available.
- **`ExecuteCommand` is a placeholder** — returns a fixed acknowledgement; real
  command execution is pending.
- **No TLS** — the server uses an insecure port (dev only). Add TLS before any
  non-local deployment.
- **No auth/identity** — the Android client sends a random per-session `user_id`
  (see app ADR-001); real identity is deferred to the auth milestone.
