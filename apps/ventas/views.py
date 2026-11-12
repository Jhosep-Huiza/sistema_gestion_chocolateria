import json
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import ListView
from apps.core.mixins import requiere_roles
from apps.core.views import BaseListView
from apps.caja.models import Caja
from apps.clientes.models import Cliente
from apps.configuracion.models import MetodoPago, Configuracion
from apps.inventario.models import Almacen, Inventario, Lote
from apps.productos.models import Producto
from apps.usuarios.services import obtener_ip
from .forms import PagoVentaForm, AnularVentaForm
from .models import Venta
from .services import registrar_venta, registrar_pago_venta, anular_venta


def _contexto_pos(request, almacen_id=None):
    almacenes = Almacen.objects.filter(estado=True).order_by("nombre")
    almacen = almacenes.filter(pk=almacen_id).first() if almacen_id else almacenes.first()
    caja = Caja.objects.filter(usuario=request.user, estado="ABIERTA").first()
    productos = list(Producto.objects.filter(estado=True).select_related("categoria").order_by("nombre"))
    stock_por_producto = {}
    lotes_por_producto = {}
    cantidad_lotes = {}
    if almacen:
        filas = Inventario.objects.filter(almacen=almacen).select_related("producto")
        for fila in filas:
            stock_por_producto[fila.producto_id] = max(
                fila.stock_actual - fila.stock_reservado, Decimal("0.000"),
            )
        lotes = Lote.objects.filter(
            almacen=almacen, estado="DISPONIBLE", cantidad_disponible__gt=0,
            fecha_vencimiento__gte=timezone.localdate(),
        ).order_by("fecha_vencimiento", "pk")
        for lote in lotes:
            lotes_por_producto.setdefault(lote.producto_id, []).append(
                f"{lote.codigo_lote} ({lote.cantidad_disponible})"
            )
            cantidad_lotes[lote.producto_id] = cantidad_lotes.get(lote.producto_id, Decimal("0.000")) + lote.cantidad_disponible
    for producto in productos:
        producto.stock_disponible = min(
            stock_por_producto.get(producto.pk, Decimal("0.000")),
            cantidad_lotes.get(producto.pk, Decimal("0.000")),
        )
        producto.lotes_fefo = " → ".join(lotes_por_producto.get(producto.pk, []))
    configuracion = Configuracion.objects.order_by("pk").first()
    igv_porcentaje = configuracion.porcentaje_igv if configuracion else Decimal("18.00")
    return {
        "productos": productos,
        "clientes": Cliente.objects.filter(estado=True).order_by("nombres"),
        "almacenes": almacenes,
        "almacen_seleccionado": almacen.pk if almacen else "",
        "caja_abierta": caja,
        "metodos_pago": MetodoPago.objects.filter(estado=True).order_by("nombre"),
        "igv_porcentaje": igv_porcentaje,
        "ventas_hoy": Venta.objects.filter(
            usuario=request.user, fecha_venta__date=timezone.localdate(),
        ).exclude(estado="ANULADA").count(),
        "payload_carrito": request.POST.get("carrito", "[]"),
        "payload_pagos": request.POST.get("pagos", "[]"),
        "cliente_seleccionado": request.POST.get("cliente", ""),
        "descuento_global": request.POST.get("descuento_global", "0.00"),
    }


@requiere_roles("Vendedor", "Cajero")
def inicio(request):
    contexto = _contexto_pos(request, request.POST.get("almacen") or request.GET.get("almacen"))
    if request.method == "POST":
        try:
            lineas = json.loads(request.POST.get("carrito", "[]"))
            pagos = json.loads(request.POST.get("pagos", "[]"))
            if not isinstance(lineas, list) or not isinstance(pagos, list):
                raise ValueError
            if request.POST.get("modo_pago") == "PENDIENTE":
                pagos = []
            elif not pagos:
                raise ValidationError("Agrega un pago o elige registrar la venta como pendiente.")
            cliente_id = request.POST.get("cliente") or None
            cliente = Cliente.objects.filter(pk=cliente_id, estado=True).first() if cliente_id else None
            if cliente_id and cliente is None:
                raise ValidationError("Selecciona un cliente activo.")
            descuento_global = Decimal(request.POST.get("descuento_global") or "0")
            venta = registrar_venta(
                usuario=request.user,
                almacen_id=request.POST.get("almacen"),
                lineas=lineas,
                cliente=cliente,
                caja=contexto["caja_abierta"],
                tipo_comprobante=request.POST.get("tipo_comprobante", "TICKET"),
                descuento=descuento_global,
                pagos=pagos,
                direccion_ip=obtener_ip(request),
            )
        except (json.JSONDecodeError, ValueError, InvalidOperation):
            messages.error(request, "El carrito o los importes enviados no tienen un formato válido.")
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        except Almacen.DoesNotExist:
            messages.error(request, "Selecciona un almacén activo.")
        else:
            messages.success(request, f"Venta {venta.numero_venta} registrada correctamente.")
            return redirect("ventas:detalle", pk=venta.pk)
    contexto.update({
        "titulo": "Punto de venta",
        "subtitulo": "Busca productos, revisa FEFO y registra uno o varios medios de pago.",
        "url_cancelar": reverse_lazy("dashboard"),
    })
    return render(request, "ventas/pos.html", contexto)


class VentaListView(BaseListView):
    model = Venta
    titulo = "Historial de ventas"
    subtitulo = "Busca comprobantes y revisa el estado de pago de cada venta."
    search_fields = ["numero_venta", "numero_comprobante", "cliente__nombres", "cliente__numero_documento"]
    columnas = [
        {"campo": "numero_venta", "titulo": "Venta", "destacado": True},
        {"campo": "fecha_venta", "titulo": "Fecha"},
        {"campo": "cliente.nombres", "titulo": "Cliente"},
        {"campo": "usuario.username", "titulo": "Vendedor"},
        {"campo": "total", "titulo": "Total", "tipo": "moneda"},
        {"campo": "estado", "titulo": "Estado", "tipo": "badge"},
    ]
    url_crear = "ventas:inicio"
    url_ver = "ventas:detalle"
    roles_permitidos = ["Administrador", "Vendedor", "Cajero"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("cliente", "usuario", "caja")
        estado = self.request.GET.get("estado", "")
        cliente = self.request.GET.get("cliente", "")
        desde = parse_date(self.request.GET.get("desde", ""))
        hasta = parse_date(self.request.GET.get("hasta", ""))
        if estado in {opcion[0] for opcion in Venta.ESTADOS}:
            qs = qs.filter(estado=estado)
        if cliente.isdigit():
            qs = qs.filter(cliente_id=int(cliente))
        if desde:
            qs = qs.filter(fecha_venta__date__gte=desde)
        if hasta:
            qs = qs.filter(fecha_venta__date__lte=hasta)
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update({
            "filtro_ventas": True,
            "clientes": Cliente.objects.filter(estado=True).order_by("nombres"),
            "estados_venta": Venta.ESTADOS,
            "estado_filtro": self.request.GET.get("estado", ""),
            "cliente_filtro": self.request.GET.get("cliente", ""),
            "desde": self.request.GET.get("desde", ""),
            "hasta": self.request.GET.get("hasta", ""),
        })
        return contexto


@requiere_roles("Vendedor", "Cajero")
def detalle(request, pk):
    venta = get_object_or_404(
        Venta.objects.select_related("cliente", "usuario", "caja").prefetch_related(
            "detalles__producto", "detalles__lote__almacen", "pagos__metodo_pago", "pagos__usuario",
        ), pk=pk,
    )
    contexto = {
        "titulo": f"Venta {venta.numero_venta}", "venta": venta,
        "saldo": venta.saldo_pendiente,
        "puede_pagar": venta.estado not in {"ANULADA", "PAGADA"} and venta.saldo_pendiente > 0,
        "form_pago": PagoVentaForm(), "form_anular": AnularVentaForm(),
        "url_cancelar": reverse_lazy("ventas:historial"),
    }
    return render(request, "ventas/detalle.html", contexto)


@requiere_roles("Vendedor", "Cajero")
def registrar_pago(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    form = PagoVentaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            registrar_pago_venta(
                venta_id=venta.pk, usuario=request.user,
                metodo_pago_id=form.cleaned_data["metodo_pago"].pk,
                monto=form.cleaned_data["monto"], referencia=form.cleaned_data["referencia"],
                caja=Caja.objects.filter(usuario=request.user, estado="ABIERTA").first(),
                direccion_ip=obtener_ip(request),
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "El pago de la venta quedó registrado.")
            return redirect("ventas:detalle", pk=venta.pk)
    return render(request, "ventas/pago.html", {
        "titulo": f"Registrar pago · {venta.numero_venta}", "venta": venta,
        "saldo": venta.saldo_pendiente, "form": form,
        "url_cancelar": reverse_lazy("ventas:detalle", kwargs={"pk": venta.pk}),
    })


@requiere_roles("Administrador")
def anular(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    if request.method != "POST":
        return redirect("ventas:detalle", pk=pk)
    form = AnularVentaForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Debes indicar un motivo válido para anular la venta.")
        return redirect("ventas:detalle", pk=pk)
    try:
        anular_venta(
            venta_id=venta.pk, usuario=request.user,
            motivo=form.cleaned_data["motivo"], direccion_ip=obtener_ip(request),
        )
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, f"La venta {venta.numero_venta} fue anulada y sus movimientos compensados.")
    return redirect("ventas:detalle", pk=pk)


@requiere_roles("Vendedor", "Cajero")
def comprobante(request, pk):
    venta = get_object_or_404(
        Venta.objects.select_related("cliente", "usuario").prefetch_related(
            "detalles__producto", "pagos__metodo_pago",
        ), pk=pk,
    )
    return render(request, "ventas/comprobante.html", {"venta": venta})
