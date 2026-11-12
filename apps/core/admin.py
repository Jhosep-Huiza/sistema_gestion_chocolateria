from django.contrib import admin


class TransaccionSoloLecturaAdmin(admin.ModelAdmin):
    """Permite consultar transacciones en admin sin crear, editar ni borrar."""
    def get_readonly_fields(self, request, obj=None):
        campos = [campo.name for campo in self.model._meta.concrete_fields]
        campos.extend(campo.name for campo in self.model._meta.many_to_many)
        campos.extend(self.readonly_fields)
        return tuple(campos)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
