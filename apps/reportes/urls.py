from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("", views.semanal, name="semanal"),
    path("pdf/", views.semanal_pdf, name="semanal_pdf"),
]
