from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import HttpError, ValidationError


def error_payload(code: str, message: str, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "fields": fields}}


def register_exception_handlers(api: NinjaAPI) -> None:
    @api.exception_handler(HttpError)
    def http_error(request: HttpRequest, exc: HttpError) -> HttpResponse:
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 409: "conflict"}.get(
            exc.status_code, "error"
        )
        return api.create_response(request, error_payload(code, str(exc)), status=exc.status_code)

    @api.exception_handler(ValidationError)
    def validation_error(request: HttpRequest, exc: ValidationError) -> HttpResponse:
        fields: dict[str, Any] = {}
        for item in exc.errors:
            location = ".".join(str(part) for part in item.get("loc", ()) if part != "body")
            fields[location or "__all__"] = item.get("msg", "invalid")
        return api.create_response(
            request,
            error_payload("validation_error", "Invalid input.", fields),
            status=400,
        )

    @api.exception_handler(PermissionDenied)
    def permission_denied(request: HttpRequest, exc: PermissionDenied) -> HttpResponse:
        return api.create_response(
            request, error_payload("forbidden", "Permission denied."), status=403
        )

    @api.exception_handler(Http404)
    def not_found(request: HttpRequest, exc: Http404) -> HttpResponse:
        return api.create_response(request, error_payload("not_found", "Not found."), status=404)
