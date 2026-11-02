from django.contrib import admin

from .models import ConsultaMedica, Hospitalizacion


@admin.register(ConsultaMedica)
class ConsultaMedicaAdmin(admin.ModelAdmin):
    list_display = ("mascota", "fecha_consulta", "profesional")
    list_filter = ("fecha_consulta",)
    search_fields = ("mascota__nombre", "mascota__id_dueno__nombre_completo", "anamnesis")


@admin.register(Hospitalizacion)
class HospitalizacionAdmin(admin.ModelAdmin):
    list_display = ("mascota", "fecha_ingreso", "estado")
    list_filter = ("estado", "fecha_ingreso")
    search_fields = ("mascota__nombre", "motivo")
