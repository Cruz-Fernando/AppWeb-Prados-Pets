"""
Reportes semanales (PB-20 / RF14).

Semana de domingo a sábado, publicada cada sábado; solo la ve el administrador.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.agendamiento.models import Cita
from apps.directorio.models import Dueno, Mascota
from apps.facturacion.models import Factura, ItemFactura, MovimientoCaja
from apps.inventario.models import Producto
from apps.peluqueria.models import CitaPeluqueria
from apps.usuarios.models import Rol

from . import analista, calculos, semanas
from .pronostico import pronosticar

Usuario = get_user_model()

# Semana de prueba: domingo 8 a sábado 14 de noviembre de 2026.
SABADO = date(2026, 11, 14)
LUNES = date(2026, 11, 9)


def usuario(nombre, rol):
    return Usuario.objects.create_user(
        username=nombre, password="Clave#12345", nombre_completo=nombre.title(),
        id_rol=Rol.objects.get_or_create(nombre_rol=rol)[0],
    )


def momento(dia, hora, minuto=0):
    """Datetime con la zona de la clínica (America/Bogota)."""
    return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))


# ---------------------------------------------------------------------------
# Semanas
# ---------------------------------------------------------------------------

class SemanasTests(SimpleTestCase):

    def test_cada_dia_pertenece_a_la_semana_que_cierra_el_sabado(self):
        self.assertEqual(semanas.sabado_de(date(2026, 11, 8)), SABADO)    # domingo
        self.assertEqual(semanas.sabado_de(date(2026, 11, 11)), SABADO)   # miércoles
        self.assertEqual(semanas.sabado_de(SABADO), SABADO)
        self.assertEqual(semanas.sabado_de(date(2026, 11, 15)), date(2026, 11, 21))

    def test_dias_de_va_de_domingo_a_sabado(self):
        dias = semanas.dias_de(SABADO)
        self.assertEqual(len(dias), 7)
        self.assertEqual((dias[0], dias[-1]), (date(2026, 11, 8), SABADO))
        self.assertEqual(dias[0].weekday(), 6)

    def test_el_sabado_se_publica_el_reporte_de_ese_dia(self):
        self.assertEqual(semanas.ultimo_publicado(SABADO), SABADO)

    def test_entre_domingo_y_viernes_el_ultimo_es_el_sabado_anterior(self):
        self.assertEqual(semanas.ultimo_publicado(date(2026, 11, 15)), SABADO)   # domingo
        self.assertEqual(semanas.ultimo_publicado(date(2026, 11, 20)), SABADO)   # viernes

    def test_proximo_reporte_no_cuenta_hoy(self):
        self.assertEqual(semanas.proximo_reporte(SABADO), date(2026, 11, 21))
        self.assertEqual(semanas.proximo_reporte(date(2026, 11, 17)), date(2026, 11, 21))

    def test_disponibles_del_mas_reciente_al_mas_antiguo(self):
        self.assertEqual(semanas.disponibles(3, date(2026, 11, 17)),
                         [SABADO, date(2026, 11, 7), date(2026, 10, 31)])

    def test_solo_se_publican_sabados_que_ya_llegaron(self):
        hoy = date(2026, 11, 17)
        self.assertTrue(semanas.es_publicado(SABADO, hoy))
        self.assertFalse(semanas.es_publicado(date(2026, 11, 21), hoy))   # sábado futuro
        self.assertFalse(semanas.es_publicado(date(2026, 11, 13), hoy))   # viernes

    def test_hora_texto(self):
        self.assertEqual(semanas.hora_texto(9), "9 a. m.")
        self.assertEqual(semanas.hora_texto(12), "12 m.")
        self.assertEqual(semanas.hora_texto(15), "3 p. m.")

    def test_limites_cubren_dias_completos_en_hora_local(self):
        inicio, fin = semanas.limites(date(2026, 11, 8), SABADO)
        self.assertEqual(timezone.localtime(inicio), momento(date(2026, 11, 8), 0))
        self.assertEqual(timezone.localtime(fin), momento(date(2026, 11, 15), 0))


# ---------------------------------------------------------------------------
# Pronóstico
# ---------------------------------------------------------------------------

class PronosticoTests(SimpleTestCase):

    def test_con_menos_de_tres_semanas_no_pronostica(self):
        self.assertIsNone(pronosticar([]))
        self.assertIsNone(pronosticar([100, 200]))

    def test_semanas_iniciales_sin_movimiento_no_cuentan(self):
        self.assertIsNone(pronosticar([0, 0, 0, 100, 200]))
        p = pronosticar([0, 0, 100, 200, 300])
        self.assertEqual(p.semanas_usadas, 3)
        self.assertAlmostEqual(p.valor, 400)

    def test_recta_exacta_sigue_la_tendencia_sin_rango(self):
        p = pronosticar([100, 200, 300, 400])
        self.assertAlmostEqual(p.valor, 500)
        self.assertAlmostEqual(p.bajo, 500)
        self.assertAlmostEqual(p.alto, 500)
        self.assertAlmostEqual(p.pendiente, 100)
        self.assertEqual(p.tendencia, "sube")

    def test_con_ruido_el_rango_rodea_el_valor(self):
        p = pronosticar([100, 180, 150, 260, 230])
        self.assertLess(p.bajo, p.valor)
        self.assertGreater(p.alto, p.valor)

    def test_nunca_pronostica_negativo(self):
        p = pronosticar([400, 200, 50])
        self.assertEqual(p.valor, 0)
        self.assertEqual(p.bajo, 0)
        self.assertEqual(p.tendencia, "baja")

    def test_cambio_menor_al_3_por_ciento_es_estable(self):
        self.assertEqual(pronosticar([100, 101, 100, 101]).tendencia, "estable")


# ---------------------------------------------------------------------------
# Simulador de IA (reglas)
# ---------------------------------------------------------------------------

def semana_tranquila(**cambios):
    """Cifras de una semana normal que no dispara ninguna recomendación."""
    dias = [{"fecha": f, "corto": semanas.DIAS_CORTOS[f.weekday()], "nombre": semanas.DIAS[f.weekday()],
             "atenciones": 3} for f in semanas.dias_de(SABADO)]
    datos = {
        "desde": date(2026, 11, 8), "hasta": SABADO, "dias": dias,
        "ingresos": Decimal("600000"), "facturas": 12, "ticket_promedio": Decimal("50000"),
        "lineas": [
            {"clave": "CONSULTA", "nombre": "Consultas y servicios clínicos", "monto": Decimal("300000"), "porcentaje": 50},
            {"clave": "PELUQUERIA", "nombre": "Peluquería", "monto": Decimal("200000"), "porcentaje": 33},
            {"clave": "PRODUCTO", "nombre": "Productos", "monto": Decimal("100000"), "porcentaje": 17},
        ],
        "caja": {"ingresos": Decimal("600000"), "gastos": Decimal("100000"), "anulaciones": Decimal("0"),
                 "balance": Decimal("500000")},
        "consultas": 10, "peluquerias": 8, "atenciones": 18, "dia_mas_atenciones": dias[1],
        "programadas": 18, "canceladas": 0, "tasa_cancelacion": 0, "por_cerrar": 0,
        "hora_pico": None, "agenda_siguiente": 18, "duenos_nuevos": 1,
        "stock_bajo": [], "agotados": 0, "vencidos": [], "por_vencer": [],
    }
    datos.update(cambios)
    return datos


def serie_plana(atenciones=18):
    return [{"sabado": SABADO - timedelta(weeks=i), "ingresos": Decimal("600000"), "atenciones": atenciones}
            for i in reversed(range(4))]


def titulos(analisis):
    return [r["titulo"] for r in analisis["recomendaciones"]]


class AnalistaTests(SimpleTestCase):

    def analizar(self, semana=None, variacion=None, **kwargs):
        return analista.analizar(semana or semana_tranquila(), serie_plana(),
                                 variacion or {"ingresos": 0, "atenciones": 0}, **kwargs)

    def test_semana_normal_no_genera_recomendaciones(self):
        self.assertEqual(self.analizar()["recomendaciones"], [])

    def test_semana_sin_movimiento_pide_revisar_el_registro(self):
        vacia = semana_tranquila(ingresos=Decimal("0"), atenciones=0, programadas=0, facturas=0)
        a = self.analizar(vacia)
        self.assertEqual(titulos(a), ["Revisa que se esté registrando la actividad"])
        self.assertIn("no se registraron cobros", a["resumen"][0])

    def test_caja_en_perdida_es_alerta(self):
        caja = {"ingresos": Decimal("100000"), "gastos": Decimal("300000"), "anulaciones": Decimal("20000"),
                "balance": Decimal("-220000")}
        a = self.analizar(semana_tranquila(caja=caja))
        reco = a["recomendaciones"][0]
        self.assertEqual((reco["tipo"], reco["titulo"]), ("alerta", "La semana cerró en pérdida"))
        self.assertIn("$320.000", reco["texto"])
        self.assertTrue(any("cerró en pérdida" in f for f in a["resumen"]))

    def test_caida_fuerte_de_ingresos(self):
        a = self.analizar(variacion={"ingresos": -20, "atenciones": 0})
        self.assertIn("Los ingresos bajaron un 20 %", titulos(a))
        self.assertIn("20 % menos que la semana anterior", a["resumen"][0])

    def test_caida_leve_no_alarma(self):
        self.assertEqual(self.analizar(variacion={"ingresos": -10, "atenciones": 0})["recomendaciones"], [])

    def test_cancelaciones_altas_solo_con_suficientes_citas(self):
        alta = semana_tranquila(programadas=10, canceladas=3, tasa_cancelacion=30)
        self.assertIn("Se canceló el 30 % de las citas", titulos(self.analizar(alta)))
        pocas = semana_tranquila(programadas=4, canceladas=2, tasa_cancelacion=50)
        self.assertNotIn("Se canceló el 50 % de las citas", titulos(self.analizar(pocas)))

    def test_singular_y_plural(self):
        uno = semana_tranquila(agotados=1, stock_bajo=[{"nombre": "Gasa", "stock_actual": 0, "stock_minimo": 5}])
        self.assertIn("1 producto agotado", titulos(self.analizar(uno)))
        dos = semana_tranquila(agotados=2, stock_bajo=[{"nombre": "Gasa", "stock_actual": 0, "stock_minimo": 5},
                                                        {"nombre": "Suero", "stock_actual": 0, "stock_minimo": 2}])
        a = self.analizar(dos)
        self.assertIn("2 productos agotados", titulos(a))
        self.assertIn("Gasa y Suero", a["recomendaciones"][0]["texto"])

    def test_recordatorios_pendientes_solo_si_hay(self):
        self.assertIn("3 recordatorios esperan aviso", titulos(self.analizar(recordatorios_pendientes=3)))
        self.assertEqual(self.analizar(recordatorios_pendientes=0)["recomendaciones"], [])

    def test_ordenadas_por_urgencia(self):
        semana = semana_tranquila(duenos_nuevos=4, por_cerrar=2, agotados=1,
                                  stock_bajo=[{"nombre": "Gasa", "stock_actual": 0, "stock_minimo": 5}])
        a = self.analizar(semana, variacion={"ingresos": 30, "atenciones": 0}, recordatorios_pendientes=2)
        orden = [analista.TIPOS[r["tipo"]]["orden"] for r in a["recomendaciones"]]
        self.assertEqual(orden, sorted(orden))
        self.assertEqual(a["recomendaciones"][0]["tipo"], "alerta")
        self.assertEqual(a["recomendaciones"][-1]["tipo"], "logro")

    def test_resumen_con_pronostico(self):
        p = pronosticar([400000, 500000, 600000])
        a = self.analizar(pronostico_ingresos=p)
        self.assertTrue(any("$700.000" in f for f in a["resumen"]))
        self.assertIn("La tendencia de ingresos va al alza", titulos(a))

    def test_formato_de_pesos(self):
        self.assertEqual(analista.pesos(1234567.8), "$1.234.568")
        self.assertEqual(analista.pesos(Decimal("-5000")), "-$5.000")
        self.assertEqual(analista.pesos(None), "$0")

    def test_rango_de_semana_que_cruza_de_mes(self):
        self.assertEqual(analista.rango_semana(date(2026, 11, 29), date(2026, 12, 5)),
                         "domingo 29 de noviembre y el sábado 5 de diciembre")
        self.assertEqual(analista.rango_semana(date(2026, 11, 8), SABADO),
                         "domingo 8 y el sábado 14 de noviembre")


# ---------------------------------------------------------------------------
# Cálculos contra la base
# ---------------------------------------------------------------------------

class CalculosTests(TestCase):
    """Una semana armada a mano, con casos en los bordes del domingo y el sábado."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = usuario("admin_rep", "administrador")
        vet = usuario("vet_rep", "veterinario")
        groomer = usuario("groomer_rep", "groomer")

        cls.antiguo = Dueno.objects.create(nombre_completo="Ana Pérez", telefono="3000000001", direccion="Cúcuta")
        Dueno.objects.filter(pk=cls.antiguo.pk).update(fecha_registro=date(2026, 6, 1))
        nuevo = Dueno.objects.create(nombre_completo="Luis Gómez", telefono="3000000002", direccion="Cúcuta")
        Dueno.objects.filter(pk=nuevo.pk).update(fecha_registro=date(2026, 11, 10))
        toby = Mascota.objects.create(id_dueno=cls.antiguo, nombre="Toby", especie="perro")
        luna = Mascota.objects.create(id_dueno=nuevo, nombre="Luna", especie="gato")

        def cita(dia, hora, estado, mascota=toby, tipo="consulta_general"):
            return Cita.objects.create(mascota=mascota, veterinario=vet, tipo_servicio=tipo, fecha=dia,
                                       hora_inicio=time(hora, 0), hora_fin=time(hora, 30), estado=estado)

        atendida = cita(LUNES, 9, "atendida")
        cita(date(2026, 11, 10), 10, "cancelada")
        cita(date(2026, 11, 11), 11, "programada", tipo="vacunacion")     # pasó y nadie la cerró
        cita(date(2026, 11, 16), 9, "programada")                         # semana siguiente
        cita(date(2026, 11, 17), 9, "cancelada")                          # semana siguiente, no cuenta
        bano = CitaPeluqueria.objects.create(mascota=luna, nombre_mascota="Luna", raza="Criollo", servicio="BANO",
                                             precio=40000, fecha_hora=momento(SABADO, 10), groomer=groomer,
                                             estado="Realizada")

        numero = iter(range(1, 100))

        def factura(cuando, dueno, items, estado=Factura.PAGADA):
            total = sum((Decimal(p) for _, _, p, _ in items), Decimal("0"))
            f = Factura.objects.create(numero=next(numero) if estado != Factura.BORRADOR else None, dueno=dueno,
                                       estado=estado, fecha=cuando, subtotal=total, total=total,
                                       creada_por=cls.admin, usuario=cls.admin)
            for tipo, descripcion, precio, ref in items:
                ItemFactura.objects.create(factura=f, tipo=tipo, descripcion=descripcion,
                                           precio_unitario=Decimal(precio), **ref)
            return f

        consulta = (ItemFactura.CONSULTA, "Consulta general", 60000, {"cita": atendida})
        factura(momento(LUNES, 9, 40), cls.antiguo, [consulta])
        # El sábado a las 11:30 p. m. todavía es de esta semana…
        factura(momento(SABADO, 23, 30), nuevo,
                [(ItemFactura.PELUQUERIA, "Peluquería: Baño", 40000, {"cita_peluqueria": bano})])
        # …y el domingo a las 12:30 a. m. ya es de la siguiente.
        factura(momento(date(2026, 11, 15), 0, 30), nuevo, [(ItemFactura.PRODUCTO, "Shampoo", 18000, {})])
        factura(momento(date(2026, 11, 12), 15), cls.antiguo, [(ItemFactura.PRODUCTO, "Gasa", 5000, {})],
                estado=Factura.BORRADOR)
        factura(momento(date(2026, 11, 12), 16), cls.antiguo, [(ItemFactura.PRODUCTO, "Suero", 9000, {})],
                estado=Factura.ANULADA)

        for tipo, categoria, monto in [(MovimientoCaja.INGRESO, "FACTURA", 100000),
                                       (MovimientoCaja.EGRESO, "FACTURA", 20000),    # anulación
                                       (MovimientoCaja.EGRESO, "ARRIENDO", 150000)]:
            MovimientoCaja.objects.create(tipo=tipo, categoria=categoria, monto=Decimal(monto),
                                          fecha=date(2026, 11, 12), descripcion="Prueba")

        Producto.objects.create(codigo="GASA", nombre="Gasa estéril", precio_venta=Decimal("300"),
                                stock_actual=0, stock_minimo=5)

    def setUp(self):
        self.semana = calculos.calcular(SABADO, ahora=momento(date(2026, 11, 16), 9))

    def test_ingresos_solo_de_facturas_cobradas_en_la_semana(self):
        s = self.semana
        self.assertEqual(s["ingresos"], Decimal("100000"))
        self.assertEqual(s["facturas"], 2)
        self.assertEqual(s["ticket_promedio"], Decimal("50000"))

    def test_ingresos_por_dia_y_ancho_de_las_barras(self):
        dias = {d["fecha"]: d for d in self.semana["dias"]}
        self.assertEqual(dias[LUNES]["ingresos"], Decimal("60000"))
        self.assertEqual(dias[SABADO]["ingresos"], Decimal("40000"))
        self.assertEqual(dias[LUNES]["ancho_ingresos"], 100)
        self.assertEqual(dias[SABADO]["ancho_ingresos"], 67)
        self.assertEqual(dias[date(2026, 11, 8)]["ancho_ingresos"], 0)

    def test_ingresos_por_linea(self):
        lineas = {l["clave"]: (l["monto"], l["porcentaje"]) for l in self.semana["lineas"]}
        self.assertEqual(lineas, {"CONSULTA": (Decimal("60000"), 60), "PELUQUERIA": (Decimal("40000"), 40),
                                  "PRODUCTO": (Decimal("0"), 0)})

    def test_caja_separa_anulaciones_de_gastos(self):
        caja = self.semana["caja"]
        self.assertEqual(caja["ingresos"], Decimal("100000"))
        self.assertEqual(caja["anulaciones"], Decimal("20000"))
        self.assertEqual(caja["gastos"], Decimal("150000"))
        self.assertEqual(caja["balance"], Decimal("-70000"))
        self.assertEqual(caja["gastos_detalle"], [{"nombre": "Arriendo", "monto": Decimal("150000")}])

    def test_agenda(self):
        s = self.semana
        self.assertEqual((s["consultas"], s["peluquerias"], s["atenciones"]), (1, 1, 2))
        self.assertEqual((s["programadas"], s["canceladas"], s["tasa_cancelacion"]), (4, 1, 25))
        self.assertEqual(s["por_cerrar"], 1)
        self.assertEqual(s["agenda_siguiente"], 1)

    def test_clientes(self):
        s = self.semana
        self.assertEqual(s["clientes_atendidos"], 2)
        self.assertEqual(s["clientes_recurrentes"], 1)
        self.assertEqual(s["duenos_nuevos"], 1)

    def test_inventario(self):
        self.assertEqual(self.semana["agotados"], 1)
        self.assertEqual(self.semana["stock_bajo"][0]["nombre"], "Gasa estéril")

    def test_serie_reparte_cada_cobro_en_su_semana(self):
        anterior, siguiente = calculos.serie(date(2026, 11, 21), 2)
        self.assertEqual((anterior["sabado"], anterior["ingresos"], anterior["atenciones"]),
                         (SABADO, Decimal("100000"), 2))
        self.assertEqual((siguiente["sabado"], siguiente["ingresos"], siguiente["atenciones"]),
                         (date(2026, 11, 21), Decimal("18000"), 0))


# ---------------------------------------------------------------------------
# Pantalla y PDF
# ---------------------------------------------------------------------------

class VistasTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = usuario("admin_vista", "administrador")
        cls.otros = [usuario(f"{rol}_vista", rol) for rol in ("veterinario", "auxiliar", "groomer", "domiciliario")]

    def setUp(self):
        cache.clear()   # el reporte se guarda en caché por sábado

    def test_sin_sesion_va_al_login(self):
        for nombre in ("reportes:semanal", "reportes:semanal_pdf"):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn(reverse("usuarios:login"), respuesta["Location"])

    def test_solo_el_administrador(self):
        for otro in self.otros:
            self.client.force_login(otro)
            for nombre in ("reportes:semanal", "reportes:semanal_pdf"):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 403, f"{otro.username} {nombre}")

    def test_pantalla_del_ultimo_reporte(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("reportes:semanal"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["sabado"], semanas.ultimo_publicado(timezone.localdate()))
        self.assertContains(respuesta, "Simulador de IA")

    def test_semana_pedida(self):
        self.client.force_login(self.admin)
        ultimo = semanas.ultimo_publicado(timezone.localdate())
        anterior = ultimo - timedelta(weeks=1)
        casos = {anterior.isoformat(): anterior,
                 (ultimo + timedelta(weeks=1)).isoformat(): ultimo,   # aún no se publica
                 (anterior + timedelta(days=1)).isoformat(): ultimo,  # no es sábado
                 "basura": ultimo}
        for pedido, esperado in casos.items():
            respuesta = self.client.get(reverse("reportes:semanal"), {"semana": pedido})
            self.assertEqual(respuesta.context["sabado"], esperado, pedido)

    def test_pdf(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("reportes:semanal_pdf"))
        self.assertEqual(respuesta.status_code, 200)
        # Si xhtml2pdf falla, render_pdf devuelve el HTML con 200: hay que mirar el contenido.
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertTrue(respuesta.content.startswith(b"%PDF"))
        sabado = semanas.ultimo_publicado(timezone.localdate())
        self.assertIn(f"reporte-semanal-{sabado.isoformat()}", respuesta["Content-Disposition"])
