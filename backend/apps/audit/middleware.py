import json
import time

from .models import OperationLog

SENSITIVE_KEYS = {"password", "token", "api_key", "llm_api_key", "authorization"}


class OperationLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):  # noqa: ANN001
        if not request.path.startswith("/api/") or request.path.endswith("/health/"):
            return self.get_response(request)

        start = time.perf_counter()
        response_code = 500
        status = OperationLog.Status.SUCCESS

        try:
            response = self.get_response(request)
            response_code = getattr(response, "status_code", 200)
            if response_code >= 400:
                status = OperationLog.Status.ERROR
            return response
        except Exception:
            status = OperationLog.Status.ERROR
            raise
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self._persist_log(request, response_code, status, duration_ms)

    def _persist_log(self, request, response_code: int, status: str, duration_ms: int) -> None:  # noqa: ANN001
        try:
            body = ""
            if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                content_type = request.META.get("CONTENT_TYPE", "")
                if "multipart/form-data" in content_type:
                    body = "<multipart>"
                else:
                    raw_body = request.body.decode("utf-8", errors="ignore")[:2000]
                    body = self._sanitize_body(raw_body)

            parts = [item for item in request.path.strip("/").split("/") if item]
            module = parts[2] if len(parts) > 2 else ""
            action = parts[3] if len(parts) > 3 else ""
            user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None

            OperationLog.objects.create(
                user=user,
                module=module,
                action=action,
                method=request.method,
                path=request.path,
                ip=request.META.get("REMOTE_ADDR", ""),
                request_body=body,
                response_code=response_code,
                status=status,
                duration_ms=duration_ms,
            )
        except Exception:
            return None

    def _sanitize_body(self, raw_body: str) -> str:
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return raw_body
        return json.dumps(self._mask_sensitive(payload), ensure_ascii=False)[:2000]

    def _mask_sensitive(self, value):  # noqa: ANN001
        if isinstance(value, dict):
            return {
                key: ("***" if key.lower() in SENSITIVE_KEYS else self._mask_sensitive(item))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._mask_sensitive(item) for item in value]
        return value
