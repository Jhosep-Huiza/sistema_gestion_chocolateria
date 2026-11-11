from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Rol, Auditoria

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Datos personales ChocoGest", {"fields": ("nombres","apellidos","telefono","rol")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Datos personales ChocoGest", {"fields": ("nombres","apellidos","telefono","rol")}),)

admin.site.register(Rol)
admin.site.register(Auditoria)
