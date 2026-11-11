from django import forms
from apps.core.forms import BaseModelForm
from .models import Producto, Categoria, Marca

class CategoriaForm(BaseModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "imagen", "estado"]


class MarcaForm(BaseModelForm):
    class Meta:
        model = Marca
        fields = ["nombre", "descripcion", "estado"]


class ProductoForm(BaseModelForm):
    class Meta:
        model = Producto
        fields = [
            "categoria", "marca", "codigo", "codigo_barras", "nombre",
            "descripcion", "peso_gramos", "precio_compra_referencial",
            "precio_venta", "stock_minimo", "imagen", "estado"
        ]
