from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from .models import MFADevice


class MFARequiredMiddleware:
    exempt_prefixes = ("/accounts/", "/mfa/", "/static/", "/health/")

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated and not request.path.startswith(self.exempt_prefixes):
            device = MFADevice.objects.filter(user=request.user, confirmed_at__isnull=False).first()
            if device is None:
                return redirect("mfa_setup")
            if not request.session.get("mfa_verified"):
                return redirect("mfa_verify")
        return self.get_response(request)
