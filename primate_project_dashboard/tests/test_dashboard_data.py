# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo.tests.common import tagged

from .common import DashboardCommon


@tagged("post_install", "-at_install")
class TestDashboardData(DashboardCommon):
	"""El RPC único: perfiles de seguridad, nulls, filtros y paginación."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.Project = cls.env["project.project"]
		# Usuario sin acceso a ventas ni a timesheets, para la degradación.
		cls.blind_user = cls.env["res.users"].create(
			{
				"name": "sin_permisos",
				"login": "sin_permisos",
				"password": "sin_permisos",
				"group_ids": [
					(
						6,
						0,
						[
							cls.env.ref("base.group_user").id,
							cls.env.ref("project.group_project_user").id,
							cls.env.ref("primate_project_dashboard.group_dashboard_area_lead").id,
						],
					)
				],
			}
		)

	def _rows_by_name(self, data):
		return {row["name"]: row for row in data["projects"]}

	def _setup_portfolio(self):
		"""Tres proyectos: uno con SO y plan, uno sin plan, uno de otro responsable."""
		con_plan = self._make_project("Con plan", start=-10, end=10, user=self.pm_user)
		self._make_milestones(con_plan, [(-5, 25.0, True), (5, 75.0, False)])
		self._make_tasks(con_plan, total=10, done=6)
		self._make_sale_order(con_plan, hours=100.0)
		self._add_timesheet(con_plan, 40.0)

		sin_plan = self._make_project("Sin plan", start=None, end=None, user=self.pm_user)
		self._make_tasks(sin_plan, total=4, done=1)
		self._add_timesheet(sin_plan, 10.0)

		ajeno = self._make_project("De otro", start=-10, end=10, user=self.lead_user)
		self._make_milestones(ajeno, [(-5, 25.0, True), (5, 75.0, False)])
		self._make_tasks(ajeno, total=10, done=6)
		return con_plan, sin_plan, ajeno

	# ------------------------------------------------------------------
	# Perfiles
	# ------------------------------------------------------------------

	def test_direccion_ve_margen(self):
		con_plan, _sin_plan, _ajeno = self._setup_portfolio()
		data = self.Project.with_user(self.manager_user).get_dashboard_data({"period": "all"})
		self.assertTrue(data["config"]["can_see_margin"])
		row = self._rows_by_name(data)["Con plan"]
		self.assertIsNotNone(row["margin_estimate"])
		self.assertIsNotNone(data["kpis"]["margin_estimate"])

	def test_lider_no_ve_margen(self):
		self._setup_portfolio()
		data = self.Project.with_user(self.lead_user).get_dashboard_data({"period": "all"})
		self.assertFalse(data["config"]["can_see_margin"])
		self.assertIsNone(data["kpis"]["margin_estimate"])
		for row in data["projects"]:
			self.assertIsNone(row["margin_estimate"])

	def test_pm_solo_ve_sus_proyectos(self):
		self._setup_portfolio()
		data = self.Project.with_user(self.pm_user).get_dashboard_data({"period": "all"})
		names = set(self._rows_by_name(data))
		self.assertIn("Con plan", names)
		self.assertNotIn("De otro", names)

	def test_lider_ve_todo_el_portafolio(self):
		self._setup_portfolio()
		data = self.Project.with_user(self.lead_user).get_dashboard_data({"period": "all"})
		names = set(self._rows_by_name(data))
		self.assertIn("Con plan", names)
		self.assertIn("De otro", names)

	# ------------------------------------------------------------------
	# "Sin dato" nunca es cero
	# ------------------------------------------------------------------

	def test_sin_permisos_devuelve_null_no_cero(self):
		self._setup_portfolio()
		data = self.Project.with_user(self.blind_user).get_dashboard_data({"period": "all"})
		self.assertFalse(data["config"]["can_see_timesheet_data"])
		for row in data["projects"]:
			self.assertIsNone(row["consumed_hours"], "las horas consumidas no son cero, son sin dato")
		self.assertIsNone(data["kpis"]["hours_deviation"])

	def test_proyecto_sin_orden_de_venta(self):
		"""Sin SO no hay horas vendidas ni margen: null, no cero (sección 1.10)."""
		_con_plan, sin_plan, _ajeno = self._setup_portfolio()
		data = self.Project.with_user(self.manager_user).get_dashboard_data({"period": "all"})
		row = self._rows_by_name(data)[sin_plan.name]
		self.assertIsNone(row["sold_hours"])
		self.assertIsNone(row["margin_estimate"])
		self.assertFalse(row["has_sale_order"])
		# Pero las horas consumidas sí existen: son un dato real.
		self.assertEqual(row["consumed_hours"], 10.0)

	def test_proyectos_sin_so_excluidos_de_los_kpis(self):
		"""El margen del portafolio no puede diluirse con proyectos que no venden."""
		con_plan, sin_plan, _ajeno = self._setup_portfolio()
		data = self.Project.with_user(self.manager_user).get_dashboard_data({"period": "all"})
		rows = self._rows_by_name(data)
		self.assertIsNone(rows[sin_plan.name]["margin_estimate"])
		# El KPI es exactamente el margen del único proyecto que sí tiene SO.
		self.assertAlmostEqual(
			data["kpis"]["margin_estimate"], rows[con_plan.name]["margin_estimate"], places=2
		)

	def test_proyecto_sin_plan_fuera_del_cumplimiento(self):
		con_plan, sin_plan, _ajeno = self._setup_portfolio()
		data = self.Project.with_user(self.manager_user).get_dashboard_data({"period": "all"})
		rows = self._rows_by_name(data)
		self.assertIsNone(rows[sin_plan.name]["progress_planned"])
		self.assertEqual(rows[sin_plan.name]["health_state"], "no_plan")
		self.assertIsNotNone(data["kpis"]["plan_compliance"])

	# ------------------------------------------------------------------
	# Filtros
	# ------------------------------------------------------------------

	def test_filtro_solo_en_riesgo(self):
		self._setup_portfolio()
		rojo = self._make_project("En riesgo", start=-10, end=10, user=self.pm_user)
		self._make_milestones(rojo, [(-5, 25.0, True), (5, 75.0, False)])
		self._make_tasks(rojo, total=10, done=0)
		data = self.Project.with_user(self.manager_user).get_dashboard_data(
			{"period": "all", "only_at_risk": True}
		)
		self.assertTrue(data["projects"])
		for row in data["projects"]:
			self.assertEqual(row["health_state"], "critical")

	def test_filtro_por_responsable_y_cliente(self):
		self._setup_portfolio()
		Dashboard = self.Project.with_user(self.manager_user)
		por_user = Dashboard.get_dashboard_data({"period": "all", "user_id": self.lead_user.id})
		self.assertEqual(set(self._rows_by_name(por_user)), {"De otro"})
		por_partner = Dashboard.get_dashboard_data(
			{"period": "all", "partner_id": self.partner.id}
		)
		self.assertTrue(por_partner["projects"])

	def test_filtro_por_area(self):
		self._setup_portfolio()
		otro = self._make_project("Solo funcional", user=self.pm_user)
		self._make_tasks(otro, total=2, area="functional")
		data = self.Project.with_user(self.manager_user).get_dashboard_data(
			{"period": "all", "area": "functional"}
		)
		self.assertEqual(set(self._rows_by_name(data)), {"Solo funcional"})

	def test_dashboard_vacio_no_rompe(self):
		data = self.Project.with_user(self.manager_user).get_dashboard_data(
			{"period": "all", "user_id": self.blind_user.id}
		)
		self.assertEqual(data["projects"], [])
		self.assertEqual(data["kpis"]["active_projects"], 0)
		self.assertIsNone(data["kpis"]["plan_compliance"])
		self.assertEqual(len(data["areas"]), 3)

	# ------------------------------------------------------------------
	# Paginación
	# ------------------------------------------------------------------

	def test_paginacion_no_repite_filas(self):
		for index in range(5):
			project = self._make_project(f"Paginado {index}", user=self.pm_user)
			self._make_tasks(project, total=2, done=1)
		Dashboard = self.Project.with_user(self.manager_user)
		primera = Dashboard.get_dashboard_data({"period": "all", "limit": 2})
		segunda = Dashboard.get_dashboard_data({"period": "all", "limit": 2, "offset": 2})
		self.assertEqual(len(primera["projects"]), 2)
		ids_primera = {row["id"] for row in primera["projects"]}
		ids_segunda = {row["id"] for row in segunda["projects"]}
		self.assertFalse(ids_primera & ids_segunda)

	def test_kpis_y_areas_invariantes_entre_paginas(self):
		"""Paginar no puede cambiar lo que dice el portafolio."""
		for index in range(5):
			project = self._make_project(f"Paginado {index}", user=self.pm_user)
			self._make_tasks(project, total=2, done=1)
		Dashboard = self.Project.with_user(self.manager_user)
		primera = Dashboard.get_dashboard_data({"period": "all", "limit": 2})
		segunda = Dashboard.get_dashboard_data({"period": "all", "limit": 2, "offset": 2})
		self.assertEqual(primera["kpis"], segunda["kpis"])
		self.assertEqual(primera["areas"], segunda["areas"])
		self.assertEqual(primera["projects_total"], segunda["projects_total"])
		self.assertGreater(primera["projects_total"], len(primera["projects"]))

	# ------------------------------------------------------------------
	# Carga por área
	# ------------------------------------------------------------------

	def test_tarjetas_de_area(self):
		project = self._make_project("Con areas", user=self.pm_user)
		self._make_tasks(project, total=3, area="technical", deadline=2)
		self._make_tasks(project, total=2, area="functional", deadline=2)
		tarea = self._make_tasks(project, total=1, area="admin")
		tarea.blocking_state = "blocked"
		data = self.Project.with_user(self.manager_user).get_dashboard_data({"period": "all"})
		areas = {area["area"]: area for area in data["areas"]}
		self.assertEqual(areas["technical"]["open_tasks"], 3)
		self.assertEqual(areas["functional"]["open_tasks"], 2)
		self.assertEqual(areas["admin"]["blocked_tasks"], 1)

	def test_capacidad_sin_equipo_es_sin_dato(self):
		project = self._make_project("Sin equipo", user=self.pm_user)
		self._make_tasks(project, total=2, area="technical", deadline=2)
		data = self.Project.with_user(self.manager_user).get_dashboard_data({"period": "all"})
		areas = {area["area"]: area for area in data["areas"]}
		self.assertIsNone(areas["technical"]["capacity_ratio"], "sin empleados no hay 0%, hay '—'")

	def test_capacidad_visible_sin_permisos_de_rrhh(self):
		"""El agregado por área no expone datos individuales: el líder tiene que verlo."""
		self.employee.area = "technical"
		project = self._make_project("Con equipo", user=self.pm_user)
		self._make_tasks(project, total=2, area="technical", allocated=4.0, deadline=2)
		self.assertFalse(self.env["hr.employee"].with_user(self.blind_user).has_access("read"))
		data = self.Project.with_user(self.blind_user).get_dashboard_data({"period": "all"})
		areas = {area["area"]: area for area in data["areas"]}
		self.assertIsNotNone(areas["technical"]["capacity_ratio"])
		# Y nada por empleado viaja en el payload.
		for area in data["areas"]:
			self.assertNotIn("employee_ids", area)

	def test_accion_de_la_tarjeta_filtra_las_tareas(self):
		project = self._make_project("Con bloqueada", user=self.pm_user)
		tareas = self._make_tasks(project, total=2, area="technical")
		tareas[0].blocking_state = "blocked"
		action = self.Project.with_user(self.manager_user).action_open_area_tasks(
			"technical", "blocked", {"period": "all"}
		)
		self.assertEqual(action["res_model"], "project.task")
		encontradas = self.env["project.task"].search(action["domain"])
		self.assertIn(tareas[0], encontradas)
		self.assertNotIn(tareas[1], encontradas)
