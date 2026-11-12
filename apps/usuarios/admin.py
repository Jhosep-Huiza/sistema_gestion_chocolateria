from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.core.admin import TransaccionSoloLecturaAdmin
from .models import Auditoria, Rol, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Datos personales ChocoGest", {"fields": ("nombres", "apellidos", "telefono", "rol")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Datos personales ChocoGest", {"fields": ("nombres", "apellidos", "telefono", "rol")}),
    )
    list_display = ("username", "email", "nombres", "apellidos", "rol", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "rol")
    search_fields = ("username", "email", "nombres", "apellidos", "telefono")
    ordering = ("username",)
    readonly_fields = ("last_login", "date_joined")


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "descripcion")


@admin.register(Auditoria)
class AuditoriaAdmin(TransaccionSoloLecturaAdmin):
    list_display = ("fecha", "usuario", "accion", "tabla_afectada", "registro_id", "direccion_ip")
    list_filter = ("accion", "tabla_afectada", "fecha")
    search_fields = ("usuario__username", "accion", "tabla_afectada", "descripcion", "direccion_ip")
    list_select_related = ("usuario",)
    date_hierarchy = "fecha"
