# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo.tests.common import tagged

from .common import DashboardCommon


@tagged("post_install", "-at_install")
class TestSaleLineSharing(DashboardCommon):
	"""Una línea de venta referenciada por varios proyectos no puede contarse dos veces."""

	def _shared_line(self, hours=100.0, price=50.0):
		order = self.env["sale.order"].create(
			{
				"partner_id": self.partner.id,
				"order_line": [
					(0, 0, {"product_id": self.service.id, "product_uom_qty": hours, "price_unit": price})
				],
			}
		)
		order.action_confirm()
		return order.order_line[0]

	def test_linea_compartida_se_imputa_a_uno_solo(self):
		line = self._shared_line(hours=100.0)
		proyectos = self.env["project.project"]
		for index in range(3):
			proyectos |= self._make_project(f"Comparte {index}", sale_line_id=line.id)
		horas = proyectos._primate_sold_hours_map()
		self.assertEqual(
			sum(value or 0.0 for value in horas.values()),
			100.0,
			"el portafolio no puede ver 300 horas vendidas donde se vendieron 100",
		)
		con_horas = [pid for pid, value in horas.items() if value]
		self.assertEqual(con_horas, [min(proyectos.ids)], "se imputa al de menor id")

	def test_monto_compartido_tampoco_se_duplica(self):
		line = self._shared_line(hours=100.0, price=50.0)
		proyectos = self.env["project.project"]
		for index in range(3):
			proyectos |= self._make_project(f"Comparte {index}", sale_line_id=line.id)
		montos = proyectos._primate_sold_amount_map()
		self.assertEqual(sum(value or 0.0 for value in montos.values()), 5000.0)

	def test_avisa_por_log(self):
		line = self._shared_line()
		proyectos = self.env["project.project"]
		for index in range(2):
			proyectos |= self._make_project(f"Comparte {index}", sale_line_id=line.id)
		with self.assertLogs(
			"odoo.addons.primate_project_dashboard.models.project_project", level="WARNING"
		) as captured:
			proyectos._primate_sold_hours_map()
		self.assertTrue(
			any(str(line.id) in message for message in captured.output),
			"el problema de datos del cliente tiene que quedar en el log",
		)

	def test_linea_con_dueno_no_entra_como_huerfana(self):
		"""Si la línea ya apunta a un proyecto, ese es su dueño y no se cuenta de nuevo."""
		line = self._shared_line(hours=100.0)
		dueno = self._make_project("Dueño")
		line.project_id = dueno.id
		otro = self._make_project("Referencia ajena", sale_line_id=line.id)
		horas = (dueno | otro)._primate_sold_hours_map()
		self.assertEqual(horas[dueno.id], 100.0)
		self.assertIsNone(horas[otro.id])

	def test_sin_orden_de_venta_es_sin_dato(self):
		project = self._make_project("Interno")
		horas = project._primate_sold_hours_map()
		self.assertIsNone(horas[project.id], "sin SO no vendió cero horas: no tiene el dato")
