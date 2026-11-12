from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.mixins import requiere_roles
from apps.usuarios.services import obtener_ip
from .forms import AperturaCajaForm, CierreCajaForm, MovimientoCajaForm
from .models import Caja
from .services import abrir_caja, cerrar_caja, registrar_movimiento_caja


def _cajas_usuario(request):
    cajas = Caja.objects.select_related("usuario")
    if not request.user.is_superuser and not request.user.es_administrador:
        cajas = cajas.filter(usuario=request.user)
    return cajas


@requiere_roles("Cajero")
def inicio(request):
    caja_abierta = _cajas_usuario(request).filter(usuario=request.user, estado="ABIERTA").first()
    apertura_form = AperturaCajaForm()
    movimiento_form = MovimientoCajaForm()
    if request.method == "POST" and request.POST.get("accion") == "abrir":
        apertura_form = AperturaCajaForm(request.POST)
        if apertura_form.is_valid():
            try:
                abrir_caja(usuario=request.user, monto_inicial=apertura_form.cleaned_data["monto_inicial"])
                messages.success(request, "Caja abierta correctamente.")
                return redirect("caja:inicio")
            except ValidationError as error:
                apertura_form.add_error(None, error)
    return render(request, "caja/inicio.html", {
        "caja_abierta": caja_abierta,
        "apertura_form": apertura_form,
        "movimiento_form": movimiento_form,
        "cajas": _cajas_usuario(request).order_by("-fecha_apertura")[:20],
    })


@requiere_roles("Cajero")
@require_POST
def movimiento(request, pk):
    caja = get_object_or_404(_cajas_usuario(request), pk=pk)
    form = MovimientoCajaForm(request.POST)
    if form.is_valid():
        try:
            registrar_movimiento_caja(
                caja_id=caja.pk, usuario=request.user, tipo=form.cleaned_data["tipo"],
                concepto=form.cleaned_data["concepto"], monto=form.cleaned_data["monto"],
            )
            messages.success(request, "Movimiento registrado.")
        except ValidationError as error:
            messages.error(request, error)
    else:
        messages.error(request, "Revisa los datos del movimiento.")
    return redirect("caja:inicio")


@requiere_roles("Cajero")
@require_POST
def cerrar(request, pk):
    caja = get_object_or_404(_cajas_usuario(request), pk=pk)
    form = CierreCajaForm(request.POST)
    if form.is_valid():
        try:
            cerrar_caja(
                caja_id=caja.pk, usuario=request.user,
                monto_final=form.cleaned_data["monto_final"], direccion_ip=obtener_ip(request),
            )
            messages.success(request, "Caja cerrada. El resumen está listo para imprimir.")
            return redirect("caja:resumen", pk=caja.pk)
        except ValidationError as error:
            messages.error(request, error)
    else:
        messages.error(request, "Ingresa el monto contado correctamente.")
    return redirect("caja:inicio")


@requiere_roles("Cajero")
def resumen(request, pk):
    caja = get_object_or_404(_cajas_usuario(request), pk=pk, estado="CERRADA")
    return render(request, "caja/resumen.html", {"caja": caja, "movimientos": caja.movimientos.select_related("usuario").all()})
