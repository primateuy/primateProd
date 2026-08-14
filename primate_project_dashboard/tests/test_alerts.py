# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from datetime import timedelta

from odoo import fields
from odoo.tests.common import tagged

from ..models.project_dashboard_alerts import ALERT_LIMIT
from .common import DashboardCommon


@tagged("post_install", "-at_install")
class TestAlerts(DashboardCommon):
	"""Catálogo de alertas (sección 1.9), clave estable y snooze."""

	def _alerts(self, user=None, options=None):
		data = self.env["project.project"].with_user(user or self.manager_user).get_dashboard_data(
			options or {"period": "all"}
		)
		return data["alerts"], data["alerts_total"]

	def _types(self, alerts):
		return {alert["type"] for alert in alerts}

	# ------------------------------------------------------------------
	# Los seis tipos del catálogo
	# ------------------------------------------------------------------

	def test_alerta_hito_vencido(self):
		project = self._make_project("Hito vencido")
		self._make_milestones(project, [(-10, 50.0, False)])
		alerts, _total = self._alerts()
		hito = [a for a in alerts if a["type"] == "milestone_overdue" and a["project_id"] == project.id]
		self.assertTrue(hito)
		self.assertEqual(hito[0]["severity"], "danger")
		self.assertEqual(hito[0]["res_model"], "project.milestone")

	def test_alerta_presupuesto_amarilla_y_roja(self):
		amarillo = self._make_project("Presupuesto amarillo", start=-10, end=10)
		self._make_milestones(amarillo, [(-5, 25.0, True), (5, 75.0, False)])
		self._make_tasks(amarillo, total=10, done=8)
		self._make_sale_order(amarillo, hours=100.0)
		self._add_timesheet(amarillo, 92.0)

		rojo = self._make_project("Presupuesto rojo", start=-10, end=10)
		self._make_milestones(rojo, [(-5, 25.0, True), (5, 75.0, False)])
		self._make_tasks(rojo, total=10, done=1)
		self._make_sale_order(rojo, hours=100.0)
		self._add_timesheet(rojo, 95.0)

		alerts, _total = self._alerts()
		por_proyecto = {
			a["project_id"]: a for a in alerts if a["type"] == "hours_budget"
		}
		# 92% de consumo con 80% de avance: brecha de 12pp, todavía amarilla.
		self.assertEqual(por_proyecto[amarillo.id]["severity"], "warning")
		# 95% de consumo con 10% de avance: brecha de 85pp, roja.
		self.assertEqual(por_proyecto[rojo.id]["severity"], "danger")

	def test_alerta_sin_actividad(self):
		project = self._make_project("Frenado")
		alerts, _total = self._alerts()
		sin_actividad = [
			a for a in alerts if a["type"] == "no_activity" and a["project_id"] == project.id
		]
		self.assertTrue(sin_actividad)

	def test_alerta_sin_actividad_no_dispara_con_movimiento(self):
		project = self._make_project("Activo")
		self._make_tasks(project, total=1)
		self._add_timesheet(project, 1.0, days_ago=0)
		alerts, _total = self._alerts()
		self.assertFalse(
			[a for a in alerts if a["type"] == "no_activity" and a["project_id"] == project.id]
		)

	def test_alerta_timesheets_sin_cargar(self):
		project = self._make_project("Sin timesheets")
		tarea = self._make_tasks(project, total=1)
		tarea.user_ids = [(6, 0, [self.lead_user.id])]
		alerts, _total = self._alerts()
		agregada = [a for a in alerts if a["type"] == "missing_timesheets"]
		self.assertTrue(agregada)
		self.assertIn(self.lead_user.id, agregada[0]["res_ids"])

	def test_alerta_timesheets_abre_la_lista_completa(self):
		"""Con varios usuarios el botón abre la lista, no el primero."""
		project = self._make_project("Varios sin cargar")
		tarea = self._make_tasks(project, total=1)
		tarea.user_ids = [(6, 0, [self.lead_user.id, self.manager_user.id])]
		alerts, _total = self._alerts()
		agregada = [a for a in alerts if a["type"] == "missing_timesheets"][0]
		self.assertGreaterEqual(len(agregada["res_ids"]), 2)
		action = self.env["project.project"].action_open_alert_record(
			agregada["res_model"], agregada["res_id"], agregada["res_ids"]
		)
		self.assertEqual(action["view_mode"], "list,form")
		self.assertEqual(action["domain"], [("id", "in", agregada["res_ids"])])

	def test_alerta_sin_plan_cubre_gris_y_aproximado(self):
		gris = self._make_project("Sin fechas", start=None, end=None)
		aproximado = self._make_project("Plan aproximado", start=-10, end=10)
		self._make_tasks(aproximado, total=2, done=1)
		alerts, _total = self._alerts()
		con_alerta = {a["project_id"] for a in alerts if a["type"] == "no_plan"}
		self.assertIn(gris.id, con_alerta)
		self.assertIn(aproximado.id, con_alerta, "el plan aproximado también necesita presión")

	def test_alerta_tarea_bloqueada(self):
		project = self._make_project("Con bloqueada")
		tarea = self._make_tasks(project, total=1)
		tarea.blocking_state = "blocked"
		tarea.blocked_since = fields.Datetime.now() - timedelta(days=10)
		alerts, _total = self._alerts()
		bloqueada = [a for a in alerts if a["type"] == "task_blocked"]
		self.assertTrue(bloqueada)
		self.assertEqual(bloqueada[0]["res_id"], tarea.id)

	def test_alerta_tarea_bloqueada_respeta_el_umbral(self):
		project = self._make_project("Recien bloqueada")
		tarea = self._make_tasks(project, total=1)
		tarea.blocking_state = "blocked"
		alerts, _total = self._alerts()
		self.assertFalse([a for a in alerts if a["type"] == "task_blocked"])

	# ------------------------------------------------------------------
	# Clave estable
	# ------------------------------------------------------------------

	def test_clave_no_depende_del_mensaje(self):
		project = self._make_project("Hito")
		milestone = self._make_milestones(project, [(-10, 50.0, False)])
		alerts, _total = self._alerts()
		alerta = [a for a in alerts if a["type"] == "milestone_overdue"][0]
		clave_original = alerta["key"]
		mensaje_original = alerta["message"]
		self.assertEqual(clave_original, f"milestone_overdue:project.milestone:{milestone.id}")
		# Se atrasa un día más: cambia el mensaje, no la clave.
		milestone.deadline = milestone.deadline - timedelta(days=1)
		alerts, _total = self._alerts()
		alerta = [a for a in alerts if a["type"] == "milestone_overdue"][0]
		self.assertNotEqual(alerta["message"], mensaje_original)
		self.assertEqual(alerta["key"], clave_original)

	# ------------------------------------------------------------------
	# Snooze
	# ------------------------------------------------------------------

	def _snooze_first(self, user):
		alerts, _total = self._alerts(user=user)
		alerta = alerts[0]
		self.env["project.dashboard.alert.snooze"].with_user(user).action_snooze_alert(
			alerta["type"], alerta["res_model"], alerta["res_id"]
		)
		return alerta

	def test_snooze_saca_la_alerta(self):
		project = self._make_project("Hito")
		self._make_milestones(project, [(-10, 50.0, False)])
		alerta = self._snooze_first(self.manager_user)
		alerts, _total = self._alerts()
		self.assertNotIn(alerta["key"], {a["key"] for a in alerts})

	def test_snooze_es_idempotente(self):
		project = self._make_project("Hito")
		self._make_milestones(project, [(-10, 50.0, False)])
		alerta = self._snooze_first(self.manager_user)
		Snooze = self.env["project.dashboard.alert.snooze"].with_user(self.manager_user)
		Snooze.action_snooze_alert(alerta["type"], alerta["res_model"], alerta["res_id"])
		self.assertEqual(
			Snooze.search_count([("alert_type", "=", alerta["type"])]),
			1,
			"silenciar dos veces no puede duplicar el registro",
		)

	def test_snooze_es_por_usuario(self):
		project = self._make_project("Hito")
		self._make_milestones(project, [(-10, 50.0, False)])
		alerta = self._snooze_first(self.manager_user)
		otras, _total = self._alerts(user=self.lead_user)
		self.assertIn(alerta["key"], {a["key"] for a in otras}, "el silencio es de quien lo pidió")

	def test_snooze_vencido_vuelve_a_mostrar(self):
		project = self._make_project("Hito")
		self._make_milestones(project, [(-10, 50.0, False)])
		alerta = self._snooze_first(self.manager_user)
		snooze = self.env["project.dashboard.alert.snooze"].search(
			[("alert_type", "=", alerta["type"]), ("res_id", "=", alerta["res_id"])]
		)
		snooze.snooze_until = fields.Datetime.now() - timedelta(days=1)
		alerts, _total = self._alerts()
		self.assertIn(alerta["key"], {a["key"] for a in alerts})

	def test_gc_limpia_los_vencidos(self):
		project = self._make_project("Hito")
		self._make_milestones(project, [(-10, 50.0, False)])
		alerta = self._snooze_first(self.manager_user)
		snooze = self.env["project.dashboard.alert.snooze"].search(
			[("alert_type", "=", alerta["type"]), ("res_id", "=", alerta["res_id"])]
		)
		snooze.snooze_until = fields.Datetime.now() - timedelta(days=1)
		self.env["project.dashboard.alert.snooze"]._gc_expired_snoozes()
		self.assertFalse(snooze.exists())

	# ------------------------------------------------------------------
	# Cap y orden
	# ------------------------------------------------------------------

	def test_cap_de_alertas(self):
		"""Más alertas que el tope: se devuelven las primeras y el total real."""
		for index in range(ALERT_LIMIT + 5):
			project = self._make_project(f"Sin plan {index}", start=None, end=None)
			self._make_tasks(project, total=1)
		alerts, total = self._alerts()
		self.assertEqual(len(alerts), ALERT_LIMIT)
		self.assertGreater(total, ALERT_LIMIT)

	def test_las_rojas_van_primero(self):
		rojo = self._make_project("Con hito vencido")
		self._make_milestones(rojo, [(-10, 50.0, False)])
		self._make_project("Sin plan", start=None, end=None)
		alerts, _total = self._alerts()
		self.assertEqual(alerts[0]["severity"], "danger")

	def test_dentro_de_la_severidad_manda_la_antiguedad(self):
		viejo = self._make_project("Hito viejo")
		self._make_milestones(viejo, [(-30, 50.0, False)])
		nuevo = self._make_project("Hito nuevo")
		self._make_milestones(nuevo, [(-2, 50.0, False)])
		alerts, _total = self._alerts()
		vencidos = [a for a in alerts if a["type"] == "milestone_overdue"]
		self.assertEqual(vencidos[0]["project_id"], viejo.id)
