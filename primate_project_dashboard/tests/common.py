# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase

from ..models.dashboard_params import PARAM_PREFIX


class DashboardCommon(TransactionCase):
	"""Base con fábricas para armar escenarios de proyecto sin repetir plomería."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.today = fields.Date.context_today(cls.env["project.project"])
		cls.partner = cls.env["res.partner"].create({"name": "Cliente Test"})
		cls.uom_hour = cls.env.ref("uom.product_uom_hour")
		cls.service = cls.env["product.product"].create(
			{
				"name": "Servicio Test",
				"type": "service",
				"uom_id": cls.uom_hour.id,
				"list_price": 100.0,
				"invoice_policy": "order",
			}
		)
		cls.manager_user = cls._make_user("dash_manager", "group_dashboard_manager")
		cls.lead_user = cls._make_user("dash_lead", "group_dashboard_area_lead")
		cls.pm_user = cls._make_user("dash_pm", "group_dashboard_pm")
		cls.employee = cls.env["hr.employee"].create(
			{"name": "Empleado Test", "user_id": cls.pm_user.id, "hourly_cost": 20.0}
		)

	# ------------------------------------------------------------------
	# Fábricas
	# ------------------------------------------------------------------

	@classmethod
	def _make_user(cls, login, dashboard_group):
		"""Usuario con el perfil de dashboard pedido, más lo mínimo para operar."""
		groups = [
			cls.env.ref("base.group_user").id,
			cls.env.ref("project.group_project_user").id,
			cls.env.ref("hr_timesheet.group_hr_timesheet_user").id,
			cls.env.ref(f"primate_project_dashboard.{dashboard_group}").id,
		]
		# Dirección y líderes de área ven los timesheets de todos; el PM, solo los suyos.
		if dashboard_group != "group_dashboard_pm":
			groups.append(cls.env.ref("hr_timesheet.group_timesheet_manager").id)
		user = cls.env["res.users"].create(
			{"name": login, "login": login, "password": login, "group_ids": [(6, 0, groups)]}
		)
		# El grupo de dirección se hereda hacia abajo: se quita explícitamente para que
		# cada perfil sea el que dice ser.
		if dashboard_group != "group_dashboard_manager":
			user.write(
				{
					"group_ids": [
						(3, cls.env.ref("primate_project_dashboard.group_dashboard_manager").id)
					]
				}
			)
		return user

	def _make_project(self, name="Proyecto", start=-30, end=30, user=None, **values):
		"""Proyecto con fechas relativas a hoy. `start`/`end` en días; None = sin fecha."""
		vals = {
			"name": name,
			"partner_id": self.partner.id,
			"user_id": (user or self.pm_user).id,
			"allow_milestones": True,
			"allow_billable": True,
		}
		if start is not None:
			vals["date_start"] = self.today + timedelta(days=start)
		if end is not None:
			vals["date"] = self.today + timedelta(days=end)
		vals.update(values)
		return self.env["project.project"].create(vals)

	def _make_milestones(self, project, points):
		"""`points` = [(días respecto de hoy, avance planificado, alcanzado)]."""
		return self.env["project.milestone"].create(
			[
				{
					"project_id": project.id,
					"name": f"Hito {index + 1}",
					"deadline": self.today + timedelta(days=days),
					"planned_progress": progress,
					"is_reached": reached,
				}
				for index, (days, progress, reached) in enumerate(points)
			]
		)

	def _area(self, code):
		"""El área por CODE. Los tests hablan de 'technical', nunca de un id: el code es lo que
		viaja en el payload del dashboard y lo que sobrevive a un dump restaurado en otra base."""
		return self.env["primate.area"]._by_code(code)

	def _make_tasks(self, project, total=10, done=0, area="technical", allocated=10.0, deadline=None):
		area_id = self._area(area).id
		tasks = self.env["project.task"].create(
			[
				{
					"name": f"{project.name} T{index + 1}",
					"project_id": project.id,
					"allocated_hours": allocated,
					"area_id": area_id,
					**(
						{"date_deadline": fields.Datetime.now() + timedelta(days=deadline)}
						if deadline is not None
						else {}
					),
				}
				for index in range(total)
			]
		)
		if done:
			tasks[:done].write({"state": "1_done"})
		return tasks

	def _make_sale_order(self, project, hours=100.0, price=100.0):
		order = self.env["sale.order"].create(
			{
				"partner_id": self.partner.id,
				"order_line": [
					(0, 0, {"product_id": self.service.id, "product_uom_qty": hours, "price_unit": price})
				],
			}
		)
		order.action_confirm()
		order.order_line.write({"project_id": project.id})
		project.sale_line_id = order.order_line[0].id
		return order

	def _add_timesheet(self, project, hours, days_ago=1, employee=None):
		return self.env["account.analytic.line"].create(
			{
				"name": "Trabajo",
				"project_id": project.id,
				"employee_id": (employee or self.employee).id,
				"unit_amount": hours,
				"date": self.today - timedelta(days=days_ago),
			}
		)

	def _set_param(self, key, value):
		self.env["ir.config_parameter"].sudo().set_param(PARAM_PREFIX + key, str(value))

	def _health(self, project):
		"""Semáforo recalculado al vuelo, que es lo que muestra el dashboard."""
		return project._primate_health_metrics()[project.id]["health_state"]

	def _metrics(self, project):
		return project._primate_health_metrics()[project.id]
