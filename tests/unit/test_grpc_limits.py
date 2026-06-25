from types import SimpleNamespace

from infrastructure.grpc.server import grpc_server_options, grpc_max_concurrent_rpcs


def _settings(**kw):
    base = dict(
        grpc_max_message_bytes=1234,
        grpc_max_concurrent_rpcs=7,
        grpc_handler_timeout_seconds=12.0,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_server_options_set_inbound_and_outbound_message_limits():
    opts = dict(grpc_server_options(_settings(grpc_max_message_bytes=2048)))
    assert opts["grpc.max_receive_message_length"] == 2048
    assert opts["grpc.max_send_message_length"] == 2048


def test_max_concurrent_rpcs_reads_settings():
    assert grpc_max_concurrent_rpcs(_settings(grpc_max_concurrent_rpcs=99)) == 99
