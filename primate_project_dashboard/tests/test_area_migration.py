# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

"""El mapeo del Selection viejo a `primate.area`, probado sobre el MISMO código que corre la
migración real (`models/area_migration.py`), no sobre una copia.

Lo que se verifica no es "el campo quedó lleno" sino las decisiones de datos aceptadas, que son
la respuesta a "¿por qué este proyecto quedó sin área?":
mayoría de las tareas, empate y sin tareas -> vacío, code desconocido -> vacío + warning con ids.
Y el cierre por conteo, que es lo que detecta que algo se perdió por el camino.
"""

from odoo.tests.common import TransactionCase

from ..models.area_migration import TABLA_RESPALDO, migrar_area_por_code


class TestAreaMigration(TransactionCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.tecnica = cls.env.ref("primate_project_area.area_technical")
		cls.funcional = cls.env.ref("primate_project_area.area_functional")
		cls.admin = cls.env.ref("primate_project_area.area_admin")
		# La tabla la deja el pre-migrate. En una base recién instalada no existe, así que el
		# test la crea igual que el script: lo que se prueba es el post-migrate.
		cls.env.cr.execute(
			"""
			CREATE TABLE IF NOT EXISTS {} (
				modelo VARCHAR NOT NULL,
				res_id INTEGER NOT NULL,
				code VARCHAR NOT NULL
			)
			""".format(TABLA_RESPALDO)
		)
		cls.env.cr.execute("DELETE FROM {}".format(TABLA_RESPALDO))

	# ------------------------------------------------------------------ helpers
	def _proyecto(self, nombre, **values):
		"""Proyectos SIN área: si la tuvieran, las tareas la heredarían al crearse y el test
		estaría midiendo la herencia en vez de la migración."""
		return self.env["project.project"].create({"name": nombre, **values})

	def _tareas(self, project, cantidad):
		return self.env["project.task"].create(
			[{"name": "T%s" % i, "project_id": project.id} for i in range(cantidad)]
		)

	def _respaldar(self, modelo, records, code):
		self.env.cr.executemany(
			"INSERT INTO {} (modelo, res_id, code) VALUES (%s, %s, %s)".format(TABLA_RESPALDO),
			[(modelo, record.id, code) for record in records],
		)

	def _migrar(self):
		reporte = migrar_area_por_code(self.env.cr, self.env)
		# La migración escribe por SQL directo: sin esto el ORM sigue mostrando la caché vieja.
		self.env.invalidate_all()
		return reporte

	# ------------------------------------------------------------------ mapeo por code
	def test_los_tres_codes_resuelven_a_su_area(self):
		proyecto = self._proyecto("P")
		tecnicas = self._tareas(proyecto, 1)
		funcionales = self._tareas(proyecto, 1)
		admins = self._tareas(proyecto, 1)
		self._respaldar("project.task", tecnicas, "technical")
		self._respaldar("project.task", funcionales, "functional")
		self._respaldar("project.task", admins, "admin")

		reporte = self._migrar()

		self.assertEqual(tecnicas.area_id, self.tecnica)
		self.assertEqual(funcionales.area_id, self.funcional)
		self.assertEqual(admins.area_id, self.admin)
		self.assertEqual(reporte["project.task"], 3)

	def test_una_tarea_sin_respaldo_queda_sin_area(self):
		"""Área nula en el Selection viejo no es "la primera área": es sin área."""
		proyecto = self._proyecto("P")
		tarea = self._tareas(proyecto, 1)
		self._migrar()
		self.assertFalse(tarea.area_id)

	def test_un_code_desconocido_no_se_pierde_en_silencio(self):
		"""Dato viejo de una base donde alguien extendió el Selection."""
		proyecto = self._proyecto("P")
		huerfanas = self._tareas(proyecto, 2)
		self._respaldar("project.task", huerfanas, "comercial")

		with self.assertLogs(
			"odoo.addons.primate_project_dashboard.models.area_migration", "WARNING"
		) as registro:
			reporte = self._migrar()

		self.assertFalse(huerfanas.area_id, "no se mapea al azar")
		self.assertEqual(
			sorted(reporte["codes_desconocidos"]["comercial"]), sorted(huerfanas.ids)
		)
		self.assertIn("comercial", "\n".join(registro.output))
		for tarea in huerfanas:
			self.assertIn(str(tarea.id), "\n".join(registro.output), "el warning trae los ids")

	def test_el_empleado_mapea_igual_que_la_tarea(self):
		empleado = self.env["hr.employee"].create({"name": "Empleado migración"})
		self._respaldar("hr.employee", empleado, "functional")
		reporte = self._migrar()
		self.assertEqual(empleado.area_id, self.funcional)
		self.assertEqual(reporte["hr.employee"], 1)

	# ------------------------------------------------------------------ área del proyecto
	def test_el_proyecto_toma_el_area_mayoritaria_de_sus_tareas(self):
		proyecto = self._proyecto("Mayoría")
		mayoria = self._tareas(proyecto, 3)
		minoria = self._tareas(proyecto, 1)
		self._respaldar("project.task", mayoria, "technical")
		self._respaldar("project.task", minoria, "functional")

		self._migrar()

		self.assertEqual(proyecto.area_id, self.tecnica)

	def test_el_empate_no_se_desempata_inventando(self):
		proyecto = self._proyecto("Empate")
		mitad = self._tareas(proyecto, 2)
		otra = self._tareas(proyecto, 2)
		self._respaldar("project.task", mitad, "technical")
		self._respaldar("project.task", otra, "functional")

		self._migrar()

		self.assertFalse(proyecto.area_id, "2 contra 2 no elige ninguna")

	def test_un_proyecto_sin_tareas_queda_sin_area(self):
		proyecto = self._proyecto("Vacío")
		self._migrar()
		self.assertFalse(proyecto.area_id)

	def test_un_proyecto_con_area_cargada_a_mano_no_se_pisa(self):
		proyecto = self._proyecto("Ya cargado", area_id=self.admin.id)
		tareas = self._tareas(proyecto, 3)
		# Las tareas nacieron heredando 'admin'; se las fuerza a otra cosa para que la mayoría
		# apunte a un área distinta de la del proyecto.
		tareas.write({"area_id": False})
		self._respaldar("project.task", tareas, "technical")

		self._migrar()

		self.assertEqual(tareas.area_id, self.tecnica)
		self.assertEqual(proyecto.area_id, self.admin, "lo cargado a mano manda")

	# ------------------------------------------------------------------ cierre por conteo
	def test_el_reporte_cierra_por_conteo(self):
		proyecto = self._proyecto("Cierre")
		buenas = self._tareas(proyecto, 4)
		malas = self._tareas(proyecto, 2)
		empleado = self.env["hr.employee"].create({"name": "Empleado cierre"})
		self._respaldar("project.task", buenas, "technical")
		self._respaldar("project.task", malas, "no_existe")
		self._respaldar("hr.employee", empleado, "admin")

		with self.assertLogs(
			"odoo.addons.primate_project_dashboard.models.area_migration", "WARNING"
		):
			reporte = self._migrar()

		self.assertEqual(reporte["respaldo_total"], 7)
		self.assertEqual(reporte["mapeados"], 5)
		self.assertEqual(reporte["desconocidos"], 2)
		self.assertTrue(reporte["cierra"], "respaldo == mapeados + desconocidos")

	def test_sin_respaldo_no_hace_nada_y_cierra(self):
		reporte = self._migrar()
		self.assertEqual(reporte["respaldo_total"], 0)
		self.assertTrue(reporte["cierra"])
