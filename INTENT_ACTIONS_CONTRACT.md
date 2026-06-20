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
  string user_id = 1;
  string command = 2;                       // the user's natural-language order (text)
  repeated ScreenElement screen_elements = 3; // structured screen map (accessibility)
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

Sensitive order — confirm first:

```json
{
  "success": true,
  "out_message": "¿Quieres que llame a mamá?",
  "action_type": "MAKE_CALL",
  "parameters_json": "{\"target\": \"mamá\"}",
  "confidence": 1.0,
  "requires_confirmation": true
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

1. Send the recognized order text (from STT or the text box) as `command`.
2. Parse `parameters_json` into a map.
3. If `requires_confirmation` is true (or confidence is low), show a confirm
   prompt using `out_message` before executing.
4. Dispatch on `action_type` to the matching handler; `NONE` ⇒ just present
   `out_message` (and optionally synthesize it via `/voice/synthesize`).
5. Treat an **unknown** `action_type` (client older than backend) as `NONE`.

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
| `LLM_MODEL` | Gemini model (default `gemini-1.5-flash`). |

Readiness is reported under `providers.intent` in `GET /voice/health`.
