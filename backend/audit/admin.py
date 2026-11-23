from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor", "action", "target_type", "target_id", "outcome")
    list_filter = ("action", "outcome")
    search_fields = ("action", "target_type", "target_id")
    readonly_fields = ("id", "timestamp")
