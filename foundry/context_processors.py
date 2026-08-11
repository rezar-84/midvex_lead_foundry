from django.http import HttpRequest

from .access import membership_for


def active_membership(request: HttpRequest) -> dict[str, object]:
    return {"active_membership": membership_for(request)}
