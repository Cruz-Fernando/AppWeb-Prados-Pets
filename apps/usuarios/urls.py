from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="usuarios/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("panel/", views.dashboard, name="dashboard"),

    # HU02 — gestión de roles
    path("roles/", views.roles_lista, name="roles_lista"),
    path("roles/nuevo/", views.rol_nuevo, name="rol_nuevo"),
    path("roles/<int:pk>/editar/", views.rol_editar, name="rol_editar"),
    path("roles/<int:pk>/eliminar/", views.rol_eliminar, name="rol_eliminar"),

    # HU02 — alta de personal y asignación de rol/estado
    path("usuarios/", views.usuarios_lista, name="usuarios_lista"),
    path("usuarios/nuevo/", views.usuario_nuevo, name="usuario_nuevo"),
    path("usuarios/<int:pk>/editar/", views.usuario_editar, name="usuario_editar"),
    path("usuarios/<int:pk>/eliminar/", views.usuario_eliminar, name="usuario_eliminar"),
]
