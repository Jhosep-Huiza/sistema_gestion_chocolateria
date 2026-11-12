from decimal import Decimal
from datetime import datetime, time, timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from apps.caja.models import Caja
from apps.compras.models import Compra
from apps.inventario.models import Inventario, Lote
from apps.ventas.models import DetalleVenta, Venta


def _filtrar_periodo(queryset, campo, desde, hasta, *, campo_fecha=True):
    """Filtra fechas con límites inclusivos/exclusivos sin depender de CONVERT_TZ."""
    if campo_fecha:
        if desde:
            inicio = timezone.make_aware(datetime.combine(desde, time.min), timezone.get_current_timezone())
            queryset = queryset.filter(**{f"{campo}__gte": inicio})
        if hasta:
            fin = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), timezone.get_current_timezone())
            queryset = queryset.filter(**{f"{campo}__lt": fin})
    else:
        if desde:
            queryset = queryset.filter(**{f"{campo}__gte": desde})
        if hasta:
            queryset = queryset.filter(**{f"{campo}__lte": hasta})
    return queryset


def construir_reporte(*, clave, desde=None, hasta=None, vendedor_id=None, producto_id=None):
    """Devuelve encabezados y filas para la vista web y las exportaciones."""
    if clave == "ventas":
        detalles = DetalleVenta.objects.filter(venta__estado__in=["PAGADA", "PARCIAL", "PENDIENTE"])
        detalles = _filtrar_periodo(detalles, "venta__fecha_venta", desde, hasta)
        if vendedor_id:
            detalles = detalles.filter(venta__usuario_id=vendedor_id)
        if producto_id:
            detalles = detalles.filter(producto_id=producto_id)
        registros = detalles.values(
            "venta__usuario__username", "producto__codigo", "producto__nombre",
        ).annotate(cantidad=Sum("cantidad"), importe=Sum("subtotal")).order_by(
            "venta__usuario__username", "producto__nombre",
        )
        return "Ventas por vendedor y producto", ["Vendedor", "Código", "Producto", "Cantidad", "Importe de líneas"], [
            [fila["venta__usuario__username"], fila["producto__codigo"], fila["producto__nombre"], fila["cantidad"], fila["importe"]]
            for fila in registros
        ]

    if clave == "compras":
        compras = Compra.objects.exclude(estado="ANULADA").select_related("proveedor")
        compras = _filtrar_periodo(compras, "fecha_compra", desde, hasta)
        registros = compras.values("proveedor__razon_social", "proveedor__ruc").annotate(
            documentos=Count("pk"), importe=Sum("total"),
        ).order_by("proveedor__razon_social")
        return "Compras por proveedor", ["Proveedor", "RUC", "Documentos", "Total"], [
            [fila["proveedor__razon_social"], fila["proveedor__ruc"], fila["documentos"], fila["importe"]]
            for fila in registros
        ]

    if clave == "inventario":
        filas = Inventario.objects.select_related("producto", "almacen").order_by("producto__nombre", "almacen__nombre")
        salida = []
        for fila in filas:
            costo = fila.producto.precio_compra_referencial
            salida.append([
                fila.producto.codigo, fila.producto.nombre, fila.almacen.nombre,
                fila.stock_actual, fila.stock_reservado,
                fila.stock_actual - fila.stock_reservado, costo, fila.stock_actual * costo,
            ])
        return "Inventario valorizado", ["Código", "Producto", "Almacén", "Stock actual", "Reservado", "Disponible", "Costo unitario", "Valor"], salida

    if clave == "lotes":
        lotes = Lote.objects.select_related("producto", "almacen").filter(
            cantidad_disponible__gt=0, estado__in=["DISPONIBLE", "CUARENTENA"],
        )
        lotes = _filtrar_periodo(lotes, "fecha_vencimiento", desde, hasta, campo_fecha=False)
        lotes = lotes.order_by("fecha_vencimiento", "producto__nombre")
        return "Lotes por vencer", ["Producto", "Lote", "Almacén", "Vencimiento", "Cantidad", "Estado"], [
            [lote.producto.nombre, lote.codigo_lote, lote.almacen.nombre,
             lote.fecha_vencimiento, lote.cantidad_disponible, lote.get_estado_display()]
            for lote in lotes
        ]

    if clave == "mas_vendidos":
        detalles = DetalleVenta.objects.filter(venta__estado__in=["PAGADA", "PARCIAL", "PENDIENTE"])
        detalles = _filtrar_periodo(detalles, "venta__fecha_venta", desde, hasta)
        if producto_id:
            detalles = detalles.filter(producto_id=producto_id)
        registros = detalles.values("producto__codigo", "producto__nombre").annotate(
            cantidad=Sum("cantidad"), importe=Sum("subtotal"),
        ).order_by("-cantidad", "producto__nombre")
        return "Productos más vendidos", ["Código", "Producto", "Unidades", "Importe de líneas"], [
            [fila["producto__codigo"], fila["producto__nombre"], fila["cantidad"], fila["importe"]]
            for fila in registros
        ]

    if clave == "cajas":
        cajas = Caja.objects.select_related("usuario").order_by("-fecha_apertura")
        cajas = _filtrar_periodo(cajas, "fecha_apertura", desde, hasta)
        return "Estado de caja", ["Caja", "Usuario", "Apertura", "Cierre", "Estado", "Inicial", "Esperado", "Contado", "Diferencia"], [
            [caja.pk, caja.usuario.get_full_name() or caja.usuario.username,
             caja.fecha_apertura, caja.fecha_cierre, caja.get_estado_display(), caja.monto_inicial,
             caja.monto_esperado, caja.monto_final, caja.diferencia]
            for caja in cajas
        ]

    raise ValueError("El reporte solicitado no existe.")
