# Une las dos ramas de migraciones de clínico: recordatorios avisados
# (0005_avisorecordatorio) y récipe médico de Duvan (0005_recetaitem, PB-15).
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("clinico", "0005_avisorecordatorio"),
        ("clinico", "0005_recetaitem"),
    ]

    operations = []
