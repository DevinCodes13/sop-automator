import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

from .metrics import HTTP_LATENCY, HTTP_REQUESTS

logger = logging.getLogger("sop.requests")


def _route_path(request) -> str:
    return getattr(request.scope.get("route"), "path", "unmatched")


def _record(request, status: int, elapsed: float):
    path = _route_path(request)
    if path != "/metrics":
        HTTP_REQUESTS.labels(request.method, path, str(status)).inc()
        HTTP_LATENCY.labels(request.method, path).observe(elapsed)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = time.perf_counter() - start
            _record(request, 500, elapsed)
            logger.error(json.dumps({
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": 500,
                "ms": round(elapsed * 1000, 1),
                "error": "unhandled exception",
            }))
            raise
        elapsed = time.perf_counter() - start
        _record(request, response.status_code, elapsed)
        response.headers["X-Request-ID"] = request_id
        logger.info(json.dumps({
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": round(elapsed * 1000, 1),
        }))
        return response
