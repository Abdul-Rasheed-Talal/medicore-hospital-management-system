from django.contrib import admin

from .models import Department, Service, ServiceCategory, StaffProfile, StaffStatusChange, VisitType


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(VisitType)
class VisitTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("code", "name")


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("staff_id", "full_name", "job_title", "department", "role", "status")
    list_filter = ("status", "role", "department")
    search_fields = ("staff_id", "full_name")
    readonly_fields = ("staff_id",)


@admin.register(StaffStatusChange)
class StaffStatusChangeAdmin(admin.ModelAdmin):
    list_display = ("staff", "previous_status", "new_status", "actor", "timestamp")
    readonly_fields = ("staff", "previous_status", "new_status", "reason", "actor", "timestamp")
