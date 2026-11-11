from django import forms

class FormularioEstilizadoMixin:
    """
    Mixin para asignar automáticamente estilos y atributos HTML a los widgets de formularios:
    - Inputs de tipo fecha y fecha/hora nativos de HTML5.
    - Checkboxes y selectores adaptados.
    - Placeholders descriptivos por defecto basados en las etiquetas.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            widget_class = widget.__class__.__name__

            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.DateInput):
                widget.input_type = "date"
                widget.attrs.setdefault("class", "form-control")
            elif isinstance(widget, forms.DateTimeInput):
                widget.input_type = "datetime-local"
                widget.attrs.setdefault("class", "form-control")
            elif isinstance(widget, (forms.FileInput, forms.ClearableFileInput)):
                widget.attrs.setdefault("class", "form-file-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", "form-textarea")
                widget.attrs.setdefault("rows", 3)
            else:
                widget.attrs.setdefault("class", "form-control")

            # Placeholder por defecto si no es select o checkbox o archivo
            if not isinstance(widget, (forms.CheckboxInput, forms.Select, forms.FileInput, forms.ClearableFileInput)):
                if not widget.attrs.get("placeholder") and field.label:
                    widget.attrs["placeholder"] = f"Ingresa {field.label.lower()}"


class BaseModelForm(FormularioEstilizadoMixin, forms.ModelForm):
    """Clase base estandarizada para formularios basados en modelos."""
    pass
