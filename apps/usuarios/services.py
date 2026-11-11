from apps.usuarios.models import Auditoria
from contextvars import ContextVar

_contexto_solicitud = ContextVar("chocogest_auditoria", default=None)


def establecer_contexto_auditoria(request):
    """Asocia el usuario e IP de la petición actual a eventos de modelo."""
    return _contexto_solicitud.set((request.user, obtener_ip(request)))


def limpiar_contexto_auditoria(token):
    _contexto_solicitud.reset(token)


def contexto_auditoria():
    return _contexto_solicitud.get() or (None, None)


def registrar_auditoria(*, usuario, accion, tabla_afectada, registro_id=None,
                        descripcion="", direccion_ip=None):
    """Guarda una acción sensible con el usuario y la IP disponibles."""
    return Auditoria.objects.create(
        usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
        accion=accion,
        tabla_afectada=tabla_afectada,
        registro_id=registro_id,
        descripcion=descripcion,
        direccion_ip=direccion_ip,
    )


def obtener_ip(request):
    """Obtiene la IP de origen respetando el proxy configurado por el despliegue."""
    if not request:
        return None
    ip_proxy = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = ip_proxy.split(",")[0].strip() if ip_proxy else request.META.get("REMOTE_ADDR")
    return ip or None
