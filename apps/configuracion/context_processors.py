from apps.configuracion.models import Configuracion

def configuracion_negocio(request):
    """
    Expone la configuración del negocio (nombre, logo, IGV, moneda) a todas las plantillas.
    """
    try:
        config = Configuracion.objects.first()
    except Exception:
        config = None

    return {
        "configuracion": config,
        "nombre_negocio": config.nombre_negocio if config and config.nombre_negocio else "ChocoGest",
        "logo_negocio": config.logo if config and config.logo else None,
        "igv_negocio": config.porcentaje_igv if config else 18,
        "moneda_negocio": config.moneda if config and config.moneda else "PEN",
    }
