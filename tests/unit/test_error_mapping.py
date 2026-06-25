import logging

from api import exceptions as ex


def test_generic_message_known_code():
    assert ex.generic_message("CHAT_UNAVAILABLE") == ex.GENERIC_MESSAGES["CHAT_UNAVAILABLE"]


def test_generic_message_unknown_code_falls_back_to_internal():
    assert ex.generic_message("DOES_NOT_EXIST") == ex.GENERIC_MESSAGES["INTERNAL"]


def test_request_ids_are_unique():
    assert ex.new_request_id() != ex.new_request_id()


def test_grpc_internal_detail_carries_request_id_but_no_exception_text():
    request_id = "abc123"
    detail = ex.grpc_internal_detail(request_id)
    assert request_id in detail
    # The client-facing detail must never echo internal exception text.
    assert "boom" not in detail


def test_log_exception_records_full_detail_server_side(caplog):
    request_id = ex.new_request_id()
    with caplog.at_level(logging.ERROR):
        ex.log_exception("INTERNAL", request_id, RuntimeError("secret boom"), context="ExecuteCommand")
    # The real exception text and the request_id are available in the logs (ops),
    # never in what we hand back to the client.
    assert "secret boom" in caplog.text
    assert request_id in caplog.text
    assert "ExecuteCommand" in caplog.text
