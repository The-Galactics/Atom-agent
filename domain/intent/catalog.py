from dataclasses import dataclass

from domain.intent.models import ActionType


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    type: str  # JSON-schema primitive: "string", "integer", "boolean"
    description: str
    required: bool = True
    enum: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ActionSpec:
    """Single source of truth for one supported action.

    Drives three things at once: the LLM tool schema (function calling), the
    runtime validation, and the Android contract documentation. To add a new
    action, append one ``ActionSpec`` here and implement its handler on the
    Android side — nothing else in the backend needs to change.
    """

    type: ActionType
    tool_name: str  # snake_case name exposed to the LLM as a callable tool
    description: str
    parameters: tuple[ParameterSpec, ...]
    # Sensitive actions (calling, messaging) should be confirmed by the user
    # on-device before they run.
    requires_confirmation: bool = False

    def to_openai_tool(self) -> dict:
        """Render this spec as an OpenAI-style function/tool definition.

        This is the format ``ChatModel.bind_tools`` accepts across providers
        (Gemini included), so the catalog stays provider-agnostic.
        """
        properties: dict = {}
        required: list[str] = []
        for param in self.parameters:
            schema: dict = {"type": param.type, "description": param.description}
            if param.enum is not None:
                schema["enum"] = list(param.enum)
            properties[param.name] = schema
            if param.required:
                required.append(param.name)
        return {
            "type": "function",
            "function": {
                "name": self.tool_name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


# --- The catalog ------------------------------------------------------------

ACTION_CATALOG: tuple[ActionSpec, ...] = (
    ActionSpec(
        type=ActionType.OPEN_APP,
        tool_name="open_app",
        description="Abre una aplicación instalada en el dispositivo del usuario.",
        parameters=(
            ParameterSpec("app_name", "string", "Nombre de la app a abrir, p. ej. 'whatsapp', 'spotify', 'cámara'."),
        ),
    ),
    ActionSpec(
        type=ActionType.MAKE_CALL,
        tool_name="make_call",
        description="Inicia una llamada telefónica a un contacto o número.",
        parameters=(
            ParameterSpec("target", "string", "Nombre del contacto o número de teléfono a llamar."),
        ),
        requires_confirmation=True,
    ),
    ActionSpec(
        type=ActionType.SEND_MESSAGE,
        tool_name="send_message",
        description="Envía un mensaje de texto a un contacto.",
        parameters=(
            ParameterSpec("recipient", "string", "Nombre del contacto o número destinatario."),
            ParameterSpec("body", "string", "Contenido del mensaje a enviar."),
            ParameterSpec("app", "string", "App de mensajería opcional, p. ej. 'whatsapp', 'sms'.", required=False),
        ),
        requires_confirmation=True,
    ),
    ActionSpec(
        type=ActionType.SET_ALARM,
        tool_name="set_alarm",
        description="Programa una alarma a una hora concreta.",
        parameters=(
            ParameterSpec("time", "string", "Hora de la alarma en formato 24h 'HH:MM'."),
            ParameterSpec("label", "string", "Etiqueta opcional de la alarma.", required=False),
        ),
    ),
    ActionSpec(
        type=ActionType.SET_TIMER,
        tool_name="set_timer",
        description="Inicia un temporizador con una duración dada.",
        parameters=(
            ParameterSpec("duration_seconds", "integer", "Duración del temporizador en segundos."),
            ParameterSpec("label", "string", "Etiqueta opcional del temporizador.", required=False),
        ),
    ),
    ActionSpec(
        type=ActionType.TOGGLE_SETTING,
        tool_name="toggle_setting",
        description="Activa o desactiva un ajuste rápido del sistema.",
        parameters=(
            ParameterSpec(
                "setting", "string", "Ajuste a cambiar.",
                enum=("wifi", "bluetooth", "flashlight", "do_not_disturb"),
            ),
            ParameterSpec(
                "state", "string", "Estado deseado del ajuste.",
                enum=("on", "off", "toggle"),
            ),
        ),
    ),
    # --- Accessibility-powered actions --------------------------------------
    # Fulfilled on-device by the AccessibilityService (global navigation,
    # gestures, reading and tapping on-screen nodes).
    ActionSpec(
        type=ActionType.NAVIGATE,
        tool_name="navigate",
        description="Realiza una navegación global del sistema: atrás, inicio, recientes o ajustes rápidos.",
        parameters=(
            ParameterSpec(
                "direction", "string", "Acción de navegación a realizar.",
                enum=("back", "home", "recents", "quick_settings"),
            ),
        ),
    ),
    ActionSpec(
        type=ActionType.SCROLL,
        tool_name="scroll",
        description="Desplaza la pantalla actual en la dirección indicada.",
        parameters=(
            ParameterSpec(
                "direction", "string", "Dirección del desplazamiento.",
                enum=("up", "down", "left", "right"),
            ),
        ),
    ),
    ActionSpec(
        type=ActionType.READ_SCREEN,
        tool_name="read_screen",
        description=(
            "Lee en voz alta el contenido visible de la pantalla actual. Úsala "
            "siempre que el usuario pida leer, oír o saber qué hay en la pantalla, "
            "p. ej. 'lee la pantalla', 'léeme la pantalla', 'qué hay en la pantalla', "
            "'qué ves', 'qué pone', 'descríbeme la pantalla'."
        ),
        parameters=(),
    ),
    ActionSpec(
        type=ActionType.TAP_ELEMENT,
        tool_name="tap_element",
        description="Pulsa un elemento de la pantalla identificado por su texto visible.",
        parameters=(
            ParameterSpec("text", "string", "Texto visible del elemento a pulsar, p. ej. 'Aceptar', 'Ajustes'."),
        ),
        requires_confirmation=True,
    ),
)

# Lookups keyed both ways so adapters/use-cases never hard-code action names.
_BY_TOOL_NAME = {spec.tool_name: spec for spec in ACTION_CATALOG}
_BY_TYPE = {spec.type: spec for spec in ACTION_CATALOG}


def spec_for_tool(tool_name: str) -> ActionSpec | None:
    return _BY_TOOL_NAME.get(tool_name)


def spec_for_type(action_type: ActionType) -> ActionSpec | None:
    return _BY_TYPE.get(action_type)


def openai_tools() -> list[dict]:
    """All actions as OpenAI-style tool definitions for ``bind_tools``."""
    return [spec.to_openai_tool() for spec in ACTION_CATALOG]
