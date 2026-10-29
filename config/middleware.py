"""
Middleware de seguridad de AppWeb Prados Pets.

LoginRequeridoMiddleware obliga a iniciar sesión para acceder a CUALQUIER
ruta del sitio (presente o futura), salvo la pantalla de login, los archivos
estáticos y el admin de Django (que tiene su propio login). Así nadie puede
saltarse la seguridad escribiendo una URL a mano, aunque a una vista se le
olvide el decorador @login_required.
"""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import resolve_url


class LoginRequeridoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        ruta = request.path_info
        login_url = resolve_url(settings.LOGIN_URL)

        rutas_libres = (
            login_url,
            "/admin/",  # el admin de Django gestiona su propio login
            "/" + settings.STATIC_URL.lstrip("/"),
        )
        if ruta.startswith(rutas_libres):
            return self.get_response(request)

        return redirect_to_login(request.get_full_path(), login_url)
