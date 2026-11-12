from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.mixins import requiere_roles
from apps.usuarios.services import obtener_ip
from .forms import GastoForm, PeriodoFinancieroForm
from .models import Gasto
from .services import actualizar_gasto, anular_gasto, registrar_gasto, resumen_financiero


@requiere_roles("Administrador")
def inicio(request):
    datos = {"ingresos_ventas": 0, "egresos_compras": 0, "egresos_gastos": 0,
             "egresos": 0, "utilidad": 0, "por_cobrar": 0, "por_pagar": 0}
    hoy = timezone.localdate()
    if request.GET:
        form = PeriodoFinancieroForm(request.GET)
        if form.is_valid():
            datos = resumen_financiero(desde=form.cleaned_data["desde"], hasta=form.cleaned_data["hasta"])
    else:
        desde = hoy.replace(day=1)
        form = PeriodoFinancieroForm(initial={"desde": desde, "hasta": hoy})
        datos = resumen_financiero(desde=desde, hasta=hoy)
    return render(request, "finanzas/inicio.html", {"form": form, "resumen": datos})


@requiere_roles("Administrador")
def gastos(request):
    consulta = request.GET.get("q", "").strip()
    registros = Gasto.objects.select_related("usuario", "caja").order_by("-fecha_gasto")
    if consulta:
        registros = registros.filter(
            Q(categoria__icontains=consulta) | Q(descripcion__icontains=consulta)
            | Q(usuario__username__icontains=consulta)
        )
    pagina = Paginator(registros, 20).get_page(request.GET.get("page"))
    return render(request, "finanzas/gastos.html", {
        "gastos": pagina.object_list, "pagina": pagina, "q": consulta,
    })


@requiere_roles("Administrador")
def crear_gasto(request):
    form = GastoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        try:
            gasto = registrar_gasto(
                usuario=request.user, categoria=datos["categoria"], descripcion=datos["descripcion"],
                monto=datos["monto"], fecha_gasto=datos["fecha_gasto"],
                comprobante=datos["comprobante"], es_efectivo=datos["es_efectivo"],
                caja_id=datos["caja"].pk if datos["caja"] else None,
            )
            messages.success(request, "Gasto registrado correctamente.")
            return redirect("finanzas:gastos")
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, "finanzas/gasto_formulario.html", {"form": form, "titulo": "Registrar gasto"})


@requiere_roles("Administrador")
def editar_gasto(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk)
    form = GastoForm(request.POST or None, request.FILES or None, instance=gasto)
    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        try:
            actualizar_gasto(
                gasto_id=gasto.pk, usuario=request.user, categoria=datos["categoria"],
                descripcion=datos["descripcion"], monto=datos["monto"],
                fecha_gasto=datos["fecha_gasto"], comprobante=datos["comprobante"],
                es_efectivo=datos["es_efectivo"], caja_id=datos["caja"].pk if datos["caja"] else None,
            )
            messages.success(request, "Gasto actualizado y su movimiento de caja ajustado.")
            return redirect("finanzas:gastos")
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, "finanzas/gasto_formulario.html", {"form": form, "titulo": "Editar gasto", "gasto": gasto})


@requiere_roles("Administrador")
@require_POST
def anular(request, pk):
    try:
        anular_gasto(
            gasto_id=pk, usuario=request.user, motivo=request.POST.get("motivo", ""),
            direccion_ip=obtener_ip(request),
        )
        messages.success(request, "Gasto anulado y reversado.")
    except ValidationError as error:
        messages.error(request, error)
    return redirect("finanzas:gastos")
