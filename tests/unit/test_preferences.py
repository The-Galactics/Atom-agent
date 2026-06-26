from domain.user.preferences import (
    DEFAULT_CONFIRM_ACTIONS,
    confirm_actions_from_settings,
)


def test_default_is_outward_facing_actions_only():
    # Calls and messages by default; TAP_ELEMENT excluded so autonomous
    # navigation isn't interrupted by a confirmation on every tap.
    assert DEFAULT_CONFIRM_ACTIONS == frozenset({"MAKE_CALL", "SEND_MESSAGE"})


def test_empty_or_missing_settings_returns_default():
    assert confirm_actions_from_settings(None) == DEFAULT_CONFIRM_ACTIONS
    assert confirm_actions_from_settings({}) == DEFAULT_CONFIRM_ACTIONS
    assert confirm_actions_from_settings({"other": 1}) == DEFAULT_CONFIRM_ACTIONS


def test_explicit_override_respected():
    settings = {"confirmation": {"require_for": ["OPEN_APP", "MAKE_CALL"]}}
    assert confirm_actions_from_settings(settings) == frozenset({"OPEN_APP", "MAKE_CALL"})


def test_empty_list_means_confirm_nothing():
    assert confirm_actions_from_settings({"confirmation": {"require_for": []}}) == frozenset()


def test_unknown_actions_filtered_and_case_normalized():
    settings = {"confirmation": {"require_for": ["make_call", "BOGUS", "send_message"]}}
    assert confirm_actions_from_settings(settings) == frozenset({"MAKE_CALL", "SEND_MESSAGE"})


def test_malformed_confirmation_block_falls_back_to_default():
    assert confirm_actions_from_settings({"confirmation": "nope"}) == DEFAULT_CONFIRM_ACTIONS
    assert confirm_actions_from_settings({"confirmation": {"require_for": "MAKE_CALL"}}) == DEFAULT_CONFIRM_ACTIONS
