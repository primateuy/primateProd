# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import DashboardCommon


@tagged("post_install", "-at_install")
class TestProgressPlanned(DashboardCommon):
	"""Interpolación del avance planificado (sección 1.7)."""

	def _plan(self, project):
		return project._primate_progress_planned_map()[project.id]

	def test_con_hitos_interpola_entre_los_dos(self):
		project = self._make_project(start=-10, end=10)
		self._make_milestones(project, [(-5, 25.0, True), (5, 75.0, False)])
		plan = self._plan(project)
		# Hoy está a mitad de camino entre los dos hitos: 25 + 50/2.
		self.assertEqual(plan["planned"], 50.0)
		self.assertTrue(plan["has_plan"])
		self.assertFalse(plan["estimated"])

	def test_sin_hitos_es_plan_aproximado(self):
		"""Con fechas pero sin hitos: recta entre inicio y fin, marcado como aproximado."""
		project = self._make_project(start=-10, end=10)
		plan = self._plan(project)
		self.assertEqual(plan["planned"], 50.0)
		self.assertTrue(plan["estimated"])
		self.assertFalse(plan["has_plan"])
		# Sigue habiendo curva: la fila dibuja marcador y no cae en gris.
		self.assertTrue(plan["has_curve"])

	def test_un_solo_hito_tambien_es_aproximado(self):
		project = self._make_project(start=-10, end=10)
		self._make_milestones(project, [(0, 40.0, False)])
		plan = self._plan(project)
		self.assertTrue(plan["estimated"])
		self.assertEqual(plan["planned"], 50.0)

	def test_hitos_vencidos_siguen_contando(self):
		"""Un hito pasado es el ancla izquierda de la interpolación."""
		project = self._make_project(start=-40, end=40)
		self._make_milestones(project, [(-20, 30.0, False), (20, 70.0, False)])
		self.assertEqual(self._plan(project)["planned"], 50.0)

	def test_curva_termina_en_100_con_fin_posterior(self):
		"""Hitos que topan en 70%: el tramo final interpola hasta el 100% en la fecha fin."""
		project = self._make_project(start=-40, end=20)
		self._make_milestones(project, [(-20, 40.0, True), (-10, 70.0, False)])
		# De -10 a +20 hay 30 días y hoy pasaron 10: 70 + 30*(10/30) = 80.
		self.assertEqual(self._plan(project)["planned"], 80.0)

	def test_curva_ancla_en_el_ultimo_hito_si_es_posterior_al_fin(self):
		"""Fin anterior al último hito: el ancla es el hito y el salto a 100 cae ahí."""
		project = self._make_project(start=-40, end=-5)
		self._make_milestones(project, [(-20, 40.0, True), (10, 70.0, False)])
		# Hoy está entre los dos hitos: 40 + 30*(20/30) = 60.
		self.assertEqual(self._plan(project)["planned"], 60.0)
		# Pasado el último hito el plan exige el 100%, no se queda en 70.
		future = project._primate_progress_planned_map(today=self.today.replace())
		self.assertEqual(future[project.id]["planned"], 60.0)

	def test_pasado_el_ancla_el_plan_pide_100(self):
		project = self._make_project(start=-40, end=-5)
		self._make_milestones(project, [(-30, 40.0, True), (-10, 70.0, False)])
		self.assertEqual(self._plan(project)["planned"], 100.0)

	def test_sin_fechas_no_hay_curva(self):
		project = self._make_project(start=None, end=None)
		plan = self._plan(project)
		self.assertIsNone(plan["planned"])
		self.assertFalse(plan["has_curve"])
		self.assertFalse(plan["has_plan"])

	def test_solo_fecha_de_inicio_no_alcanza(self):
		project = self._make_project(start=-10, end=None)
		self.assertFalse(self._plan(project)["has_curve"])

	def test_antes_del_inicio_el_plan_pide_cero(self):
		project = self._make_project(start=10, end=40)
		self.assertEqual(self._plan(project)["planned"], 0.0)

	# ------------------------------------------------------------------
	# Avance real
	# ------------------------------------------------------------------

	def test_avance_real_pondera_por_horas(self):
		project = self._make_project()
		self._make_tasks(project, total=2, done=0, allocated=10.0)
		grande = self.env["project.task"].create(
			{"name": "Grande", "project_id": project.id, "allocated_hours": 80.0}
		)
		grande.state = "1_done"
		# 80 de 100 horas cerradas, aunque sean 1 de 3 tareas.
		self.assertEqual(self._metrics(project)["progress_real"], 80.0)

	def test_avance_real_sin_horas_cae_a_conteo(self):
		project = self._make_project()
		self._make_tasks(project, total=4, done=1, allocated=0.0)
		self.assertEqual(self._metrics(project)["progress_real"], 25.0)

	def test_avance_por_horas_capea_por_tarea(self):
		"""Una tarea pasada de horas no puede inflar el avance del proyecto."""
		self._set_param("progress_method", "hours")
		project = self._make_project()
		tasks = self._make_tasks(project, total=2, done=0, allocated=10.0)
		self._add_timesheet(project, 100.0)
		tasks[0].timesheet_ids = [
			(
				0,
				0,
				{
					"name": "Exceso",
					"project_id": project.id,
					"employee_id": self.employee.id,
					"unit_amount": 100.0,
					"date": self.today,
				},
			)
		]
		# La tarea desbordada aporta como mucho sus 10 horas: 10 de 20 = 50%.
		self.assertLessEqual(self._metrics(project)["progress_real"], 50.0)

	# ------------------------------------------------------------------
	# Constraint de monotonía
	# ------------------------------------------------------------------

	def test_hitos_deben_crecer_con_la_fecha(self):
		project = self._make_project()
		self._make_milestones(project, [(-10, 50.0, False)])
		with self.assertRaises(ValidationError):
			self._make_milestones(project, [(10, 20.0, False)])

	def test_avance_planificado_fuera_de_rango(self):
		project = self._make_project()
		with self.assertRaises(ValidationError):
			self._make_milestones(project, [(0, 150.0, False)])
