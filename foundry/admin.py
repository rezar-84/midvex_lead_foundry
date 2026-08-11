from django.contrib import admin

from .models import MailboxConnection, Membership, Organization

admin.site.register(Organization)
admin.site.register(Membership)
admin.site.register(MailboxConnection)
