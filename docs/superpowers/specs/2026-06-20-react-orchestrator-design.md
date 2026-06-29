# Step-wise ReAct orchestrator for `ExecuteCommand`

Date: 2026-06-20
Repo: Atom-agent (branch `feature/function-calling`)
Status: Approved — pending implementation

## Goal

Turn the single-shot `ExecuteCommandUseCase` into a step-wise ReAct orchestrator
that drives a high-level command (e.g. "Open YouTube and search for a Rubius
video") to completion: one action per gRPC call, informed by the live screen and
the accumulated action history, terminating with an explicit `task_complete`
signal.

## Architecture decision

The orchestration loop is **distributed across gRPC calls**. Each `ExecuteCommand`
call is exactly **one ReAct step**: Reason over `screen_elements` + action history,
then Act by emitting one tool/action. The Android client closes the loop —
execute the action, recapture the screen, call again with the same `session_id`
until the backend returns `task_complete=true` or a step cap trips.

There is intentionally **no in-call `while`-loop over screen-changing actions**.
The backend cannot observe a fresh screen mid-call (the device owns screen state
and sends one snapshot per unary call), so a server-side loop would re-reason over
a stale snapshot — the exact repeat/infinite-loop failure we must avoid. The
guarded loop is therefore the cross-call state machine plus boundary checks.

Model id: `gemini-3.1-flash`.

## Components (approach A — refactor in place + history-aware recognizer)

1. **Contract** — add to `CommandResponse` in `proto/atom_agent.proto`:
   - `bool task_complete = 7;` — client stops looping when true.
   - `int32 step = 8;` — current step index (telemetry/debug).
   Regenerate `atom_agent_pb2.py` / `atom_agent_pb2_grpc.py`. Mirror the same two
   fields into `Atom_app/src/main/proto/ai.proto` for contract parity (proto edit
   only; the Android app is not built here).

2. **Session store** — new bounded in-memory store keyed by `session_id`, holding
   an ordered action trace (e.g. `Step 1: OPEN_APP {app_name: youtube}`). Per-session
   step cap + max-sessions/TTL eviction. Pure, injectable, trivially mockable.
   Methods: `get`, `append`, `reset`.

3. **Orchestrator** (`application/use_cases/execute_command.py`):
   - Load prior steps for `session_id`.
   - Call the recognizer with `text` + `screen_elements` + `history`.
   - Anti-repeat: an action identical to the previous step ⇒ stop (mark complete).
   - Boundary: enforce `max_steps` cap ⇒ forced `task_complete` with a graceful reply.
   - Completion: model signals done via `ActionType.NONE` + reply after ≥1 action,
     or the cap is reached.
   - Record the chosen step; reset the session on completion.
   - Return `ExecuteCommandOutputDTO` extended with `task_complete` and `step`.

4. **Recognizer + Gemini adapter** — extend
   `IntentRecognizerPort.recognize(text, session_id="default", screen=None, history=None)`.
   The adapter renders the action trace into the message list so the evolving
   context feeds Gemini's history and the model emits the *next* single action or
   signals completion. `history=None` preserves current behavior (back-compat).

5. **Wiring** — instantiate/inject the session store and `max_steps` config in
   `infrastructure/container.py` (+ `infrastructure/config.py`).

6. **gRPC/API mapping** — map `task_complete`/`step` from the output DTO into
   `CommandResponse` (`infrastructure/grpc/server.py`, `api/controllers.py`,
   `api/schemas.py`). Incoming `screen_elements` continue to flow through.

## Data flow ("Open YouTube and search for a Rubius video")

- Call 1: screen=home, history empty ⇒ OPEN_APP youtube. Store Step 1. `task_complete=false`.
- Call 2: screen=YouTube home, history=[Step 1] ⇒ TAP_ELEMENT search. Store Step 2.
- Call 3+: screen evolves ⇒ TAP/TYPE search, scroll, etc.
- Final: model judges goal met ⇒ NONE + reply ⇒ `task_complete=true`, session reset.
- Boundary: step count reaches `max_steps` ⇒ forced `task_complete=true` + graceful message.

## Error handling / boundaries

- `max_steps` cap ⇒ forced completion (no infinite loop).
- Identical-action-repeat ⇒ stop.
- `ProviderError` from Gemini propagates as today (`success=false`).
- Empty screen is valid (model may OPEN_APP first).
- Session store bounded (per-session cap + max-sessions/TTL) ⇒ no memory growth.

## Testing

- Keep the existing 11 unit tests green (new fields/params default to current behavior).
- New unit tests, mocking the recognizer/LLM:
  - `screen_elements` + history injection updates the model's message context.
  - Multi-step chaining (OPEN_APP → TAP_ELEMENT → completion) across repeated
    `execute()` calls with evolving screen: assert step accumulation, repeat
    suppression, and `task_complete` flipping true at the end.
  - Boundary cases: `max_steps` cap and identical-action repeat.
  - Session-store units (append/get/reset/eviction/cap).
- Trim verbose/placeholder comments in touched files.

## Constraints

- **No git commits anywhere.** Leave Atom-agent (impl + regenerated stubs + proto)
  and Atom_app (`ai.proto` mirror) modified in the working tree for review.
