from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Proveedor

@login_required
def listado(request):
    q = request.GET.get("q", "").strip()
    registros = Proveedor.objects.all()
    if q:
        campos = [f.name for f in Proveedor._meta.fields if getattr(f, "get_internal_type", lambda: "")() in ("CharField","TextField","EmailField")]
        from django.db.models import Q
        filtro = Q()
        for campo in campos: filtro |= Q(**{f"{campo}__icontains": q})
        registros = registros.filter(filtro)
    return render(request, "modulo/listado.html", {"titulo": "Proveedores", "registros": registros, "q": q})

@login_required
def crear(request):
    if request.method == "POST":
        from .forms import ProveedorForm
        form = ProveedorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro creado correctamente.")
            return redirect("proveedores_listado")
    else:
        from .forms import ProveedorForm
        form = ProveedorForm()
    return render(request, "modulo/formulario.html", {"titulo": "Nuevo registro", "form": form})

@login_required
def editar(request, pk):
    objeto = get_object_or_404(Proveedor, pk=pk)
    from .forms import ProveedorForm
    form = ProveedorForm(request.POST or None, request.FILES or None, instance=objeto)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Registro actualizado correctamente.")
        return redirect("proveedores_listado")
    return render(request, "modulo/formulario.html", {"titulo": "Editar registro", "form": form})

@login_required
def eliminar(request, pk):
    objeto = get_object_or_404(Proveedor, pk=pk)
    if request.method == "POST":
        objeto.delete()
        messages.success(request, "Registro eliminado correctamente.")
        return redirect("proveedores_listado")
    return render(request, "modulo/confirmar_eliminar.html", {"objeto": objeto})
