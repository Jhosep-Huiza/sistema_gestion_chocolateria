from decimal import Decimal
import datetime
from django import template
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()

@register.filter
def obtener_campo(objeto, campo):
    """Obtiene el valor de un campo o método con soporte para notación de puntos (ej. 'categoria.nombre')."""
    if objeto is None or not campo:
        return ""
    val = objeto
    for parte in str(campo).split("."):
        if hasattr(val, parte):
            val = getattr(val, parte)
            if callable(val) and not isinstance(val, type):
                try:
                    val = val()
                except Exception:
                    return ""
        elif isinstance(val, dict):
            val = val.get(parte, "")
        else:
            return ""
    return val


@register.simple_tag
def render_celda(objeto, columna, moneda="PEN"):
    """
    Renderiza el contenido de una celda para una tabla de listado según su configuración.
    """
    if isinstance(columna, dict):
        campo = columna.get("campo", "")
        titulo = columna.get("titulo", "")
        tipo = columna.get("tipo", "texto")
        destacado = columna.get("destacado", False)
    else:
        campo = str(columna)
        tipo = "texto"
        destacado = False

    valor = obtener_campo(objeto, campo)

    if valor is None or valor == "":
        return mark_safe("<span class='text-muted'>-</span>")

    # Renderizado según tipo
    if tipo == "badge" or isinstance(valor, bool) or campo in ("estado", "status"):
        if valor is True or valor == 1 or str(valor).upper() in ("ACTIVO", "ABIERTA", "PAGADA", "CONFIRMADO", "DISPONIBLE", "APROBADA"):
            texto = "Activo" if isinstance(valor, bool) else str(valor).title()
            return mark_safe(f'<span class="pill pill-success">{escape(texto)}</span>')
        elif valor is False or valor == 0 or str(valor).upper() in ("INACTIVO", "CERRADA", "ANULADO", "AGOTADO", "VENCIDO", "RECHAZADA"):
            texto = "Inactivo" if isinstance(valor, bool) else str(valor).title()
            return mark_safe(f'<span class="pill pill-danger">{escape(texto)}</span>')
        else:
            return mark_safe(f'<span class="pill pill-warning">{escape(str(valor).title())}</span>')

    if tipo == "moneda" or (isinstance(valor, Decimal) and "precio" in campo.lower() or "total" in campo.lower() or "monto" in campo.lower() or "subtotal" in campo.lower()):
        simbolo = "S/" if moneda == "PEN" else moneda
        try:
            return mark_safe(f'<b>{simbolo} {valor:,.2f}</b>')
        except (ValueError, TypeError):
            return mark_safe(f'{simbolo} {escape(str(valor))}')

    if tipo == "numero" or isinstance(valor, (int, float, Decimal)):
        if isinstance(valor, Decimal):
            return f"{valor:g}"
        return str(valor)

    if isinstance(valor, datetime.datetime):
        return valor.strftime("%d/%m/%Y %H:%M")

    if isinstance(valor, datetime.date):
        return valor.strftime("%d/%m/%Y")

    # Si es imagen
    if hasattr(valor, "url"):
        try:
            return mark_safe(f'<img src="{escape(valor.url)}" class="table-thumb" alt="Miniatura">')
        except Exception:
            return mark_safe("<span class='text-muted'>Sin imagen</span>")

    texto = escape(str(valor))
    if destacado:
        return mark_safe(f'<b>{texto}</b>')
    return mark_safe(texto)


@register.filter
def es_checkbox(field):
    """Determina si un BoundField corresponde a un CheckboxInput."""
    return isinstance(field.field.widget, forms.CheckboxInput)
