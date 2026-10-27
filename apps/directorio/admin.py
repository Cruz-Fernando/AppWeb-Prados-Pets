from django.contrib import admin

from .models import Dueno, Mascota, Vacunacion


class MascotaInline(admin.TabularInline):
    model = Mascota
    extra = 0


@admin.register(Dueno)
class DuenoAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "telefono", "es_recurrente", "numero_visitas")
    search_fields = ("nombre_completo", "telefono")
    inlines = [MascotaInline]


@admin.register(Mascota)
class MascotaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "especie", "raza", "id_dueno")
    search_fields = ("nombre", "id_dueno__nombre_completo")
    list_filter = ("especie",)


@admin.register(Vacunacion)
class VacunacionAdmin(admin.ModelAdmin):
    list_display = ("mascota", "vacuna", "fecha")
    search_fields = ("mascota__nombre", "vacuna")
    list_filter = ("fecha",)
