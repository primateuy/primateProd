# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo.tests.common import tagged

from .common import DashboardCommon


@tagged("post_install", "-at_install")
class TestHealthState(DashboardCommon):
	"""Reglas del semáforo (sección 1.6), con sus casos borde."""

	def _project_with_plan(self, real_progress):
		"""Proyecto cuyo plan pide exactamente 50% hoy y avanzó `real_progress`%.

		Los hitos van a -10 y +10 días con 20% y 80%: hoy cae justo en el medio. Las
		fechas del proyecto son más anchas para que el ancla inicial no colisione con
		el primer hito.
		"""
		project = self._make_project(start=-20, end=20)
		self._make_milestones(project, [(-10, 20.0, True), (10, 80.0, False)])
		# 20 tareas iguales: cada una vale 5 puntos, así se pueden pedir bordes como 45%.
		self._make_tasks(project, total=20, done=int(real_progress / 5))
		return project

	# ------------------------------------------------------------------
	# Verde
	# ------------------------------------------------------------------

	def test_on_track_sin_desvios(self):
		project = self._project_with_plan(real_progress=60)
		self.assertEqual(self._health(project), "on_track")

	def test_on_track_exige_plan(self):
		"""Un verde sin plan sería un falso verde: sin curva va a no_plan."""
		project = self._make_project(start=None, end=None)
		self._make_tasks(project, total=4, done=4)
		self.assertEqual(self._health(project), "no_plan")

	# ------------------------------------------------------------------
	# Amarillo: brecha de avance
	# ------------------------------------------------------------------

	def test_at_risk_borde_justo_en_el_umbral(self):
		"""Brecha de exactamente 5pp NO alcanza: la regla pide estrictamente menor."""
		project = self._project_with_plan(real_progress=45)
		self.assertEqual(self._metrics(project)["progress_planned"], 50.0)
		self.assertEqual(self._health(project), "on_track")

	def test_at_risk_un_punto_pasado_el_umbral(self):
		project = self._project_with_plan(real_progress=40)
		self.assertEqual(self._health(project), "at_risk")

	# ------------------------------------------------------------------
	# Rojo: brecha de avance
	# ------------------------------------------------------------------

	def test_critical_borde_justo_en_el_umbral(self):
		"""Brecha de exactamente 15pp todavía es amarillo."""
		project = self._project_with_plan(real_progress=35)
		self.assertEqual(self._health(project), "at_risk")

	def test_critical_un_punto_pasado_el_umbral(self):
		project = self._project_with_plan(real_progress=30)
		self.assertEqual(self._health(project), "critical")

	# ------------------------------------------------------------------
	# Reglas de horas
	# ------------------------------------------------------------------

	def test_at_risk_por_horas(self):
		"""80% de horas consumidas con avance por debajo del 80%."""
		project = self._project_with_plan(real_progress=50)
		self._make_sale_order(project, hours=100.0)
		self._add_timesheet(project, 80.0)
		self.assertEqual(self._health(project), "at_risk")

	def test_critical_por_horas(self):
		"""90% de horas consumidas con avance por debajo del 70%."""
		project = self._project_with_plan(real_progress=50)
		self._make_sale_order(project, hours=100.0)
		self._add_timesheet(project, 90.0)
		self.assertEqual(self._health(project), "critical")

	def test_horas_borde_no_dispara(self):
		"""89% de consumo se queda corto del umbral rojo."""
		project = self._project_with_plan(real_progress=50)
		self._make_sale_order(project, hours=100.0)
		self._add_timesheet(project, 89.0)
		self.assertEqual(self._health(project), "at_risk")

	# ------------------------------------------------------------------
	# Regla de hito vencido
	# ------------------------------------------------------------------

	def test_critical_por_hito_vencido(self):
		project = self._make_project(start=-30, end=30)
		self._make_milestones(project, [(-30, 10.0, True), (-4, 20.0, False)])
		self._make_tasks(project, total=10, done=9)
		self.assertEqual(self._health(project), "critical")

	def test_hito_vencido_borde_no_dispara(self):
		"""Exactamente N días de atraso no alcanza: la regla pide más de N."""
		project = self._make_project(start=-30, end=30)
		self._make_milestones(project, [(-30, 10.0, True), (-3, 20.0, False)])
		self._make_tasks(project, total=10, done=9)
		self.assertEqual(self._metrics(project)["overdue_milestone_days"], 3)
		self.assertNotEqual(self._health(project), "critical")

	# ------------------------------------------------------------------
	# Orden de evaluación
	# ------------------------------------------------------------------

	def test_no_plan_no_esconde_un_rojo_por_horas(self):
		"""Sin plan, pero quemando el presupuesto: manda el rojo, no el gris."""
		project = self._make_project(start=-30, end=None)
		self._make_tasks(project, total=10, done=0)
		self._make_sale_order(project, hours=10.0)
		self._add_timesheet(project, 10.0)
		metrics = self._metrics(project)
		self.assertFalse(metrics["has_plan_curve"])
		self.assertEqual(metrics["health_state"], "critical")

	def test_no_plan_no_esconde_un_hito_vencido(self):
		project = self._make_project(start=None, end=None)
		self._make_milestones(project, [(-10, 0.0, False)])
		self._make_tasks(project, total=2, done=0)
		self.assertEqual(self._health(project), "critical")

	def test_no_plan_cuando_no_hay_nada_que_reprochar(self):
		project = self._make_project(start=None, end=None)
		self._make_tasks(project, total=2, done=1)
		self.assertEqual(self._health(project), "no_plan")

	# ------------------------------------------------------------------
	# Umbrales configurables
	# ------------------------------------------------------------------

	def test_umbrales_salen_de_la_configuracion(self):
		"""Mismo proyecto, distinto umbral: el estado tiene que cambiar."""
		project = self._project_with_plan(real_progress=40)
		self.assertEqual(self._health(project), "at_risk")
		# Con el umbral rojo en 5pp, la misma brecha de 10pp pasa a crítico.
		self._set_param("health_red_progress_gap", 5)
		self.assertEqual(self._health(project), "critical")
		# Y con el amarillo en 20pp deja de haber alerta.
		self._set_param("health_red_progress_gap", 15)
		self._set_param("health_yellow_progress_gap", 20)
		self.assertEqual(self._health(project), "on_track")

	def test_umbral_de_hito_vencido_configurable(self):
		project = self._make_project(start=-30, end=30)
		self._make_milestones(project, [(-30, 10.0, True), (-3, 20.0, False)])
		self._make_tasks(project, total=10, done=9)
		self.assertNotEqual(self._health(project), "critical")
		self._set_param("health_milestone_overdue_days", 1)
		self.assertEqual(self._health(project), "critical")

	# ------------------------------------------------------------------
	# Campo almacenado
	# ------------------------------------------------------------------

	def test_health_state_almacenado_es_filtrable(self):
		project = self._project_with_plan(real_progress=30)
		project.action_recompute_health_state()
		self.assertEqual(project.health_state, "critical")
		found = self.env["project.project"].search(
			[("id", "=", project.id), ("health_state", "=", "critical")]
		)
		self.assertEqual(found, project)
