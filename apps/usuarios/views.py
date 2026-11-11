from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next")
            if not next_url or not url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                next_url = "dashboard"
            return redirect(next_url)
        messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, "auth/login.html")

@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")
