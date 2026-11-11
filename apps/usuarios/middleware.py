from apps.usuarios.services import establecer_contexto_auditoria, limpiar_contexto_auditoria


class ContextoAuditoriaMiddleware:
    """Expone usuario e IP de la petición durante la ejecución de servicios y señales."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = establecer_contexto_auditoria(request)
        try:
            return self.get_response(request)
        finally:
            limpiar_contexto_auditoria(token)
