import contextvars

import grpc

from ports.token_service_port import TokenServicePort

# Holds the Principal verified by AuthInterceptor for the current RPC. Set once
# per request by the interceptor and read by handlers (US-10.2), so the token
# signature is never verified twice. Defaults to None outside an authorized RPC.
_principal_var: contextvars.ContextVar = contextvars.ContextVar(
    "atom_principal", default=None
)

# RPCs that issue the FIRST token, so they cannot require one. Full method paths
# include the proto package (com.atom.proto).
_PUBLIC_METHODS = {
    "/com.atom.proto.AtomAgentService/Register",
    "/com.atom.proto.AtomAgentService/Login",
    "/com.atom.proto.AtomAgentService/AuthenticateWithGoogle",
    "/com.atom.proto.AtomAgentService/RefreshToken",
}


def _bearer_token(metadata) -> str:
    md = dict(metadata or ())
    raw = md.get("authorization", "") or ""
    if raw.lower().startswith("bearer "):
        return raw[7:].strip()
    return raw.strip()


def principal_from_context():
    """The Principal verified by AuthInterceptor for the current RPC, or None.

    The interceptor verifies the token signature exactly once per request and
    stashes the Principal here, so protected handlers read the identity without
    re-checking the signature (US-10.2). None when auth is disabled or the RPC is
    public — handlers fall back to their own default in that case.
    """
    return _principal_var.get()


class AuthInterceptor(grpc.aio.ServerInterceptor):
    """Rejects non-public RPCs that lack a valid access token.

    Wraps each handler's behaviour so the check runs in the same coroutine that
    serves the call. When ``token_service`` is None (auth disabled) every RPC
    passes through unchanged.
    """

    def __init__(self, token_service: TokenServicePort | None):
        self._tokens = token_service

    async def intercept_service(self, continuation, handler_call_details):
        handler = await continuation(handler_call_details)
        if (handler is None
                or self._tokens is None
                or handler_call_details.method in _PUBLIC_METHODS):
            return handler
        return self._wrap(handler)

    def _wrap(self, handler):
        tokens = self._tokens

        async def _authorize(context):
            token = _bearer_token(context.invocation_metadata())
            principal = tokens.verify_access(token) if token else None
            if principal is None:
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED, "missing or invalid access token"
                )
            # Stash the verified principal so the handler reads it without re-verifying.
            _principal_var.set(principal)

        if handler.unary_unary is not None:
            async def unary_unary(request, context):
                await _authorize(context)
                return await handler.unary_unary(request, context)
            return grpc.unary_unary_rpc_method_handler(
                unary_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.unary_stream is not None:
            async def unary_stream(request, context):
                await _authorize(context)
                async for response in handler.unary_stream(request, context):
                    yield response
            return grpc.unary_stream_rpc_method_handler(
                unary_stream,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        # This service only uses unary_unary / unary_stream; leave others as-is.
        return handler
