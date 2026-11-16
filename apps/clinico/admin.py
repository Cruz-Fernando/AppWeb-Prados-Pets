from django.contrib import admin

from .models import (
    ConsultaMedica,
    EvolucionHospitalaria,
    Hospitalizacion,
    RegistroClinico,
    TrazaClinica,
)


@admin.register(ConsultaMedica)
class ConsultaMedicaAdmin(admin.ModelAdmin):
    list_display = ("mascota", "fecha_consulta", "profesional")
    list_filter = ("fecha_consulta",)
    search_fields = ("mascota__nombre", "mascota__id_dueno__nombre_completo", "anamnesis")


class EvolucionInline(admin.TabularInline):
    model = EvolucionHospitalaria
    extra = 0
    fields = ("fecha", "profesional", "estado_general", "temperatura", "frecuencia_cardiaca", "observaciones")


@admin.register(Hospitalizacion)
class HospitalizacionAdmin(admin.ModelAdmin):
    list_display = ("numero", "mascota", "fecha_ingreso", "estado", "condicion_alta")
    list_filter = ("estado", "condicion_alta", "fecha_ingreso")
    search_fields = ("mascota__nombre", "motivo")
    inlines = [EvolucionInline]


@admin.register(RegistroClinico)
class RegistroClinicoAdmin(admin.ModelAdmin):
    list_display = ("numero", "mascota", "tipo", "fecha_atencion", "profesional", "anulado")
    list_filter = ("tipo", "anulado", "fecha_atencion")
    search_fields = ("mascota__nombre", "mascota__codigo_mascota", "motivo")
    readonly_fields = ("creado_en", "actualizado_en", "actualizado_por", "anulado_por", "anulado_en")

    def has_delete_permission(self, request, obj=None):
        return False  # los registros clínicos se anulan, no se borran


@admin.register(TrazaClinica)
class TrazaClinicaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "mascota", "accion", "usuario", "descripcion", "ip")
    list_filter = ("accion", "fecha")
    search_fields = ("mascota__nombre", "descripcion", "usuario__username")

    # Bitácora de solo lectura
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
