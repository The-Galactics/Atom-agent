from domain.intent.catalog import spec_for_tool, validate_and_coerce_args


def test_valid_args_pass_unchanged():
    spec = spec_for_tool("open_app")
    coerced, errors = validate_and_coerce_args(spec, {"app_name": "spotify"})
    assert errors == []
    assert coerced["app_name"] == "spotify"


def test_missing_required_param_is_error():
    spec = spec_for_tool("make_call")  # 'target' is required
    _, errors = validate_and_coerce_args(spec, {})
    assert errors


def test_enum_violation_is_error():
    spec = spec_for_tool("toggle_setting")  # setting/state are enums
    _, errors = validate_and_coerce_args(spec, {"setting": "teleport", "state": "on"})
    assert errors


def test_enum_valid_value_passes():
    spec = spec_for_tool("toggle_setting")
    _, errors = validate_and_coerce_args(spec, {"setting": "wifi", "state": "on"})
    assert errors == []


def test_integer_string_is_coerced():
    spec = spec_for_tool("set_timer")  # duration_seconds is integer
    coerced, errors = validate_and_coerce_args(spec, {"duration_seconds": "300"})
    assert errors == []
    assert coerced["duration_seconds"] == 300


def test_non_numeric_integer_is_error():
    spec = spec_for_tool("set_timer")
    _, errors = validate_and_coerce_args(spec, {"duration_seconds": "five"})
    assert errors


def test_boolean_string_is_coerced():
    spec = spec_for_tool("type_text")  # submit is optional boolean
    coerced, errors = validate_and_coerce_args(spec, {"text": "hi", "submit": "false"})
    assert errors == []
    assert coerced["submit"] is False


def test_optional_missing_param_is_not_an_error():
    spec = spec_for_tool("set_alarm")  # 'label' optional
    _, errors = validate_and_coerce_args(spec, {"time": "07:30"})
    assert errors == []
