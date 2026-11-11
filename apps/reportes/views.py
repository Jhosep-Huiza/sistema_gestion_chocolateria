from django.contrib.auth.decorators import login_required
from apps.core.mixins import requiere_roles
from django.db.models import Sum
from django.shortcuts import render
from apps.productos.models import Producto
from apps.clientes.models import Cliente
from apps.ventas.models import Venta
from apps.compras.models import Compra
from apps.inventario.models import Inventario, Lote
from django.utils import timezone

@login_required
def dashboard(request):
    hoy = timezone.localdate()
    ventas_hoy = Venta.objects.filter(fecha_venta__date=hoy, estado__in=["PAGADA","PARCIAL"]).aggregate(total=Sum("total"))["total"] or 0
    context = {
        "productos_count": Producto.objects.filter(estado=True).count(),
        "clientes_count": Cliente.objects.filter(estado=True).count(),
        "ventas_hoy": ventas_hoy,
        "compras_pendientes": Compra.objects.filter(estado="PENDIENTE").count(),
        "stock_bajo": Inventario.objects.filter(stock_actual__lte=0).count(),
        "lotes_por_vencer": Lote.objects.filter(fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=hoy + timezone.timedelta(days=30), cantidad_disponible__gt=0).count(),
        "ventas_recientes": Venta.objects.select_related("cliente","usuario").order_by("-fecha_venta")[:7],
    }
    return render(request, "dashboard.html", context)

@requiere_roles("Administrador")
def inicio(request):
    return render(request, "modulo/en_construccion.html", {"titulo": "Reportes y Estadísticas"})
