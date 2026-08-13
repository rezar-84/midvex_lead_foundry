from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

INDEX_PATH = settings.BASE_DIR / "frontend" / "dist" / "index.html"

_cached_index: str | None = None


def _index_html() -> str:
    global _cached_index
    if settings.DEBUG or _cached_index is None:
        _cached_index = INDEX_PATH.read_text(encoding="utf-8")
    return _cached_index


@ensure_csrf_cookie
def spa_index(request: HttpRequest) -> HttpResponse:
    try:
        html = _index_html()
    except FileNotFoundError:
        return HttpResponse(
            "Frontend build missing. Run `npm run build` in frontend/ (or use the Vite dev "
            "server on :5173 during development).",
            status=501,
            content_type="text/plain",
        )
    return HttpResponse(html)
