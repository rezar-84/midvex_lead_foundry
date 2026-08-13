from __future__ import annotations

from ninja import NinjaAPI
from ninja.security import django_auth

from .errors import register_exception_handlers
from .routers.core import router as core_router
from .routers.projects import router as projects_router

# Session (cookie) auth: django-ninja enforces the CSRF check automatically
# for cookie-based auth since 1.6, so no explicit csrf flag exists any more.
api = NinjaAPI(
    title="Lead Foundry API",
    auth=django_auth,
    docs_url=None,
    urls_namespace="api",
)
register_exception_handlers(api)
api.add_router("", core_router)
api.add_router("", projects_router)
