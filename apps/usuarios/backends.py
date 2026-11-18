from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UsuarioConRolBackend(ModelBackend):
    """ModelBackend que trae el rol en la misma consulta que el usuario.

    Cada página lee ``request.user.id_rol`` (menú lateral y ``rol_requerido``);
    sin esto, Django hacía una consulta aparte para el rol en cada petición.
    """

    def get_user(self, user_id):
        Usuario = get_user_model()
        try:
            usuario = Usuario._default_manager.select_related("id_rol").get(pk=user_id)
        except Usuario.DoesNotExist:
            return None
        return usuario if self.user_can_authenticate(usuario) else None
