from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from apps.core.mixins import requiere_roles
from apps.core.views import BaseListView
from apps.inventario.models import Almacen
from apps.proveedores.models import Proveedor
from .forms import CompraCabeceraForm, DetalleCompraFormSet, LoteRecepcionFormSet, PagoCompraForm
from .models import Compra
from .services import crear_compra, recibir_compra, registrar_pago_compra, anular_compra
from apps.usuarios.services import obtener_ip


class CompraListView(BaseListView):
    model = Compra
    titulo = "Compras y recepción"
    subtitulo = "Consulta documentos, saldos y estado de recepción de proveedores."
    search_fields = ["numero_compra", "numero_documento", "proveedor__razon_social"]
    columnas = [
        {"campo": "numero_compra", "titulo": "Compra", "destacado": True},
        {"campo": "proveedor.razon_social", "titulo": "Proveedor"},
        {"campo": "fecha_compra", "titulo": "Fecha"},
        {"campo": "total", "titulo": "Total", "tipo": "moneda"},
        {"campo": "estado", "titulo": "Recepción", "tipo": "badge"},
        {"campo": "estado_pago", "titulo": "Pago", "tipo": "badge"},
    ]
    url_crear = "compras:crear"
    url_ver = "compras:detalle"
    roles_permitidos = ["Administrador", "Almacenero"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("proveedor", "usuario")
        estado = self.request.GET.get("estado", "").strip()
        proveedor = self.request.GET.get("proveedor", "").strip()
        desde = self.request.GET.get("desde", "").strip()
        hasta = self.request.GET.get("hasta", "").strip()
        if estado in {opcion[0] for opcion in Compra.ESTADOS}:
            qs = qs.filter(estado=estado)
        if proveedor.isdigit():
            qs = qs.filter(proveedor_id=int(proveedor))
        if parse_date(desde):
            qs = qs.filter(fecha_compra__date__gte=parse_date(desde))
        if parse_date(hasta):
            qs = qs.filter(fecha_compra__date__lte=parse_date(hasta))
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update({
            "proveedores": Proveedor.objects.filter(estado=True).order_by("razon_social"),
            "estado_filtro": self.request.GET.get("estado", ""),
            "proveedor_filtro": self.request.GET.get("proveedor", ""),
            "desde": self.request.GET.get("desde", ""),
            "hasta": self.request.GET.get("hasta", ""),
            "estados_compra": Compra.ESTADOS,
        })
        return contexto


@requiere_roles("Almacenero")
def crear(request):
    encabezado = CompraCabeceraForm(request.POST or None)
    lineas = DetalleCompraFormSet(request.POST or None, prefix="lineas")
    if request.method == "POST" and encabezado.is_valid() and lineas.is_valid():
        datos_lineas = [
            {
                "producto_id": formulario.cleaned_data["producto"].pk,
                "cantidad": formulario.cleaned_data["cantidad"],
                "precio_unitario": formulario.cleaned_data["precio_unitario"],
                "descuento": formulario.cleaned_data["descuento"],
            }
            for formulario in lineas if formulario.cleaned_data and not formulario.cleaned_data.get("DELETE")
        ]
        try:
            compra = crear_compra(
                proveedor_id=encabezado.cleaned_data["proveedor"].pk,
                usuario=request.user,
                tipo_documento=encabezado.cleaned_data["tipo_documento"],
                numero_documento=encabezado.cleaned_data["numero_documento"],
                observaciones=encabezado.cleaned_data["observaciones"],
                lineas=datos_lineas,
            )
        except ValidationError as error:
            encabezado.add_error(None, error)
        else:
            messages.success(request, f"La compra {compra.numero_compra} fue creada.")
            return redirect("compras:detalle", pk=compra.pk)
    return render(request, "compras/nueva.html", {
        "titulo": "Nueva compra", "subtitulo": "Registra el documento y los productos del proveedor.",
        "form": encabezado, "lineas": lineas, "url_cancelar": reverse_lazy("compras:listado"),
    })


@requiere_roles("Almacenero")
def detalle(request, pk):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor", "usuario").prefetch_related(
            "detalles__producto", "detalles__lotes__almacen", "pagos__metodo_pago", "pagos__usuario",
        ), pk=pk,
    )
    pagado = sum((pago.monto for pago in compra.pagos.all() if pago.estado == "CONFIRMADO"), Decimal("0.00"))
    return render(request, "compras/detalle.html", {
        "titulo": f"Compra {compra.numero_compra}", "compra": compra,
        "pagado": pagado, "saldo": compra.total - pagado,
        "puede_pagar": compra.estado != "ANULADA" and pagado < compra.total,
        "url_cancelar": reverse_lazy("compras:listado"),
    })


@requiere_roles("Almacenero")
def recepcion(request, pk):
    compra = get_object_or_404(Compra.objects.prefetch_related("detalles__producto"), pk=pk)
    detalles = compra.detalles.select_related("producto").all()
    almacenes = Almacen.objects.filter(estado=True).order_by("nombre")
    if request.method == "POST":
        lotes_formset = LoteRecepcionFormSet(request.POST, prefix="lotes", form_kwargs={"detalles": detalles})
        almacen_form = almacenes.filter(pk=request.POST.get("almacen", "")).first()
        if lotes_formset.is_valid() and almacen_form:
            por_detalle = {}
            for formulario in lotes_formset:
                if not formulario.cleaned_data:
                    continue
                item = formulario.cleaned_data
                por_detalle.setdefault(item["detalle"].pk, []).append({
                    "codigo_lote": item["codigo_lote"],
                    "fecha_fabricacion": item["fecha_fabricacion"],
                    "fecha_vencimiento": item["fecha_vencimiento"],
                    "cantidad": item["cantidad"],
                })
            try:
                recibir_compra(
                    compra_id=compra.pk, almacen_id=almacen_form.pk, usuario=request.user,
                    lotes_por_detalle=por_detalle, direccion_ip=obtener_ip(request),
                )
            except ValidationError as error:
                lotes_formset._non_form_errors = lotes_formset.error_class(error.messages)
            else:
                messages.success(request, "La compra fue recibida y el stock quedó registrado por lote.")
                return redirect("compras:detalle", pk=compra.pk)
        elif not almacen_form:
            messages.error(request, "Selecciona un almacén activo para recibir la compra.")
    else:
        lotes_formset = LoteRecepcionFormSet(prefix="lotes", form_kwargs={"detalles": detalles})
    return render(request, "compras/recepcion.html", {
        "titulo": f"Recibir {compra.numero_compra}",
        "subtitulo": "Asigna cada cantidad recibida a uno o más lotes y a un almacén.",
        "compra": compra, "detalles": detalles, "lotes": lotes_formset,
        "almacenes": almacenes, "almacen_seleccionado": request.POST.get("almacen", ""),
        "url_cancelar": reverse_lazy("compras:detalle", kwargs={"pk": compra.pk}),
    })


@requiere_roles("Almacenero")
def registrar_pago(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    form = PagoCompraForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            registrar_pago_compra(
                compra_id=compra.pk, usuario=request.user,
                metodo_pago_id=form.cleaned_data["metodo_pago"].pk,
                monto=form.cleaned_data["monto"], referencia=form.cleaned_data["referencia"],
                direccion_ip=obtener_ip(request),
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "El pago quedó registrado.")
            return redirect("compras:detalle", pk=compra.pk)
    return render(request, "modulo/formulario.html", {
        "titulo": f"Registrar pago · {compra.numero_compra}",
        "subtitulo": f"Saldo pendiente: S/ {compra.saldo_pendiente:.2f}",
        "form": form, "url_cancelar": reverse_lazy("compras:detalle", kwargs={"pk": compra.pk}),
    })


@requiere_roles("Almacenero")
def anular(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    if request.method != "POST":
        return render(request, "modulo/confirmar_eliminar.html", {
            "objeto": compra, "titulo": "Anular compra",
            "url_cancelar": reverse_lazy("compras:detalle", kwargs={"pk": pk}),
            "accion_texto": "Anular compra",
        })
    try:
        compra = anular_compra(compra_id=pk, usuario=request.user, direccion_ip=obtener_ip(request))
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, f"La compra {compra.numero_compra} fue anulada.")
    return redirect("compras:detalle", pk=pk)
