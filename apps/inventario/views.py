from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from apps.core.mixins import requiere_roles
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from apps.core.views import BaseListView, BaseCreateView, BaseUpdateView, BaseDeleteView
from .models import Almacen, Inventario, Lote, MovimientoInventario
from .forms import AlmacenForm, AjusteInventarioForm, TransferenciaStockForm, EstadoLoteForm
from .services import ajustar_inventario, transferir_stock, cambiar_estado_lote
from apps.usuarios.services import obtener_ip

@requiere_roles("Vendedor", "Almacenero")
def inicio(request):
    return redirect("inventario:stock")


class StockListView(BaseListView):
    model = Inventario
    titulo = "Stock por producto y almacén"
    subtitulo = "Consulta existencias y detecta productos por debajo del stock mínimo."
    template_name = "modulo/listado.html"
    search_fields = ["producto__codigo", "producto__nombre", "almacen__nombre"]
    columnas = [
        {"campo": "producto.codigo", "titulo": "Código"},
        {"campo": "producto.nombre", "titulo": "Producto", "destacado": True},
        {"campo": "almacen.nombre", "titulo": "Almacén"},
        {"campo": "stock_actual", "titulo": "Stock", "tipo": "numero"},
        {"campo": "producto.stock_minimo", "titulo": "Mínimo", "tipo": "numero"},
        {"campo": "estado_stock", "titulo": "Alerta", "tipo": "badge"},
    ]
    roles_permitidos = ["Administrador", "Vendedor", "Almacenero"]
    url_ajustar = "inventario:ajustar"
    url_transferir = "inventario:transferir"
    roles_crear = ["Administrador", "Almacenero"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("producto", "almacen")
        almacen_id = self.request.GET.get("almacen", "")
        if almacen_id.isdigit():
            qs = qs.filter(almacen_id=int(almacen_id))
        if self.request.GET.get("alerta") == "bajo":
            from django.db.models import F
            qs = qs.filter(stock_actual__lte=F("producto__stock_minimo"))
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update({
            "filtro_stock": True,
            "almacenes": Almacen.objects.filter(estado=True).order_by("nombre"),
            "almacen_filtro": self.request.GET.get("almacen", ""),
            "alerta_filtro": self.request.GET.get("alerta", ""),
        })
        return contexto


class LoteListView(BaseListView):
    model = Lote
    titulo = "Lotes y vigencia"
    subtitulo = "Consulta vencimientos, cuarentenas y cantidades disponibles por lote."
    template_name = "modulo/listado.html"
    search_fields = ["codigo_lote", "producto__codigo", "producto__nombre", "almacen__nombre"]
    columnas = [
        {"campo": "codigo_lote", "titulo": "Lote", "destacado": True},
        {"campo": "producto.nombre", "titulo": "Producto"},
        {"campo": "almacen.nombre", "titulo": "Almacén"},
        {"campo": "fecha_vencimiento", "titulo": "Vencimiento"},
        {"campo": "cantidad_disponible", "titulo": "Disponible", "tipo": "numero"},
        {"campo": "estado", "titulo": "Estado", "tipo": "badge"},
    ]
    url_ver = "inventario:lote_detalle"
    roles_permitidos = ["Administrador", "Vendedor", "Almacenero"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("producto", "almacen")
        vigencia = self.request.GET.get("vigencia", "")
        hoy = timezone.localdate()
        if vigencia == "vigente":
            qs = qs.filter(fecha_vencimiento__gte=hoy, estado="DISPONIBLE", cantidad_disponible__gt=0)
        elif vigencia == "por_vencer":
            qs = qs.filter(fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=hoy + timezone.timedelta(days=30), estado="DISPONIBLE", cantidad_disponible__gt=0)
        elif vigencia == "vencido":
            from django.db.models import Q
            qs = qs.filter(Q(fecha_vencimiento__lt=hoy) | Q(estado="VENCIDO"))
        elif vigencia == "cuarentena":
            qs = qs.filter(estado="CUARENTENA")
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["vigencia_filtro"] = self.request.GET.get("vigencia", "")
        contexto["filtro_lotes"] = True
        return contexto


class MovimientoListView(BaseListView):
    model = MovimientoInventario
    titulo = "Kardex de inventario"
    subtitulo = "Revisa las entradas, salidas, ajustes y transferencias."
    template_name = "modulo/listado.html"
    search_fields = ["producto__codigo", "producto__nombre", "lote__codigo_lote", "motivo"]
    columnas = [
        {"campo": "fecha", "titulo": "Fecha"},
        {"campo": "producto.nombre", "titulo": "Producto"},
        {"campo": "almacen.nombre", "titulo": "Almacén"},
        {"campo": "lote.codigo_lote", "titulo": "Lote"},
        {"campo": "tipo_movimiento", "titulo": "Movimiento", "tipo": "badge"},
        {"campo": "cantidad", "titulo": "Cantidad", "tipo": "numero"},
        {"campo": "motivo", "titulo": "Motivo"},
        {"campo": "usuario.username", "titulo": "Usuario"},
    ]
    roles_permitidos = ["Administrador", "Vendedor", "Almacenero"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("producto", "almacen", "lote", "usuario")
        producto = self.request.GET.get("producto", "")
        almacen = self.request.GET.get("almacen", "")
        tipo = self.request.GET.get("tipo", "")
        desde = parse_date(self.request.GET.get("desde", ""))
        hasta = parse_date(self.request.GET.get("hasta", ""))
        if producto.isdigit(): qs = qs.filter(producto_id=int(producto))
        if almacen.isdigit(): qs = qs.filter(almacen_id=int(almacen))
        if tipo in {opcion[0] for opcion in MovimientoInventario.TIPOS}: qs = qs.filter(tipo_movimiento=tipo)
        if desde: qs = qs.filter(fecha__date__gte=desde)
        if hasta: qs = qs.filter(fecha__date__lte=hasta)
        return qs

    def get_context_data(self, **kwargs):
        from apps.productos.models import Producto
        contexto = super().get_context_data(**kwargs)
        contexto.update({
            "filtro_movimientos": True,
            "productos": Producto.objects.filter(estado=True).order_by("nombre"),
            "almacenes": Almacen.objects.filter(estado=True).order_by("nombre"),
            "tipos_movimiento": MovimientoInventario.TIPOS,
            "producto_filtro": self.request.GET.get("producto", ""),
            "almacen_filtro": self.request.GET.get("almacen", ""),
            "tipo_filtro": self.request.GET.get("tipo", ""),
            "desde": self.request.GET.get("desde", ""), "hasta": self.request.GET.get("hasta", ""),
        })
        return contexto


@requiere_roles("Almacenero")
def nuevo_ajuste(request):
    form = AjusteInventarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            movimiento = ajustar_inventario(
                lote_id=form.cleaned_data["lote"].pk, tipo=form.cleaned_data["tipo"],
                cantidad=form.cleaned_data["cantidad"], motivo=form.cleaned_data["motivo"],
                usuario=request.user, direccion_ip=obtener_ip(request),
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "El ajuste de stock fue registrado en el kardex.")
            return redirect("inventario:movimientos")
    return render(request, "modulo/formulario.html", {
        "titulo": "Ajustar stock", "subtitulo": "Registra un ajuste con motivo y lote asociado.",
        "form": form, "url_cancelar": reverse_lazy("inventario:stock"),
    })


@requiere_roles("Almacenero")
def nueva_transferencia(request):
    form = TransferenciaStockForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            transferir_stock(
                lote_id=form.cleaned_data["lote"].pk,
                almacen_destino_id=form.cleaned_data["almacen_destino"].pk,
                cantidad=form.cleaned_data["cantidad"], motivo=form.cleaned_data["motivo"],
                usuario=request.user, direccion_ip=obtener_ip(request),
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "La transferencia quedó registrada con salida y entrada en el kardex.")
            return redirect("inventario:movimientos")
    return render(request, "modulo/formulario.html", {
        "titulo": "Transferir stock", "subtitulo": "Traslada un lote disponible a otro almacén.",
        "form": form, "url_cancelar": reverse_lazy("inventario:stock"),
    })


@requiere_roles("Vendedor", "Almacenero")
def lote_detalle(request, pk):
    lote = get_object_or_404(Lote.objects.select_related("producto", "almacen"), pk=pk)
    estado_siguiente = "CUARENTENA" if lote.estado == "DISPONIBLE" else "DISPONIBLE"
    form = EstadoLoteForm(initial={"estado": estado_siguiente})
    return render(request, "inventario/lote_detalle.html", {
        "titulo": f"Lote {lote.codigo_lote}", "lote": lote, "form": form,
        "url_cancelar": reverse_lazy("inventario:lotes"),
    })


@requiere_roles("Almacenero")
def actualizar_estado_lote(request, pk):
    if request.method != "POST":
        return redirect("inventario:lote_detalle", pk=pk)
    lote = get_object_or_404(Lote, pk=pk)
    form = EstadoLoteForm(request.POST)
    if form.is_valid():
        try:
            cambiar_estado_lote(
                lote_id=lote.pk, estado=form.cleaned_data["estado"],
                usuario=request.user, direccion_ip=obtener_ip(request),
            )
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, "El estado del lote fue actualizado.")
    else:
        messages.error(request, "Selecciona un estado válido para el lote.")
    return redirect("inventario:lote_detalle", pk=pk)


# ==========================================
# CRUD ALMACENES
# ==========================================

class AlmacenListView(BaseListView):
    model = Almacen
    titulo = "Almacenes y Ubicaciones"
    subtitulo = "Controla los espacios físicos de almacenamiento y tiendas."
    search_fields = ["nombre", "ubicacion", "descripcion"]
    columnas = [
        {"campo": "nombre", "titulo": "Nombre", "destacado": True},
        {"campo": "ubicacion", "titulo": "Ubicación"},
        {"campo": "descripcion", "titulo": "Descripción"},
        {"campo": "estado", "titulo": "Estado", "tipo": "badge"},
    ]
    url_crear = "inventario:almacen_crear"
    url_editar = "inventario:almacen_editar"
    url_eliminar = "inventario:almacen_eliminar"
    roles_permitidos = ["Administrador", "Almacenero"]
    roles_crear = ["Administrador"]
    roles_editar = ["Administrador"]


class AlmacenCreateView(BaseCreateView):
    model = Almacen
    form_class = AlmacenForm
    titulo = "Nuevo Almacén"
    subtitulo = "Registra una nueva bodega o punto de venta."
    success_url = reverse_lazy("inventario:almacen_listado")
    roles_permitidos = ["Administrador"]


class AlmacenUpdateView(BaseUpdateView):
    model = Almacen
    form_class = AlmacenForm
    titulo = "Editar Almacén"
    subtitulo = "Modifica los datos del almacén seleccionado."
    success_url = reverse_lazy("inventario:almacen_listado")
    roles_permitidos = ["Administrador"]


class AlmacenDeleteView(BaseDeleteView):
    model = Almacen
    success_url = reverse_lazy("inventario:almacen_listado")
    roles_permitidos = ["Administrador"]
