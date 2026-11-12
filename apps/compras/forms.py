from decimal import Decimal
from django import forms
from django.forms import formset_factory
from apps.core.forms import FormularioEstilizadoMixin
from apps.productos.models import Producto
from apps.proveedores.models import Proveedor
from apps.configuracion.models import MetodoPago
from .models import DetalleCompra


class CompraCabeceraForm(FormularioEstilizadoMixin, forms.Form):
    proveedor = forms.ModelChoiceField(queryset=Proveedor.objects.none(), label="Proveedor")
    tipo_documento = forms.ChoiceField(choices=[
        ("FACTURA", "Factura"), ("BOLETA", "Boleta"), ("RECIBO", "Recibo"), ("OTRO", "Otro"),
    ], label="Tipo de documento")
    numero_documento = forms.CharField(max_length=50, required=False, label="Número de documento")
    observaciones = forms.CharField(required=False, label="Observaciones", widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proveedor"].queryset = Proveedor.objects.filter(estado=True).order_by("razon_social")


class DetalleCompraForm(FormularioEstilizadoMixin, forms.Form):
    producto = forms.ModelChoiceField(queryset=Producto.objects.none(), label="Producto")
    cantidad = forms.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"), label="Cantidad")
    precio_unitario = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.00"), label="Precio unitario")
    descuento = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.00"), initial=Decimal("0.00"), label="Descuento")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = Producto.objects.filter(estado=True).order_by("nombre")

    def clean(self):
        datos = super().clean()
        cantidad = datos.get("cantidad")
        precio = datos.get("precio_unitario")
        descuento = datos.get("descuento")
        if cantidad is not None and precio is not None and descuento is not None:
            if descuento > cantidad * precio:
                self.add_error("descuento", "El descuento no puede superar el importe de la línea.")
        return datos


DetalleCompraFormSet = formset_factory(DetalleCompraForm, extra=1, can_delete=True, min_num=1, validate_min=True)


class LoteRecepcionForm(FormularioEstilizadoMixin, forms.Form):
    detalle = forms.ModelChoiceField(queryset=DetalleCompra.objects.none(), label="Producto de la compra")
    codigo_lote = forms.CharField(max_length=60, label="Código de lote")
    fecha_fabricacion = forms.DateField(required=False, label="Fecha de fabricación", widget=forms.DateInput(attrs={"type": "date"}))
    fecha_vencimiento = forms.DateField(label="Fecha de vencimiento", widget=forms.DateInput(attrs={"type": "date"}))
    cantidad = forms.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"), label="Cantidad del lote")

    def __init__(self, *args, detalles=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["detalle"].queryset = detalles if detalles is not None else DetalleCompra.objects.none()

    def clean(self):
        datos = super().clean()
        fabricacion = datos.get("fecha_fabricacion")
        vencimiento = datos.get("fecha_vencimiento")
        if fabricacion and vencimiento and fabricacion > vencimiento:
            self.add_error("fecha_fabricacion", "La fabricación no puede ser posterior al vencimiento.")
        return datos


LoteRecepcionFormSet = formset_factory(LoteRecepcionForm, extra=1, min_num=1, validate_min=True)


class PagoCompraForm(FormularioEstilizadoMixin, forms.Form):
    metodo_pago = forms.ModelChoiceField(queryset=MetodoPago.objects.none(), label="Método de pago")
    monto = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"), label="Monto")
    referencia = forms.CharField(max_length=100, required=False, label="Referencia")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["metodo_pago"].queryset = MetodoPago.objects.filter(estado=True).order_by("nombre")
