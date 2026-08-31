# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
"""El dashboard con acceso PARCIAL a las horas cargadas.

Hermano del caso de las líneas de venta, pero más peligroso, porque no revienta.

`hr_timesheet.group_hr_timesheet_user` se llama, textual, "Usuario: solo sus hojas de
horas", y su record rule tapa las horas de los compañeros. La ACL del modelo la pasa igual,
así que el chequeo viejo -`has_access("read")`- daba verde y después todo se calculaba con
`_read_group`, que filtra en silencio: las horas consumidas del proyecto salían contando
SOLO las del usuario y se mostraban como el total del proyecto.

Es el perfil del PM, no un caso de laboratorio: el propio harness de tests le da ese grupo.

Y las dos alertas que dependen de horas quedaban peor todavía. La de "sin actividad" veía
un proyecto quieto porque no veía el trabajo ajeno, y la de "timesheets sin cargar" acusaba
a compañeros de no registrar horas mirando datos que el usuario no tiene permitido ver.
"""
from .common import DashboardCommon


class TestTimesheetAccess(DashboardCommon):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Un segundo empleado, con su propio usuario: sus horas son las "ajenas".
		cls.otro_usuario = cls.env["res.users"].create(
			{
				"name": "Otro Trabajador",
				"login": "otro_trabajador",
				"group_ids": [
					(6, 0, [
						cls.env.ref("base.group_user").id,
						cls.env.ref("hr_timesheet.group_hr_timesheet_user").id,
					])
				],
			}
		)
		cls.otro_empleado = cls.env["hr.employee"].create(
			{"name": "Otro Empleado", "user_id": cls.otro_usuario.id, "hourly_cost": 30.0}
		)

	def _proyecto_con_horas_de_dos(self):
		"""10 horas del PM y 40 de otra persona: el total real del proyecto es 50."""
		project = self._make_project("Horas compartidas")
		self._add_timesheet(project, 10.0, employee=self.employee)
		self._add_timesheet(project, 40.0, employee=self.otro_empleado)
		return project

	def _solo_sus_horas(self, user):
		"""Deja al usuario con 'solo sus hojas de horas'."""
		user.write({
			"group_ids": [
				(3, self.env.ref("hr_timesheet.group_timesheet_manager").id),
				(4, self.env.ref("hr_timesheet.group_hr_timesheet_user").id),
			]
		})
		return user

	# ------------------------------------------------------------------
	# 1. El número incompleto
	# ------------------------------------------------------------------

	def test_con_visibilidad_parcial_las_horas_son_sin_dato(self):
		"""Antes devolvía 10.0 —solo las propias— como si fuera el total de 50."""
		project = self._proyecto_con_horas_de_dos()
		user = self._solo_sus_horas(self.pm_user)

		proyecto_usuario = project.with_user(user)
		self.assertFalse(proyecto_usuario._primate_can_read_timesheets())
		self.assertIsNone(proyecto_usuario._primate_consumed_hours_map()[project.id])

	def test_la_fila_del_dashboard_no_miente(self):
		project = self._proyecto_con_horas_de_dos()
		user = self._solo_sus_horas(self.pm_user)

		datos = self.env["project.project"].with_user(user).get_dashboard_data({"period": "all"})
		fila = next(row for row in datos["projects"] if row["id"] == project.id)

		self.assertIsNone(fila["consumed_hours"])
		self.assertFalse(datos["config"]["can_see_timesheet_data"])

	def test_el_margen_no_se_infla_con_un_costo_incompleto(self):
		"""Costo parcial = margen inflado. Preferimos no mostrarlo."""
		project = self._proyecto_con_horas_de_dos()
		self._make_sale_order(project)
		user = self._solo_sus_horas(self.manager_user)

		datos = self.env["project.project"].with_user(user).get_dashboard_data({"period": "all"})
		fila = next(row for row in datos["projects"] if row["id"] == project.id)

		self.assertIsNone(fila["margin_estimate"])

	# ------------------------------------------------------------------
	# 2. Las alertas falsas
	# ------------------------------------------------------------------

	def test_no_acusa_a_nadie_de_no_cargar_horas(self):
		"""La alerta miraba horas ajenas invisibles y concluía que no existían."""
		project = self._proyecto_con_horas_de_dos()
		self._make_tasks(project, total=2)
		project.task_ids.write({"user_ids": [(4, self.otro_usuario.id)]})
		user = self._solo_sus_horas(self.pm_user)

		alertas = project.with_user(user)._primate_alerts_missing_timesheets(self.today)

		self.assertEqual(alertas, [], "sin ver las horas ajenas no se puede afirmar que faltan")

	# ------------------------------------------------------------------
	# 3. Que el usuario legítimo no pierda nada
	# ------------------------------------------------------------------

	def test_con_acceso_completo_el_total_es_el_real(self):
		project = self._proyecto_con_horas_de_dos()

		# lead_user tiene group_timesheet_manager por el harness: ve todo.
		proyecto_usuario = project.with_user(self.lead_user)
		self.assertTrue(proyecto_usuario._primate_can_read_timesheets())
		self.assertEqual(proyecto_usuario._primate_consumed_hours_map()[project.id], 50.0)

	def test_un_proyecto_sin_horas_no_queda_marcado_como_sin_dato(self):
		"""Cero horas cargadas es un cero real, no una restricción de permisos."""
		project = self._make_project("Sin horas")
		user = self._solo_sus_horas(self.pm_user)

		proyecto_usuario = project.with_user(user)
		self.assertTrue(proyecto_usuario._primate_can_read_timesheets())
		self.assertEqual(proyecto_usuario._primate_consumed_hours_map()[project.id], 0.0)
