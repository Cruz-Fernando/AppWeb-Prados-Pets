"""
Periodos del reporte (PB-20 / RF14): día, semana y mes.

  - Día: de 00:00 a 23:59 en hora de Colombia.
  - Semana: de domingo a sábado (semanas.py). Se publica el sábado, así que
    la semana en curso no se puede pedir antes de que llegue su sábado.
  - Mes: del día 1 al último día del mes.

El día y el mes en curso sí se pueden ver: el reporte sale «parcial», con
lo registrado hasta el momento.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from django.utils import timezone

from . import semanas

DIA, SEMANA, MES = "dia", "semana", "mes"
TIPOS = (DIA, SEMANA, MES)

# Cuántos periodos mira la tendencia (y el pronóstico) de cada tipo.
TENDENCIA = {DIA: 14, SEMANA: 8, MES: 6}

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Palabras para armar los textos del reporte y del analista según el periodo.
TEXTOS = {
    DIA: {
        "nombre": "día", "plural": "días", "pestana": "Día", "adjetivo": "diario", "titulo": "Reporte diario",
        "el": "el día", "del": "del día", "este": "este día", "ese": "ese día", "anterior": "el día anterior", "frente": "frente al día anterior", "proximo": "el día siguiente",
        "de_proximo": "del día siguiente", "un_normal": "un día normal", "ultimos": "los últimos",
        "siguiente": "el siguiente", "cupos": "ofrece cupos para los próximos días",
        "tramo": "hora", "por_tramo": "por hora",
    },
    SEMANA: {
        "nombre": "semana", "plural": "semanas", "pestana": "Semana", "adjetivo": "semanal", "titulo": "Reporte semanal",
        "el": "la semana", "del": "de la semana", "este": "esta semana", "ese": "esa semana", "anterior": "la semana anterior", "frente": "frente a la semana anterior", "proximo": "la próxima semana",
        "de_proximo": "de la próxima semana", "un_normal": "una semana normal", "ultimos": "las últimas",
        "siguiente": "la siguiente", "cupos": "ofrece cupos en los días flojos de la próxima semana",
        "tramo": "día", "por_tramo": "por día",
    },
    MES: {
        "nombre": "mes", "plural": "meses", "pestana": "Mes", "adjetivo": "mensual", "titulo": "Reporte mensual",
        "el": "el mes", "del": "del mes", "este": "este mes", "ese": "ese mes", "anterior": "el mes anterior", "frente": "frente al mes anterior", "proximo": "el próximo mes",
        "de_proximo": "del próximo mes", "un_normal": "un mes normal", "ultimos": "los últimos",
        "siguiente": "el siguiente", "cupos": "ofrece cupos en los días flojos del próximo mes",
        "tramo": "día", "por_tramo": "por día",
    },
}


def fecha_larga(fecha):
    """«26 de noviembre»."""
    return f"{fecha.day} de {MESES[fecha.month - 1]}"


@dataclass(frozen=True)
class Periodo:
    tipo: str
    desde: date
    hasta: date

    @classmethod
    def de(cls, tipo, fecha):
        """El periodo del tipo pedido que contiene `fecha`."""
        if tipo == DIA:
            return cls(DIA, fecha, fecha)
        if tipo == SEMANA:
            sabado = semanas.sabado_de(fecha)
            return cls(SEMANA, semanas.domingo_de(sabado), sabado)
        if tipo == MES:
            ultimo = calendar.monthrange(fecha.year, fecha.month)[1]
            return cls(MES, fecha.replace(day=1), fecha.replace(day=ultimo))
        raise ValueError(f"Tipo de periodo desconocido: {tipo!r}")

    # --- Navegación ----------------------------------------------------------
    def anterior(self):
        return Periodo.de(self.tipo, self.desde - timedelta(days=1))

    def siguiente(self):
        return Periodo.de(self.tipo, self.hasta + timedelta(days=1))

    def contiene(self, fecha):
        return self.desde <= fecha <= self.hasta

    def en_curso(self, hoy=None):
        """True si el periodo incluye hoy (sus cifras todavía pueden cambiar)."""
        return self.contiene(hoy or timezone.localdate())

    def es_valido(self, hoy=None):
        """Se puede pedir: ya empezó y, si es semana, ya llegó su sábado."""
        hoy = hoy or timezone.localdate()
        if self.tipo == SEMANA:
            return semanas.es_publicado(self.hasta, hoy)
        return self.desde <= hoy

    # --- Datos derivados -----------------------------------------------------
    @property
    def dias(self):
        return [self.desde + timedelta(days=i) for i in range((self.hasta - self.desde).days + 1)]

    @property
    def sabado(self):
        """Sábado que cierra la semana (solo para el reporte semanal)."""
        return self.hasta if self.tipo == SEMANA else None

    @property
    def clave(self):
        """Para la caché: «mes:2026-11-01»."""
        return f"{self.tipo}:{self.desde.isoformat()}"

    @property
    def textos(self):
        return TEXTOS[self.tipo]

    @property
    def etiqueta(self):
        """«jueves 26 de noviembre», «semana del 22 al 28 de noviembre», «noviembre de 2026»."""
        if self.tipo == DIA:
            return f"{semanas.DIAS[self.desde.weekday()]} {fecha_larga(self.desde)}"
        if self.tipo == SEMANA:
            inicio = fecha_larga(self.desde) if self.desde.month != self.hasta.month else str(self.desde.day)
            return f"semana del {inicio} al {fecha_larga(self.hasta)}"
        return f"{MESES[self.desde.month - 1]} de {self.desde.year}"

    @property
    def corto(self):
        """Etiqueta del eje de la tendencia: «26/11» (día), «28/11» (sábado de la semana), «nov» (mes)."""
        if self.tipo == MES:
            return MESES_CORTOS[self.desde.month - 1]
        return f"{self.hasta.day}/{self.hasta.month}"

    @property
    def nombre_archivo(self):
        """Para el PDF: «reporte-diario-2026-11-26», «reporte-semanal-2026-11-28», «reporte-mensual-2026-11»."""
        fecha = self.desde.strftime("%Y-%m") if self.tipo == MES else self.hasta.isoformat()
        return f"reporte-{self.textos['adjetivo']}-{fecha}"

    def semanas(self):
        """
        Semanas (domingo a sábado) que tocan el periodo, recortadas a sus
        límites. En el mes, la primera y la última suelen quedar «parciales»:
        así la suma de las semanas es exactamente el mes.
        """
        resultado = []
        sabado = semanas.sabado_de(self.desde)
        while semanas.domingo_de(sabado) <= self.hasta:
            domingo = semanas.domingo_de(sabado)
            desde, hasta = max(domingo, self.desde), min(sabado, self.hasta)
            resultado.append({
                "desde": desde,
                "hasta": hasta,
                "sabado": sabado,
                "parcial": desde != domingo or hasta != sabado,
                "etiqueta": (f"{desde.day}–{hasta.day} {MESES_CORTOS[hasta.month - 1]}"
                             if desde != hasta else f"{desde.day} {MESES_CORTOS[desde.month - 1]}"),
            })
            sabado += timedelta(days=7)
        return resultado


def ultimo_valido(tipo, hoy=None):
    """El periodo más reciente que se puede ver: hoy, el mes en curso o la última semana publicada."""
    hoy = hoy or timezone.localdate()
    if tipo == SEMANA:
        return Periodo.de(SEMANA, semanas.ultimo_publicado(hoy))
    return Periodo.de(tipo, hoy)


def como_periodo(valor):
    """Acepta un Periodo o, como antes de PB-20, el sábado de una semana."""
    if isinstance(valor, Periodo):
        return valor
    if isinstance(valor, date):
        return Periodo.de(SEMANA, valor)
    raise TypeError(f"Se esperaba un Periodo o una fecha, no {type(valor).__name__}")
