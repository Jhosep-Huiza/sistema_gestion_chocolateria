from django.contrib import messages
from django.core.exceptions import ValidationError
from django.forms import formset_factory
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.mixins import requiere_roles
from apps.usuarios.services import obtener_ip
from apps.ventas.models import Venta
from .forms import DetalleDevolucionForm, RechazoDevolucionForm, SolicitudDevolucionForm
from .models import Devolucion
from .services import aprobar_devolucion, rechazar_devolucion, solicitar_devolucion

DetalleFormSet = formset_factory(DetalleDevolucionForm, extra=0)


@requiere_roles("Vendedor")
def inicio(request):
    consulta = request.GET.get("q", "").strip()
    registros = Devolucion.objects.select_related("venta", "usuario").prefetch_related("detalles").order_by("-fecha_devolucion")
    if consulta:
        registros = registros.filter(
            Q(venta__numero_venta__icontains=consulta)
            | Q(usuario__username__icontains=consulta)
            | Q(motivo__icontains=consulta)
        )
    pagina = Paginator(registros, 20).get_page(request.GET.get("page"))
    rol = getattr(getattr(request.user, "rol", None), "nombre", "")
    return render(request, "devoluciones/listado.html", {
        "devoluciones": pagina.object_list,
        "pagina": pagina,
        "q": consulta,
        "puede_resolver": request.user.is_superuser or rol == "Administrador",
    })


@requiere_roles("Vendedor")
def crear(request):
    venta_id = request.POST.get("venta") or request.GET.get("venta")
    venta = Venta.objects.filter(pk=venta_id).first() if venta_id else None
    form = SolicitudDevolucionForm(request.POST or None, initial={"venta": venta.pk if venta else None})
    if request.method == "POST" and form.is_valid():
        venta = form.cleaned_data["venta"]
    initial = [{"detalle_venta_id": fila.pk} for fila in venta.detalles.select_related("producto").all()] if venta else []
    formset = DetalleFormSet(request.POST or None, initial=initial, prefix="lineas")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        detalles = [
            {"detalle_venta_id": fila.cleaned_data["detalle_venta_id"],
             "cantidad": fila.cleaned_data["cantidad"],
             "estado_producto": fila.cleaned_data["estado_producto"]}
            for fila in formset if fila.cleaned_data and fila.cleaned_data.get("cantidad")
        ]
        try:
            devolucion = solicitar_devolucion(
                venta_id=form.cleaned_data["venta"].pk, usuario=request.user,
                motivo=form.cleaned_data["motivo"], tipo_reembolso=form.cleaned_data["tipo_reembolso"],
                detalles=detalles, reembolso_efectivo=form.cleaned_data["efectivo"],
            )
            messages.success(request, "Solicitud de devolución enviada para aprobación.")
            return redirect("devoluciones:listado")
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, "devoluciones/formulario.html", {
        "form": form, "formset": formset, "venta": venta,
    })


@requiere_roles("Administrador")
@require_POST
def aprobar(request, pk):
    devolucion = get_object_or_404(Devolucion, pk=pk)
    efectivo = devolucion.reembolso_efectivo
    try:
        aprobar_devolucion(
            devolucion_id=pk, usuario=request.user, efectivo=efectivo,
            direccion_ip=obtener_ip(request),
        )
        messages.success(request, "Devolución aprobada.")
    except ValidationError as error:
        messages.error(request, error)
    return redirect("devoluciones:listado")


@requiere_roles("Administrador")
@require_POST
def rechazar(request, pk):
    form = RechazoDevolucionForm(request.POST)
    if form.is_valid():
        try:
            rechazar_devolucion(
                devolucion_id=pk, usuario=request.user,
                motivo=form.cleaned_data["motivo"], direccion_ip=obtener_ip(request),
            )
            messages.success(request, "Solicitud rechazada.")
        except ValidationError as error:
            messages.error(request, error)
    else:
        messages.error(request, "El motivo de rechazo no es válido.")
    return redirect("devoluciones:listado")
