# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

"""La regla de herencia proyecto -> tarea, que es lo único con lógica del módulo.

Lo que se prueba no es "el campo existe" sino la promesa: la tarea hereda, y una edición manual
NO se pierde al mover la tarea de proyecto. Ese es el bug que tendría un related o un compute
stored editable, y por el que la regla está escrita a mano.
"""

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAreaInheritance(TransactionCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.tecnica = cls.env.ref("primate_project_area.area_technical")
		cls.funcional = cls.env.ref("primate_project_area.area_functional")
		cls.Task = cls.env["project.task"]
		cls.proyecto_tecnico = cls.env["project.project"].create(
			{"name": "Proyecto técnico", "area_id": cls.tecnica.id}
		)
		cls.proyecto_funcional = cls.env["project.project"].create(
			{"name": "Proyecto funcional", "area_id": cls.funcional.id}
		)
		cls.proyecto_sin_area = cls.env["project.project"].create({"name": "Proyecto sin área"})

	def _tarea(self, project, **values):
		return self.Task.create({"name": "Tarea", "project_id": project.id, **values})

	# ------------------------------------------------------------------ crear
	def test_al_crear_hereda_el_area_del_proyecto(self):
		self.assertEqual(self._tarea(self.proyecto_tecnico).area_id, self.tecnica)

	def test_al_crear_un_area_explicita_no_se_pisa(self):
		tarea = self._tarea(self.proyecto_tecnico, area_id=self.funcional.id)
		self.assertEqual(tarea.area_id, self.funcional)

	def test_al_crear_en_proyecto_sin_area_queda_vacia(self):
		self.assertFalse(self._tarea(self.proyecto_sin_area).area_id)

	def test_al_crear_en_lote_cada_una_hereda_la_suya(self):
		"""create es model_create_multi: el lote no puede resolver una sola área para todos."""
		tareas = self.Task.create(
			[
				{"name": "T1", "project_id": self.proyecto_tecnico.id},
				{"name": "T2", "project_id": self.proyecto_funcional.id},
				{"name": "T3", "project_id": self.proyecto_tecnico.id, "area_id": self.funcional.id},
			]
		)
		self.assertEqual(tareas.mapped("area_id"), self.tecnica | self.funcional)
		self.assertEqual(tareas[0].area_id, self.tecnica)
		self.assertEqual(tareas[1].area_id, self.funcional)
		self.assertEqual(tareas[2].area_id, self.funcional)

	# ------------------------------------------------------------------ mover
	def test_al_mover_re_hereda_si_no_la_habian_tocado(self):
		tarea = self._tarea(self.proyecto_tecnico)
		tarea.project_id = self.proyecto_funcional
		self.assertEqual(tarea.area_id, self.funcional)

	def test_al_mover_se_respeta_el_area_editada_a_mano(self):
		"""EL caso que justifica no usar related ni compute stored."""
		tarea = self._tarea(self.proyecto_tecnico)
		tarea.area_id = self.funcional          # decisión humana explícita
		tarea.project_id = self.proyecto_funcional
		self.assertEqual(
			tarea.area_id, self.funcional, "una edición manual no se pierde al mover la tarea"
		)

	def test_al_mover_a_un_proyecto_sin_area_la_heredada_se_limpia(self):
		tarea = self._tarea(self.proyecto_tecnico)
		tarea.project_id = self.proyecto_sin_area
		self.assertFalse(tarea.area_id)

	def test_al_mover_en_lote_cada_tarea_decide_por_separado(self):
		heredada = self._tarea(self.proyecto_tecnico)
		editada = self._tarea(self.proyecto_tecnico)
		editada.area_id = self.funcional
		(heredada | editada).write({"project_id": self.proyecto_sin_area.id})
		self.assertFalse(heredada.area_id)
		self.assertEqual(editada.area_id, self.funcional)

	def test_mover_con_area_explicita_en_el_mismo_write_manda_el_area(self):
		tarea = self._tarea(self.proyecto_tecnico)
		tarea.write({"project_id": self.proyecto_funcional.id, "area_id": self.tecnica.id})
		self.assertEqual(tarea.area_id, self.tecnica)

	# ------------------------------------------------------------------ no-cascada
	def test_cambiar_el_area_del_proyecto_no_recascadea_a_las_tareas(self):
		"""Decisión explícita: lo reporta el rol Gestor de Proyectos, no lo reescribe el ORM."""
		tarea = self._tarea(self.proyecto_tecnico)
		self.proyecto_tecnico.area_id = self.funcional
		self.assertEqual(tarea.area_id, self.tecnica)

	# ------------------------------------------------------------------ el modelo
	def test_el_code_es_unico(self):
		with self.assertRaises(Exception):
			with self.env.cr.savepoint():
				self.env["primate.area"].create({"name": "Otra", "code": "technical"})

	def test_el_code_no_admite_espacios(self):
		with self.assertRaises(ValidationError):
			self.env["primate.area"].create({"name": "Otra", "code": "con espacio"})

	def test_by_code_no_inventa_un_area(self):
		self.assertEqual(self.env["primate.area"]._by_code("technical"), self.tecnica)
		self.assertFalse(self.env["primate.area"]._by_code("no_existe"))
		self.assertFalse(self.env["primate.area"]._by_code(False))
