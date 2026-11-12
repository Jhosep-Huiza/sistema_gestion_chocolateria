import csv
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from apps.clientes.models import Cliente
from apps.compras.models import Compra
from apps.core.mixins import requiere_roles
from apps.inventario.models import Inventario, Lote
from apps.productos.models import Producto
from apps.ventas.models import DetalleVenta, Venta
from .forms import FiltroReporteForm
from .services import construir_reporte

REPORTES = {
    "ventas": "Ventas por periodo, vendedor y producto",
    "compras": "Compras por proveedor",
    "inventario": "Inventario valorizado",
    "lotes": "Lotes por vencer",
    "mas_vendidos": "Productos más vendidos",
    "cajas": "Estado de caja",
}


@login_required
def dashboard(request):
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    ultimos_siete = [hoy - timedelta(days=offset) for offset in range(6, -1, -1)]
    ventas_validas = Venta.objects.exclude(estado="ANULADA")
    inicio_hoy = timezone.make_aware(datetime.combine(hoy, time.min), timezone.get_current_timezone())
    inicio_manana = inicio_hoy + timedelta(days=1)
    total_hoy = ventas_validas.filter(
        fecha_venta__gte=inicio_hoy, fecha_venta__lt=inicio_manana,
    ).aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    inicio_mes_dt = timezone.make_aware(datetime.combine(inicio_mes, time.min), timezone.get_current_timezone())
    ventas_mes = ventas_validas.filter(
        fecha_venta__gte=inicio_mes_dt, fecha_venta__lt=inicio_manana,
    )
    total_mes = ventas_mes.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    stock_bajo = Inventario.objects.filter(
        producto__estado=True, stock_actual__lte=F("producto__stock_minimo"),
    ).values("producto_id").distinct().count()
    lotes_por_vencer_qs = Lote.objects.select_related("producto", "almacen").filter(
        estado__in=["DISPONIBLE", "CUARENTENA"], cantidad_disponible__gt=0,
        fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=hoy + timedelta(days=30),
    ).order_by("fecha_vencimiento")
    inicio_semana = timezone.make_aware(datetime.combine(ultimos_siete[0], time.min), timezone.get_current_timezone())
    ventas_semanales = ventas_validas.filter(
        fecha_venta__gte=inicio_semana, fecha_venta__lt=inicio_manana,
    ).values_list("fecha_venta", "total")
    totales_dia = {}
    for fecha_venta, total in ventas_semanales:
        dia = timezone.localtime(fecha_venta).date() if timezone.is_aware(fecha_venta) else fecha_venta.date()
        totales_dia[dia] = totales_dia.get(dia, Decimal("0.00")) + total
    grafico = [{"fecha": dia, "etiqueta": dia.strftime("%d/%m"), "total": totales_dia.get(dia, Decimal("0.00"))}
               for dia in ultimos_siete]
    maximo = max((fila["total"] for fila in grafico), default=Decimal("0.00"))
    for indice, fila in enumerate(grafico):
        fila["alto_svg"] = int(fila["total"] * 120 / maximo) if maximo else 0
        fila["y_svg"] = 150 - fila["alto_svg"]
        fila["x_svg"] = 28 + indice * 64
        fila["etiqueta_x"] = fila["x_svg"] + 17
    top_productos = DetalleVenta.objects.filter(
        venta__estado__in=["PAGADA", "PARCIAL", "PENDIENTE"],
        venta__fecha_venta__gte=inicio_mes_dt, venta__fecha_venta__lt=inicio_manana,
    ).values("producto__codigo", "producto__nombre").annotate(
        cantidad=Sum("cantidad"), importe=Sum("subtotal"),
    ).order_by("-cantidad", "producto__nombre")[:5]
    contexto = {
        "productos_count": Producto.objects.filter(estado=True).count(),
        "clientes_count": Cliente.objects.filter(estado=True).count(),
        "ventas_hoy": total_hoy,
        "ventas_mes": total_mes,
        "ventas_mes_cantidad": ventas_mes.count(),
        "compras_pendientes": Compra.objects.filter(estado="PENDIENTE").count(),
        "stock_bajo": stock_bajo,
        "lotes_por_vencer": lotes_por_vencer_qs.count(),
        "lotes_alerta": lotes_por_vencer_qs[:5],
        "top_productos": top_productos,
        "ventas_ultimos_siete": grafico,
        "ventas_recientes": Venta.objects.select_related("cliente", "usuario").order_by("-fecha_venta")[:7],
    }
    return render(request, "dashboard.html", contexto)


@requiere_roles("Administrador")
def inicio(request):
    return render(request, "reportes/inicio.html", {"reportes": REPORTES})


def _parametros_reporte(request, clave):
    hoy = timezone.localdate()
    if clave == "lotes":
        predeterminados = {"desde": hoy, "hasta": hoy + timedelta(days=30)}
    elif clave == "inventario":
        predeterminados = {"desde": None, "hasta": None}
    else:
        predeterminados = {"desde": hoy.replace(day=1), "hasta": hoy}
    if request.GET:
        form = FiltroReporteForm(request.GET)
        if clave != "ventas":
            form.fields.pop("vendedor", None)
        if clave not in {"ventas", "mas_vendidos"}:
            form.fields.pop("producto", None)
        filtros = form.cleaned_data if form.is_valid() else None
        if filtros is not None:
            return form, filtros
        return form, None
    form = FiltroReporteForm(initial=predeterminados)
    if clave != "ventas":
        form.fields.pop("vendedor", None)
    if clave not in {"ventas", "mas_vendidos"}:
        form.fields.pop("producto", None)
    return form, {
        **predeterminados, "vendedor": None, "producto": None,
    }


@requiere_roles("Administrador")
@require_GET
def reporte(request, clave):
    if clave not in REPORTES:
        raise Http404("El reporte solicitado no existe.")
    form, filtros = _parametros_reporte(request, clave)
    titulo = REPORTES[clave]
    encabezados, filas = [], []
    if filtros is not None:
        titulo, encabezados, filas = construir_reporte(
            clave=clave, desde=filtros["desde"], hasta=filtros["hasta"],
            vendedor_id=filtros.get("vendedor").pk if filtros.get("vendedor") else None,
            producto_id=filtros.get("producto").pk if filtros.get("producto") else None,
        )
    return render(request, "reportes/reporte.html", {
        "clave": clave, "titulo": titulo, "form": form,
        "encabezados": encabezados, "filas": filas,
        "cantidad_registros": len(filas),
        "filtros_query": request.GET.urlencode(),
    })


@requiere_roles("Administrador")
@require_GET
def exportar(request, clave, formato):
    if clave not in REPORTES or formato not in {"csv", "excel"}:
        raise Http404("El reporte o formato solicitado no existe.")
    form, filtros = _parametros_reporte(request, clave)
    if filtros is None:
        return HttpResponse("Los filtros del reporte no son válidos.", status=400, content_type="text/plain; charset=utf-8")
    titulo, encabezados, filas = construir_reporte(
        clave=clave, desde=filtros["desde"], hasta=filtros["hasta"],
        vendedor_id=filtros.get("vendedor").pk if filtros.get("vendedor") else None,
        producto_id=filtros.get("producto").pk if filtros.get("producto") else None,
    )
    if formato == "csv":
        respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
        respuesta["Content-Disposition"] = f'attachment; filename="{clave}.csv"'
        respuesta.write("\ufeff")
        escritor = csv.writer(respuesta)
        escritor.writerow(encabezados)
        for fila in filas:
            escritor.writerow([_valor_csv(valor) for valor in fila])
        return respuesta

    libro = Workbook()
    hoja = libro.active
    hoja.title = titulo[:31]
    hoja.append(encabezados)
    for celda in hoja[1]:
        celda.font = Font(color="FFFFFF", bold=True)
        celda.fill = PatternFill("solid", fgColor="4A241C")
    for fila in filas:
        hoja.append([_valor_excel(valor) for valor in fila])
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = hoja.dimensions
    for columna in hoja.columns:
        letra = columna[0].column_letter
        ancho = max((len(str(celda.value or "")) for celda in columna), default=10)
        hoja.column_dimensions[letra].width = min(max(ancho + 2, 12), 40)
    archivo = BytesIO()
    libro.save(archivo)
    respuesta = HttpResponse(
        archivo.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    respuesta["Content-Disposition"] = f'attachment; filename="{clave}.xlsx"'
    return respuesta


def _valor_csv(valor):
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        texto = valor.isoformat(sep=" ")
    elif isinstance(valor, date):
        texto = valor.isoformat()
    else:
        texto = str(valor)
    if isinstance(valor, str) and texto.startswith(("=", "+", "-", "@")):
        return f"'{texto}"
    return texto


def _valor_excel(valor):
    if isinstance(valor, str) and valor.startswith(("=", "+", "-", "@")):
        return f"'{valor}"
    return valor
