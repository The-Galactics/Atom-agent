# Intent & Actions Contract — Function Calling (Sprint 3)

This contract defines how the Android client turns a **user order** (voice or
text) into an **executable action**. The backend uses LLM **function calling**
(Google Gemini) to interpret the order and returns a structured action the app
runs on-device.

It complements `ANDROID_CONTRACT.md` (STT/TTS voice module) and
`GRPC_CONNECTION_TEST.md` (gRPC transport).

## End-to-end flow

```text
User speaks/types an order
  → (voice only) POST /voice/transcribe  → text
  → gRPC ExecuteCommand(user_id, command=text)
  → Backend: Gemini function calling → structured Action
  → CommandResponse(action_type, parameters_json, out_message, ...)
  → Android: ActionRouter dispatches to the matching handler
  → (optional) POST /voice/synthesize(out_message) → spoken confirmation
```

Conversation vs. order is decided by the model: if the message maps to a
catalog action it returns a tool call (`action_type != "NONE"`); otherwise it
replies conversationally (`action_type == "NONE"`, speak `out_message`).

## Transport: gRPC `ExecuteCommand`

Service `AtomAgentService` in `proto/atom_agent.proto`:

```proto
rpc ExecuteCommand (CommandRequest) returns (CommandResponse);

message CommandRequest {
  string user_id = 1;                       // DEPRECATED: identity comes from the access token
  string command = 2;                       // the user's natural-language order (text)
  repeated ScreenElement screen_elements = 3; // structured screen map (accessibility)
  string order_id = 4;                      // stable id for all turns of one task; new id => fresh trace
}

message ScreenElement {
  string text = 1;
  string role = 2;        // short widget class, e.g. Button/EditText/TextView
  bool   clickable = 3;
  bool   focusable = 4;
  bool   editable = 5;
  bool   scrollable = 6;
  int32  index = 7;       // stable ordinal
}

message CommandResponse {
  bool   success = 1;
  string out_message = 2;            // reply to speak / show (TTS-ready)
  string action_type = 3;           // e.g. "OPEN_APP", "NONE"
  string parameters_json = 4;       // JSON object of slots
  float  confidence = 5;            // 1.0 for actions, 0.0 for conversation
  bool   requires_confirmation = 6; // confirm before executing if true
}
```

> **Regenerate stubs after pulling this change** (both repos):
> ```bash
> # Backend (Python)
> python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. --pyi_out=. proto/atom_agent.proto
> # Android: rebuild — the protobuf-gradle plugin regenerates Java stubs from the shared .proto
> ```

### `screen_elements` — the structured screen map

When accessibility is enabled, the Android client attaches a snapshot of the
currently visible UI as `CommandRequest.screen_elements` (repeated
`ScreenElement`, field 3). The backend renders these into the model's context so
Gemini can reason over real screen structure and drive `read_screen` /
`tap_element` against actual targets instead of claiming it cannot see the screen.

| Field | Type | Meaning |
|---|---|---|
| `text` | string | Visible text of the element. |
| `role` | string | Short widget class, e.g. `Button`, `EditText`, `TextView`. |
| `clickable` | bool | Element responds to taps. |
| `focusable` | bool | Element can receive focus. |
| `editable` | bool | Element accepts text input. |
| `scrollable` | bool | Element can be scrolled. |
| `index` | int32 | Stable ordinal used to disambiguate targets. |

The field is optional: an empty list is valid and the model simply has no screen
context for that turn.

### gRPC status codes

| Status | Meaning |
|---|---|
| `OK` | Order interpreted (may be an action or a conversational reply). |
| `UNAVAILABLE` | Intent provider not ready (no `GOOGLE_API_KEY` / lib missing). |
| `INTERNAL` | Unexpected failure interpreting the order. |

## Action catalog

`action_type` is one of the values below (single source of truth:
`domain/intent/catalog.py`). `parameters_json` is a JSON object with the listed
slots.

| `action_type` | Slots (`parameters_json`) | Confirm? | Example utterance | Android API to fulfill |
|---|---|:--:|---|---|
| `OPEN_APP` | `app_name` (string) | no | "abre WhatsApp" | Launch intent via `PackageManager.getLaunchIntentForPackage` (resolve label→package) |
| `MAKE_CALL` | `target` (string: contact or number) | **yes** | "llama a mamá" | `Intent.ACTION_CALL` (perm `CALL_PHONE`) after contact lookup |
| `SEND_MESSAGE` | `recipient` (string), `body` (string), `app` (string, optional) | **yes** | "envía 'voy tarde' a Ana" | SMS `SmsManager` / messaging app deep link |
| `SET_ALARM` | `time` (string `HH:MM`), `label` (string, optional) | no | "pon una alarma a las 7:30" | `AlarmClock.ACTION_SET_ALARM` |
| `SET_TIMER` | `duration_seconds` (integer), `label` (string, optional) | no | "temporizador de 5 minutos" | `AlarmClock.ACTION_SET_TIMER` |
| `TOGGLE_SETTING` | `setting` (`wifi`\|`bluetooth`\|`flashlight`\|`do_not_disturb`), `state` (`on`\|`off`\|`toggle`) | no | "enciende la linterna" | `CameraManager.setTorchMode`, Quick Settings tile, or AccessibilityService |
| `NAVIGATE` | `direction` (`back`\|`home`\|`recents`\|`quick_settings`) | no | "ve atrás" | `AccessibilityService.performGlobalAction` |
| `SCROLL` | `direction` (`up`\|`down`\|`left`\|`right`) | no | "baja la pantalla" | `AccessibilityService` node `ACTION_SCROLL_*` / `dispatchGesture` |
| `READ_SCREEN` | `{}` | no | "¿qué hay en la pantalla?" | `AccessibilityService` walks the active window; text returned in `out_message` |
| `TAP_ELEMENT` | `text` (string: visible label) | **yes** | "toca Ajustes" | `AccessibilityService` `findAccessibilityNodeInfosByText` + `ACTION_CLICK` |
| `NONE` | `{}` | no | "¿qué tiempo hace?" | No action — speak `out_message` |

### Example responses

Order — open an app:

```json
{
  "success": true,
  "out_message": "Abriendo WhatsApp.",
  "action_type": "OPEN_APP",
  "parameters_json": "{\"app_name\": \"whatsapp\"}",
  "confidence": 1.0,
  "requires_confirmation": false
}
```

Sensitive order — conversational confirmation (two turns):

Sensitive actions (by default `MAKE_CALL`, `SEND_MESSAGE`; per-user configurable)
are **not** executed on the spot. The backend asks out loud and holds the action
until the user replies. **Turn 1** returns `action_type: "NONE"` with the question
in `out_message` and `requires_confirmation: false` (the client must NOT pop its
own dialog — it just speaks/shows the question and listens):

```json
{
  "success": true,
  "out_message": "¿Confirmas que llame a mamá?",
  "action_type": "NONE",
  "parameters_json": "{}",
  "confidence": 1.0,
  "requires_confirmation": false,
  "task_complete": false
}
```

**Turn 2** — the client sends the user's spoken reply (e.g. `"sí"` / `"no"`) as a
normal `command` **with the same `order_id`**. On "sí" the backend emits the held
action to execute; on "no" it returns `NONE` + `task_complete: true`:

```json
{
  "success": true,
  "out_message": "De acuerdo, lo hago.",
  "action_type": "MAKE_CALL",
  "parameters_json": "{\"target\": \"mamá\"}",
  "confidence": 1.0,
  "requires_confirmation": false
}
```

Conversation — no action:

```json
{
  "success": true,
  "out_message": "Hoy hay cielos despejados y 24 grados.",
  "action_type": "NONE",
  "parameters_json": "{}",
  "confidence": 0.0,
  "requires_confirmation": false
}
```

## Android client expectations

1. Send the recognized order text (from STT or the text box) as `command`, and a
   client-generated **`order_id`** that stays constant for all turns of one task
   (including the confirmation question and the user's "sí/no" reply). A new
   `order_id` starts a fresh ReAct trace; empty falls back to the user identity.
2. Parse `parameters_json` into a map.
3. **Conversational confirmation:** when the backend asks (a `NONE` turn whose
   `out_message` is a question and `task_complete: false`), speak/show the
   question and capture the user's spoken reply, then send it as the next
   `command` **with the same `order_id`**. The backend interprets "sí/no" and
   either emits the action to execute or cancels. Do **not** pop a local confirm
   dialog for these — `requires_confirmation` stays `false` on this path. (The
   legacy `requires_confirmation` flag is only emitted when an action is left
   outside the user's confirm set; it remains for back-compat.)
4. Dispatch on `action_type` to the matching handler; `NONE` ⇒ just present
   `out_message` (and optionally synthesize it via `/voice/synthesize`). When
   `task_complete: false` on an executed action, re-capture the screen and call
   `ExecuteCommand` again (same `order_id`) to continue the ReAct loop.
5. Treat an **unknown** `action_type` (client older than backend) as `NONE`.

### User settings (confirmation scope)

Which action types require the spoken confirmation is per-user and configurable
via two gRPC RPCs (protected — access token required):

- `GetSettings(SettingsRequest) → SettingsResponse` — returns the user's settings
  as a JSON object string.
- `UpdateSettings(UpdateSettingsRequest{settings_json}) → SettingsResponse` —
  merges the given JSON into the user's stored settings.

The confirmation scope lives under `confirmation.require_for` (a list of action
type names), e.g. `{"confirmation": {"require_for": ["MAKE_CALL", "SEND_MESSAGE"]}}`.
An empty list means "confirm nothing" (full autonomy); omitting the key uses the
default (`MAKE_CALL`, `SEND_MESSAGE`).

## How to add a new action

1. **Backend:** add one `ActionSpec` to `ACTION_CATALOG` in
   `domain/intent/catalog.py` (tool name, description, slots, `requires_confirmation`).
   Nothing else changes — it auto-binds as a callable tool and appears here.
2. **Android:** add a handler for the new `action_type` in the `ActionRouter`
   and request any new runtime permission.
3. Update this table and regenerate nothing (no proto change unless you add new
   response fields).

## Configuration (backend)

| Env var | Purpose |
|---|---|
| `GOOGLE_API_KEY` | Required — enables Gemini function calling. Absent ⇒ `ExecuteCommand` returns `UNAVAILABLE`. |
| `LLM_MODEL` | Gemini model (default `gemini-3.1-flash-lite`). |

Readiness is reported under `providers.intent` in `GET /voice/health`.
