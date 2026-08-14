# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDashboardTour(HttpCase):
	"""Único punto donde el frontend se ejecuta de verdad en un navegador."""

	def test_dashboard_tour(self):
		today = fields.Date.context_today(self.env["project.project"])
		admin = self.env.ref("base.user_admin")
		admin.write(
			{
				"group_ids": [
					(4, self.env.ref("primate_project_dashboard.group_dashboard_manager").id),
					(4, self.env.ref("hr_timesheet.group_hr_timesheet_user").id),
				]
			}
		)
		partner = self.env["res.partner"].create({"name": "Cliente Tour"})

		# Un proyecto crítico, para que el filtro de "solo en riesgo" tenga qué mostrar.
		critico = self.env["project.project"].create(
			{
				"name": "Tour crítico",
				"partner_id": partner.id,
				"user_id": admin.id,
				"date_start": today - timedelta(days=20),
				"date": today + timedelta(days=20),
				"allow_milestones": True,
			}
		)
		self.env["project.milestone"].create(
			[
				{
					"project_id": critico.id,
					"name": "Hito alcanzado",
					"deadline": today - timedelta(days=15),
					"planned_progress": 30.0,
					"is_reached": True,
				},
				{
					"project_id": critico.id,
					"name": "Hito vencido",
					"deadline": today - timedelta(days=10),
					"planned_progress": 80.0,
				},
			]
		)
		self.env["project.task"].create(
			[
				{
					"name": f"Tarea tour {index}",
					"project_id": critico.id,
					"allocated_hours": 10.0,
					"area": "technical",
					"date_deadline": fields.Datetime.now() + timedelta(days=2),
				}
				for index in range(3)
			]
		)

		# Y uno sano, para que la tabla tenga más de una fila.
		sano = self.env["project.project"].create(
			{
				"name": "Tour en plan",
				"partner_id": partner.id,
				"user_id": admin.id,
				"date_start": today - timedelta(days=10),
				"date": today + timedelta(days=10),
				"allow_milestones": True,
			}
		)
		self.env["project.milestone"].create(
			[
				{
					"project_id": sano.id,
					"name": "Arranque",
					"deadline": today - timedelta(days=5),
					"planned_progress": 25.0,
					"is_reached": True,
				},
				{
					"project_id": sano.id,
					"name": "Cierre",
					"deadline": today + timedelta(days=5),
					"planned_progress": 75.0,
				},
			]
		)
		tareas_sanas = self.env["project.task"].create(
			[
				{
					"name": f"Tarea sana {index}",
					"project_id": sano.id,
					"allocated_hours": 10.0,
					"area": "functional",
				}
				for index in range(4)
			]
		)
		tareas_sanas[:3].write({"state": "1_done"})

		self.env["project.project"]._cron_recompute_health_state()
		self.env.flush_all()

		self.start_tour(
			"/odoo/action-primate_project_dashboard.action_project_dashboard",
			"primate_project_dashboard_tour",
			login="admin",
		)
