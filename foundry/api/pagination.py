from __future__ import annotations

from typing import Any

from django.core.paginator import Paginator
from django.db.models import QuerySet


def paginate_queryset(
    queryset: QuerySet[Any], page_number: int, per_page: int
) -> tuple[list[Any], dict[str, int]]:
    """Return the page's objects plus the pagination envelope fields."""
    paginator = Paginator(queryset, per_page)
    page = paginator.get_page(page_number)
    meta = {
        "count": paginator.count,
        "page": page.number,
        "pages": paginator.num_pages,
        "per_page": per_page,
    }
    return list(page.object_list), meta
