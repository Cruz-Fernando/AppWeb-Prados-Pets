"""
PB-19 / RF13 · Factura consolidada e ingresos y gastos.

Criterio de aceptación: una sola factura suma todo lo cobrado en la atención;
las entradas y salidas de dinero (incluidos los gastos) quedan registradas.
"""

from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.agendamiento.models import Cita
from apps.clinico.models import RegistroClinico
from apps.directorio.models import Dueno, Mascota
from apps.inventario.models import MovimientoInventario, Producto, Servicio
from apps.inventario.services import descontar_stock, registrar_salida_manual
from apps.peluqueria.models import CitaPeluqueria
from apps.usuarios.models import Rol

from . import servicios
from .models import Factura, ItemFactura, MovimientoCaja
from .servicios import FacturaError, parsear_monto

Usuario = get_user_model()


def crear_usuario(username, rol):
    return Usuario.objects.create_user(
        username=username, password="Clave#12345", nombre_completo=username.title(),
        id_rol=Rol.objects.get_or_create(nombre_rol=rol)[0],
    )


class FacturaBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario("admin_fac19", "administrador")
        cls.auxiliar = crear_usuario("aux_fac19", "auxiliar")
        cls.groomer = crear_usuario("groomer_fac19", "groomer")
        cls.vet = crear_usuario("vet_fac19", "veterinario")
        cls.domiciliario = crear_usuario("domi_fac19", "domiciliario")
        cls.dueno = Dueno.objects.create(nombre_completo="Carolina Mesa", telefono="3150000019", direccion="Calle 19")
        cls.mascota = Mascota.objects.create(id_dueno=cls.dueno, nombre="Lola", especie="perro")
        cls.otro_dueno = Dueno.objects.create(nombre_completo="Pedro Gil", telefono="3150000020", direccion="Calle 20")
        cls.otra_mascota = Mascota.objects.create(id_dueno=cls.otro_dueno, nombre="Rocky", especie="perro")

    def setUp(self):
        self.client.force_login(self.auxiliar)
        hoy = timezone.localdate()
        self.cita = Cita.objects.create(mascota=self.mascota, veterinario=self.vet, fecha=hoy, hora_inicio=time(9, 0))
        self.pelu = CitaPeluqueria.objects.create(
            mascota=self.mascota, nombre_mascota="Lola", raza="Criollo", servicio="BANO",
            fecha_hora=timezone.now() + timedelta(hours=1), precio=40000, groomer=self.groomer,
        )
        # Insumo usado en la consulta (ya descontado con el registro clínico)
        self.amox = Producto.objects.create(codigo="AMOX19", nombre="Amoxicilina", precio_venta=Decimal("3000"),
                                            stock_actual=20, stock_minimo=1)
        self.registro = RegistroClinico.objects.create(mascota=self.mascota, tipo="otro", profesional=self.vet,
                                                       motivo="Otitis")
        self.salida_consulta = descontar_stock(self.amox.pk, 2, tipo="SALIDA_CLINICA",
                                               registro_clinico=self.registro)
        # Producto que se vende en la factura
        self.champu = Producto.objects.create(codigo="CHAMPU19", nombre="Champú", precio_venta=Decimal("15000"),
                                              stock_actual=10, stock_minimo=1)

    # Atajos
    def borrador(self, dueno=None):
        return servicios.crear_borrador(dueno or self.dueno, self.auxiliar)[0]

    def agregar(self, factura, **datos):
        return self.client.post(reverse("facturacion:factura_agregar", args=[factura.pk]), datos)

    def cobrar(self, factura, medio="EFECTIVO", descuento=""):
        return self.client.post(reverse("facturacion:factura_cobrar", args=[factura.pk]),
                                {"medio_pago": medio, "descuento": descuento})

    def factura_completa(self):
        f = self.borrador()
        self.agregar(f, tipo="consulta", cita=self.cita.pk, precio="50.000")
        self.agregar(f, tipo="peluqueria", cita_peluqueria=self.pelu.pk)
        self.agregar(f, tipo="insumo", movimiento=self.salida_consulta.pk)
        self.agregar(f, tipo="producto", producto=self.champu.pk, cantidad="2")
        f.refresh_from_db()
        return f

    def mensajes(self, respuesta):
        return [str(m) for m in respuesta.wsgi_request._messages]


class FacturaConsolidadaTests(FacturaBase):
    # ---------- Los 3 tipos de ítem y el total ----------
    def test_factura_con_los_tres_tipos_y_total_correcto(self):
        f = self.factura_completa()
        self.assertEqual(set(f.items.values_list("tipo", flat=True)), {"CONSULTA", "PELUQUERIA", "PRODUCTO"})
        # 50.000 consulta + 40.000 peluquería + 2 × 3.000 insumo + 2 × 15.000 champú
        self.assertEqual(f.subtotal, Decimal("126000"))
        self.assertEqual(f.estado, Factura.BORRADOR)

        self.cobrar(f, descuento="6.000")
        f.refresh_from_db()
        self.assertEqual((f.estado, f.numero, f.medio_pago), (Factura.PAGADA, 1, "EFECTIVO"))
        self.assertEqual((f.subtotal, f.descuento, f.total), (Decimal("126000"), Decimal("6000"), Decimal("120000")))
        self.assertEqual(f.usuario, self.auxiliar)

    def test_al_cobrar_la_consulta_queda_atendida_y_la_peluqueria_realizada(self):
        f = self.factura_completa()
        self.cobrar(f)
        self.cita.refresh_from_db(); self.pelu.refresh_from_db()
        self.assertEqual((self.cita.estado, self.pelu.estado), ("atendida", "Realizada"))

    def test_numero_consecutivo(self):
        f1 = self.borrador()
        self.agregar(f1, tipo="producto", producto=self.champu.pk, cantidad="1")
        self.cobrar(f1)
        f2 = self.borrador(self.otro_dueno)
        self.agregar(f2, tipo="producto", producto=self.champu.pk, cantidad="1")
        self.cobrar(f2, medio="NEQUI")
        f1.refresh_from_db(); f2.refresh_from_db()
        self.assertEqual((f1.numero, f2.numero), (1, 2))
        self.assertEqual(f2.numero_display, "N.° 00002")

    def test_servicio_del_catalogo_con_precio_propio_o_del_catalogo(self):
        vacuna = Servicio.objects.create(codigo="VAC-R", nombre="Vacuna antirrábica", precio=Decimal("35000"))
        f = self.borrador()
        self.agregar(f, tipo="servicio", servicio=vacuna.pk, precio="")
        self.agregar(f, tipo="servicio", servicio=vacuna.pk, precio="30.000")
        self.assertEqual(sorted(f.items.values_list("precio_unitario", flat=True)),
                         [Decimal("30000"), Decimal("35000")])

    def test_el_mismo_producto_se_suma_en_una_linea(self):
        f = self.borrador()
        self.agregar(f, tipo="producto", producto=self.champu.pk, cantidad="2")
        self.agregar(f, tipo="producto", producto=self.champu.pk, cantidad="3")
        item = f.items.get()
        self.assertEqual((item.cantidad, item.subtotal), (5, Decimal("75000")))

    def test_quitar_item_del_borrador(self):
        f = self.borrador()
        self.agregar(f, tipo="peluqueria", cita_peluqueria=self.pelu.pk)
        item = f.items.get()
        self.client.post(reverse("facturacion:factura_quitar", args=[f.pk, item.pk]))
        f.refresh_from_db()
        self.assertEqual((f.items.count(), f.subtotal), (0, Decimal("0")))

    # ---------- Una cita se factura una sola vez ----------
    def test_no_facturar_dos_veces_la_misma_cita(self):
        f1 = self.borrador()
        self.agregar(f1, tipo="consulta", cita=self.cita.pk, precio="50000")
        self.agregar(f1, tipo="peluqueria", cita_peluqueria=self.pelu.pk)
        self.agregar(f1, tipo="insumo", movimiento=self.salida_consulta.pk)

        f2 = Factura.objects.create(dueno=self.dueno, creada_por=self.admin)   # otro borrador del mismo dueño
        r = self.agregar(f2, tipo="consulta", cita=self.cita.pk, precio="50000")
        self.assertIn("Esa consulta ya está en otra factura (borrador o pagada).", self.mensajes(r))
        for datos in ({"tipo": "peluqueria", "cita_peluqueria": self.pelu.pk},
                      {"tipo": "insumo", "movimiento": self.salida_consulta.pk}):
            self.agregar(f2, **datos)
        self.assertEqual(f2.items.count(), 0)

        # Tampoco aparece entre lo pendiente
        p = servicios.pendientes(self.dueno)
        self.assertEqual((p["consultas"], p["peluquerias"], p["insumos"]), ([], [], []))

    def test_la_base_de_datos_impide_el_duplicado(self):
        f1, f2 = self.borrador(), Factura.objects.create(dueno=self.dueno)
        ItemFactura.objects.create(factura=f1, tipo="CONSULTA", descripcion="x", cita=self.cita)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ItemFactura.objects.create(factura=f2, tipo="CONSULTA", descripcion="x", cita=self.cita)

    def test_anular_libera_la_cita_para_otra_factura(self):
        f = self.factura_completa()
        self.cobrar(f)
        self.client.post(reverse("facturacion:factura_anular", args=[f.pk]), {"motivo_anulacion": "Error de cobro"})
        f2 = self.borrador()
        self.agregar(f2, tipo="consulta", cita=self.cita.pk, precio="50000")
        self.assertEqual(f2.items.count(), 1)

    def test_descartar_borrador_libera_la_cita(self):
        f = self.borrador()
        self.agregar(f, tipo="consulta", cita=self.cita.pk, precio="50000")
        self.client.post(reverse("facturacion:factura_descartar", args=[f.pk]))
        self.assertFalse(Factura.objects.filter(pk=f.pk).exists())
        self.assertEqual(servicios.pendientes(self.dueno)["consultas"], [self.cita])

    def test_cita_de_otro_dueno_o_cancelada_no_se_factura(self):
        ajena = Cita.objects.create(mascota=self.otra_mascota, veterinario=self.vet,
                                    fecha=timezone.localdate(), hora_inicio=time(11, 0))
        f = self.borrador()
        r = self.agregar(f, tipo="consulta", cita=ajena.pk, precio="50000")
        self.assertIn("Esa consulta no es de una mascota de este propietario.", self.mensajes(r))
        Cita.objects.filter(pk=self.cita.pk).update(estado="cancelada")
        self.agregar(f, tipo="consulta", cita=self.cita.pk, precio="50000")
        self.assertEqual(f.items.count(), 0)

    def test_consulta_sin_precio_no_se_agrega(self):
        f = self.borrador()
        r = self.agregar(f, tipo="consulta", cita=self.cita.pk, precio="")
        self.assertIn("Escribe el precio de la consulta.", self.mensajes(r))
        r = self.agregar(f, tipo="consulta", cita=self.cita.pk, precio="0")
        self.assertIn("El precio de la consulta debe ser mayor que $0.", self.mensajes(r))
        self.assertEqual(f.items.count(), 0)

    # ---------- Stock ----------
    def test_stock_descontado_al_cobrar_y_devuelto_al_anular(self):
        f = self.factura_completa()
        self.champu.refresh_from_db(); self.amox.refresh_from_db()
        self.assertEqual((self.champu.stock_actual, self.amox.stock_actual), (10, 18))   # el borrador no descuenta

        self.cobrar(f)
        self.champu.refresh_from_db(); self.amox.refresh_from_db()
        self.assertEqual((self.champu.stock_actual, self.amox.stock_actual), (8, 18))    # el insumo no se descuenta 2 veces
        venta = f.items.get(producto=self.champu).movimiento
        self.assertEqual((venta.tipo, venta.cantidad), ("SALIDA_VENTA", 2))

        r = self.client.post(reverse("facturacion:factura_anular", args=[f.pk]), {"motivo_anulacion": "Se devolvió"})
        self.assertEqual(r.status_code, 302)
        self.champu.refresh_from_db(); self.amox.refresh_from_db()
        self.assertEqual((self.champu.stock_actual, self.amox.stock_actual), (10, 18))   # el insumo ya se usó
        venta.refresh_from_db()
        self.assertTrue(venta.devuelto)
        self.assertEqual(MovimientoInventario.objects.filter(tipo="ENTRADA_DEVOLUCION").count(), 1)

    def test_si_el_stock_no_alcanza_al_cobrar_no_se_cobra_nada(self):
        f = self.borrador()
        self.agregar(f, tipo="peluqueria", cita_peluqueria=self.pelu.pk)
        self.agregar(f, tipo="producto", producto=self.champu.pk, cantidad="8")
        registrar_salida_manual(self.champu.pk, 5, motivo="DANO")          # alguien quitó unidades mientras tanto
        r = self.cobrar(f)
        self.assertTrue(any("No hay stock suficiente de «Champú»" in m for m in self.mensajes(r)))
        f.refresh_from_db(); self.pelu.refresh_from_db(); self.champu.refresh_from_db()
        self.assertEqual((f.estado, f.numero), (Factura.BORRADOR, None))
        self.assertEqual((self.pelu.estado, self.champu.stock_actual), ("Programada", 5))
        self.assertFalse(MovimientoCaja.objects.exists())

    def test_no_se_agrega_mas_de_lo_disponible(self):
        f = self.borrador()
        r = self.agregar(f, tipo="producto", producto=self.champu.pk, cantidad="11")
        self.assertIn("No hay stock suficiente de «Champú»: pediste 11 y hay 10 disponibles.", self.mensajes(r))

    def test_cita_cancelada_despues_de_agregarla_bloquea_el_cobro(self):
        f = self.borrador()
        self.agregar(f, tipo="peluqueria", cita_peluqueria=self.pelu.pk)
        CitaPeluqueria.objects.filter(pk=self.pelu.pk).update(estado="Cancelada")
        self.cobrar(f)
        f.refresh_from_db()
        self.assertEqual(f.estado, Factura.BORRADOR)

    # ---------- Cobro y anulación ----------
    def test_cobrar_valida_items_medio_de_pago_y_descuento(self):
        f = self.borrador()
        r = self.cobrar(f)
        self.assertIn("Agrega al menos un servicio o producto antes de cobrar.", self.mensajes(r))
        self.agregar(f, tipo="peluqueria", cita_peluqueria=self.pelu.pk)
        r = self.cobrar(f, medio="")
        self.assertIn("Elige el medio de pago.", self.mensajes(r))
        r = self.cobrar(f, descuento="50.000")
        self.assertIn("El descuento no puede superar el subtotal ($40.000).", self.mensajes(r))
        f.refresh_from_db()
        self.assertEqual(f.estado, Factura.BORRADOR)

    def test_una_factura_pagada_no_se_modifica(self):
        f = self.borrador()
        self.agregar(f, tipo="peluqueria", cita_peluqueria=self.pelu.pk)
        self.cobrar(f)
        r = self.agregar(f, tipo="producto", producto=self.champu.pk, cantidad="1")
        self.assertIn("La factura N.° 00001 ya está pagada: no se puede modificar.", self.mensajes(r))
        self.assertEqual(f.items.count(), 1)

    def test_anular_pide_motivo_y_no_borra_nada(self):
        f = self.factura_completa()
        self.cobrar(f)
        r = self.client.post(reverse("facturacion:factura_anular", args=[f.pk]), {"motivo_anulacion": "  "})
        self.assertIn("Escribe el motivo de la anulación.", self.mensajes(r))
        f.refresh_from_db()
        self.assertEqual(f.estado, Factura.PAGADA)

        self.client.post(reverse("facturacion:factura_anular", args=[f.pk]), {"motivo_anulacion": "Cliente equivocado"})
        f.refresh_from_db()
        self.assertEqual((f.estado, f.motivo_anulacion, f.anulada_por), (Factura.ANULADA, "Cliente equivocado",
                                                                         self.auxiliar))
        self.assertEqual(f.items.count(), 4)                                 # los ítems se conservan
        self.assertFalse(f.items.filter(vigente=True).exists())
        with self.assertRaises(FacturaError):
            servicios.anular(f, motivo="otra vez")

    # ---------- Caja ----------
    def test_ingreso_automatico_al_cobrar(self):
        f = self.factura_completa()
        self.cobrar(f, medio="NEQUI", descuento="6000")
        ingreso = MovimientoCaja.objects.get()
        self.assertEqual((ingreso.tipo, ingreso.categoria, ingreso.monto, ingreso.factura),
                         ("INGRESO", "FACTURA", Decimal("120000"), f))
        self.assertIn("Factura N.° 00001", ingreso.descripcion)

    def test_anular_crea_el_egreso_que_reversa_el_ingreso(self):
        f = self.factura_completa()
        self.cobrar(f)
        servicios.anular(f, motivo="Error", usuario=self.admin)
        egreso = MovimientoCaja.objects.get(tipo="EGRESO")
        self.assertEqual((egreso.monto, egreso.factura), (Decimal("126000"), f))
        self.assertEqual(MovimientoCaja.objects.count(), 2)

    def test_gasto_registrado_y_saldo_correcto(self):
        f = self.borrador()
        self.agregar(f, tipo="peluqueria", cita_peluqueria=self.pelu.pk)
        self.cobrar(f)                                                     # +40.000
        hoy = timezone.localdate()
        r = self.client.post(reverse("facturacion:gasto"), {
            "categoria": "ARRIENDO", "monto": "25.000", "fecha": hoy.isoformat(), "descripcion": "Arriendo noviembre"})
        self.assertEqual(r.status_code, 302)
        gasto = MovimientoCaja.objects.get(tipo="EGRESO")
        self.assertEqual((gasto.categoria, gasto.monto, gasto.usuario), ("ARRIENDO", Decimal("25000"), self.auxiliar))

        resumen = servicios.resumen_caja(hoy.replace(day=1), hoy)
        self.assertEqual((resumen["ingresos"], resumen["egresos"], resumen["saldo_final"]),
                         (Decimal("40000"), Decimal("25000"), Decimal("15000")))
        self.assertEqual(resumen["movimientos"][-1].saldo, Decimal("15000"))

        pagina = self.client.get(reverse("facturacion:caja"))
        self.assertContains(pagina, "Arriendo noviembre")
        self.assertContains(pagina, "$15.000")

    def test_saldo_inicial_cuenta_lo_anterior_al_periodo(self):
        hoy = timezone.localdate()
        MovimientoCaja.objects.create(tipo="INGRESO", categoria="OTRO", monto=Decimal("100000"),
                                      fecha=hoy - timedelta(days=40), descripcion="Antes")
        servicios.registrar_gasto(categoria="NOMINA", monto="30000", fecha=hoy, descripcion="Nómina")
        r = servicios.resumen_caja(hoy - timedelta(days=5), hoy)
        self.assertEqual((r["saldo_inicial"], r["saldo_final"]), (Decimal("100000"), Decimal("70000")))
        por_categoria = servicios.resumen_caja(hoy - timedelta(days=5), hoy, "NOMINA")
        self.assertFalse(por_categoria["con_saldo"])
        self.assertEqual(por_categoria["egresos"], Decimal("30000"))

    def test_validaciones_del_gasto(self):
        hoy = timezone.localdate()
        casos = [
            (dict(categoria="FACTURA", monto="1000", fecha=hoy, descripcion="x"), "Elige la categoría del gasto."),
            (dict(categoria="OTRO", monto="0", fecha=hoy, descripcion="x"), "El monto del gasto debe ser mayor que $0."),
            (dict(categoria="OTRO", monto="1000", fecha=hoy + timedelta(days=1), descripcion="x"),
             "La fecha del gasto no puede ser futura."),
            (dict(categoria="OTRO", monto="1000", fecha=hoy, descripcion=" "), "Describe el gasto (ej.: Arriendo de noviembre)."),
        ]
        for datos, mensaje in casos:
            with self.subTest(mensaje=mensaje), self.assertRaisesMessage(FacturaError, mensaje):
                servicios.registrar_gasto(**datos)
        self.assertFalse(MovimientoCaja.objects.exists())

    # ---------- Pantallas y PDF ----------
    def test_flujo_por_pantallas_y_pdf(self):
        r = self.client.get(reverse("facturacion:factura_nueva"), {"q": "carolina"})
        self.assertContains(r, "Carolina Mesa")
        r = self.client.post(reverse("facturacion:factura_nueva"), {"dueno": self.dueno.pk})
        f = Factura.objects.get()
        self.assertRedirects(r, reverse("facturacion:factura_detalle", args=[f.pk]))
        detalle = self.client.get(r["Location"])
        self.assertContains(detalle, "Consultas sin facturar")
        self.assertContains(detalle, "Amoxicilina")                        # insumo de la consulta por cobrar
        # Volver a «Facturar» al mismo dueño continúa el borrador
        self.client.post(reverse("facturacion:factura_nueva"), {"dueno": self.dueno.pk})
        self.assertEqual(Factura.objects.count(), 1)

        pdf = self.client.get(reverse("facturacion:factura_pdf", args=[f.pk]))
        self.assertEqual(pdf.status_code, 302)                             # el borrador no tiene comprobante
        self.agregar(f, tipo="peluqueria", cita_peluqueria=self.pelu.pk)
        self.cobrar(f)
        pdf = self.client.get(reverse("facturacion:factura_pdf", args=[f.pk]))
        self.assertEqual(pdf.status_code, 200)

    def test_lista_filtra_por_estado_y_dueno(self):
        f1 = self.borrador()
        self.agregar(f1, tipo="peluqueria", cita_peluqueria=self.pelu.pk)
        self.cobrar(f1)
        self.borrador(self.otro_dueno)
        url = reverse("facturacion:facturas")
        numeros = lambda r: {f.pk for f in r.context["facturas"]}   # noqa: E731
        self.assertEqual(numeros(self.client.get(url, {"estado": "pagada"})), {f1.pk})
        self.assertEqual(len(self.client.get(url, {"q": "pedro"}).context["facturas"]), 1)
        self.assertEqual(numeros(self.client.get(url, {"q": "#1"})), {f1.pk})       # por número de factura
        self.assertEqual(self.client.get(url).context["totales"]["cobrado"], Decimal("40000"))

    # ---------- Permisos ----------
    def test_permisos_por_rol(self):
        f = self.borrador()
        urls = [reverse("facturacion:facturas"), reverse("facturacion:factura_nueva"), reverse("facturacion:caja"),
                reverse("facturacion:gasto"), reverse("facturacion:factura_detalle", args=[f.pk])]
        for usuario in (self.groomer, self.vet, self.domiciliario):
            self.client.force_login(usuario)
            for url in urls:
                with self.subTest(usuario=usuario.username, url=url):
                    self.assertEqual(self.client.get(url).status_code, 403)
            r = self.cobrar(f)
            self.assertEqual(r.status_code, 403)
        for usuario in (self.admin, self.auxiliar):
            self.client.force_login(usuario)
            for url in urls:
                with self.subTest(usuario=usuario.username, url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_menu_lateral_segun_el_rol(self):
        menu = self.client.get(reverse("usuarios:dashboard"))
        self.assertContains(menu, f'href="{reverse("facturacion:facturas")}"')
        self.client.force_login(self.groomer)
        menu = self.client.get(reverse("usuarios:dashboard"))
        self.assertNotContains(menu, f'href="{reverse("facturacion:facturas")}"')
        self.assertContains(menu, 'id="nav-facturacion"')                 # el groomer ve sus ganancias
        self.client.force_login(self.vet)
        self.assertNotContains(self.client.get(reverse("usuarios:dashboard")), 'id="nav-facturacion"')


class ParsearMontoTests(TestCase):
    def test_formatos(self):
        for texto, esperado in (("45000", "45000"), ("45.000", "45000"), ("$ 45.000", "45000"),
                                ("1.200.000", "1200000"), ("45.000,50", "45000.50"), ("45000 COP", "45000")):
            with self.subTest(texto=texto):
                self.assertEqual(parsear_monto(texto), Decimal(esperado))

    def test_invalidos(self):
        for texto in ("", "abc", "-5", "0", "999999999"):
            with self.subTest(texto=texto), self.assertRaises(FacturaError):
                parsear_monto(texto)
        self.assertEqual(parsear_monto("0", permitir_cero=True), Decimal("0"))
