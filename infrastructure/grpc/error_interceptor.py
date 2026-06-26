"""Global gRPC error sanitization (US-10.1).

Wraps every handler so an unhandled exception is turned into a generic
``INTERNAL`` status — the client never sees the real exception text (stack,
DB DSNs, env). The full cause is logged server-side, correlated by a
``request_id`` that is also handed to the client for support. A handler's
deliberate ``context.abort()`` (which carries an intended status) passes
through unchanged.
"""

import grpc

from api.exceptions import grpc_internal_detail, log_exception, new_request_id


class ErrorInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(self, continuation, handler_call_details):
        handler = await continuation(handler_call_details)
        if handler is None:
            return handler
        return self._wrap(handler, handler_call_details.method)

    def _wrap(self, handler, method):
        async def _sanitize(exc, context):
            # A deliberate abort already carries the intended status; let it stand.
            if isinstance(exc, grpc.aio.AbortError):
                raise exc
            request_id = new_request_id()
            log_exception("INTERNAL", request_id, exc, context=method)
            await context.abort(
                grpc.StatusCode.INTERNAL, grpc_internal_detail(request_id)
            )

        if handler.unary_unary is not None:
            async def unary_unary(request, context):
                try:
                    return await handler.unary_unary(request, context)
                except Exception as exc:  # noqa: BLE001 — funnel to generic INTERNAL
                    await _sanitize(exc, context)

            return grpc.unary_unary_rpc_method_handler(
                unary_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.unary_stream is not None:
            async def unary_stream(request, context):
                try:
                    async for response in handler.unary_stream(request, context):
                        yield response
                except Exception as exc:  # noqa: BLE001 — funnel to generic INTERNAL
                    await _sanitize(exc, context)

            return grpc.unary_stream_rpc_method_handler(
                unary_stream,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        # This service only uses unary_unary / unary_stream; leave others as-is.
        return handler
