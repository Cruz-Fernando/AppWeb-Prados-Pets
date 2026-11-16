"""
Convierte un RegistroClinico en datos listos para mostrar (pantalla y PDF),
usando el catálogo de registros.py para etiquetas y opciones.
"""

from datetime import date, time

from django.utils.formats import localize

from .registros import grupos_de


def _formatear(campo, valor, registros_por_id=None):
    if valor in (None, ""):
        return ""
    if campo.tipo == "bool":
        return "Sí" if valor else "No"
    if campo.tipo == "choice":
        if campo.nombre == "cirugia_relacionada" and registros_por_id is not None:
            return registros_por_id.get(str(valor), f"RC-{int(valor):06d}" if str(valor).isdigit() else valor)
        return dict(campo.opciones).get(valor, valor)
    if campo.tipo == "date":
        try:
            return date.fromisoformat(valor).strftime("%d/%m/%Y")
        except (TypeError, ValueError):
            return valor
    if campo.tipo == "time":
        try:
            return time.fromisoformat(valor).strftime("%H:%M")
        except (TypeError, ValueError):
            return valor
    return str(valor)


def detalle_legible(registro):
    """[(titulo_grupo, [(etiqueta, valor, es_largo), ...]), ...] solo con datos llenos."""
    tipo = registro.definicion
    if not tipo:
        return []
    detalle = registro.detalle or {}

    relacionadas = None
    if any(c.nombre == "cirugia_relacionada" for c in tipo.campos) and detalle.get("cirugia_relacionada"):
        from .models import RegistroClinico
        relacionadas = {
            str(r.pk): f"{r.numero} · {r.detalle.get('procedimiento', 'Cirugía')} ({r.fecha_atencion:%d/%m/%Y})"
            for r in RegistroClinico.objects.filter(pk=detalle["cirugia_relacionada"])
        } if str(detalle["cirugia_relacionada"]).isdigit() else {}

    salida = []
    for titulo, campos in grupos_de(tipo):
        filas = []
        for c in campos:
            valor = _formatear(c, detalle.get(c.nombre), relacionadas)
            if valor:
                filas.append((c.etiqueta, valor, c.tipo == "textarea" or c.ancho == "full"))
        if filas:
            salida.append((titulo or tipo.nombre, filas))
    return salida


def vitales(obj):
    """Constantes vitales con unidad, solo las registradas."""
    pares = [
        ("Peso", getattr(obj, "peso", None) or getattr(obj, "peso_actual", None), "kg"),
        ("Temperatura", getattr(obj, "temperatura", None), "°C"),
        ("F. cardíaca", getattr(obj, "frecuencia_cardiaca", None), "lpm"),
        ("F. respiratoria", getattr(obj, "frecuencia_respiratoria", None), "rpm"),
        ("TLLC", getattr(obj, "tllc", None), "s"),
    ]
    datos = [(etq, f"{localize(v)} {u}") for etq, v, u in pares if v not in (None, "")]
    for campo, etq in (("mucosas", "Mucosas"), ("condicion_corporal", "Cond. corporal"),
                       ("hidratacion", "Hidratación")):
        valor = getattr(obj, campo, "")
        if valor:
            display = getattr(obj, f"get_{campo}_display", None)
            datos.append((etq, display() if callable(display) else valor))
    return datos


def evaluacion(registro):
    """Bloque de evaluación y plan, solo lo diligenciado."""
    campos = [
        ("Anamnesis", registro.anamnesis),
        ("Diagnóstico presuntivo", registro.diagnostico_presuntivo),
        ("Diagnóstico definitivo", registro.diagnostico_definitivo),
        ("Tratamiento realizado", registro.tratamiento),
        ("Fórmula médica", registro.prescripcion),
        ("Recomendaciones", registro.recomendaciones),
        ("Observaciones", registro.observaciones),
    ]
    return [(etq, v) for etq, v in campos if v]


def resumen_corto(registro):
    """Una línea para la línea de tiempo."""
    d = registro.detalle or {}
    tipo = registro.tipo
    if tipo == "vacunacion":
        return " · ".join(x for x in (d.get("vacuna"), f"Lote {d['lote']}" if d.get("lote") else "") if x)
    if tipo == "desparasitacion":
        return " · ".join(x for x in (d.get("producto"), d.get("dosis")) if x)
    if tipo in ("cirugia", "otro"):
        return d.get("procedimiento", "")
    if tipo == "sedacion":
        return f"ASA {d['asa']}" if d.get("asa") else ""
    if tipo == "control":
        tipo_def = registro.definicion
        opciones = dict(next(c.opciones for c in tipo_def.campos if c.nombre == "evolucion"))
        return f"Evolución {opciones.get(d.get('evolucion'), '').lower()}" if d.get("evolucion") else ""
    if tipo == "eutanasia":
        return f"Hora de fallecimiento {d['hora_fallecimiento']}" if d.get("hora_fallecimiento") else ""
    return registro.diagnostico_definitivo or registro.diagnostico_presuntivo or ""
