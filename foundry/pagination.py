from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest

DEFAULT_PER_PAGE = 50


def paginate(
    request: HttpRequest,
    object_list: QuerySet[Any] | Sequence[Any],
    per_page: int = DEFAULT_PER_PAGE,
) -> tuple[Page[Any], str]:
    """Return the requested page plus the querystring to preserve on page links.

    Invalid or out-of-range page numbers clamp to the nearest valid page rather
    than raising, so stale links keep working.
    """
    paginator = Paginator(object_list, per_page)
    page = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return page, params.urlencode()
