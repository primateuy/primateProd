# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo.tests.common import tagged

from ..models.project_task import WAITING_STATE
from .common import DashboardCommon


@tagged("post_install", "-at_install")
class TestBlockedSince(DashboardCommon):
	"""Sin blocked_since la alerta de tarea bloqueada no se puede calcular."""

	def setUp(self):
		super().setUp()
		self.project = self._make_project("Bloqueos")
		self.tag = self.env["project.tags"].create({"name": "Bloqueada QA"})
		self._set_param("blocked_tag_ids", self.tag.id)

	def _task(self, **values):
		return self.env["project.task"].create(
			{"name": "Tarea", "project_id": self.project.id, **values}
		)

	# ------------------------------------------------------------------
	# Las tres vías sellan
	# ------------------------------------------------------------------

	def test_sella_por_campo_propio(self):
		task = self._task()
		self.assertFalse(task.blocked_since)
		task.blocking_state = "blocked"
		self.assertTrue(task.blocked_since)

	def test_sella_por_estado(self):
		task = self._task()
		task.state = WAITING_STATE
		self.assertTrue(task.blocked_since)

	def test_sella_por_etiqueta(self):
		task = self._task()
		task.tag_ids = [(6, 0, [self.tag.id])]
		self.assertTrue(task.blocked_since)

	def test_sella_en_create(self):
		self.assertTrue(self._task(blocking_state="blocked").blocked_since)
		self.assertTrue(self._task(state=WAITING_STATE).blocked_since)
		self.assertTrue(self._task(tag_ids=[(6, 0, [self.tag.id])]).blocked_since)

	def test_no_sella_una_tarea_normal(self):
		self.assertFalse(self._task().blocked_since)

	# ------------------------------------------------------------------
	# Desbloquear limpia
	# ------------------------------------------------------------------

	def test_limpia_al_desbloquear_el_campo(self):
		task = self._task(blocking_state="blocked")
		task.blocking_state = False
		self.assertFalse(task.blocked_since)

	def test_limpia_al_salir_del_estado(self):
		task = self._task(state=WAITING_STATE)
		task.state = "01_in_progress"
		self.assertFalse(task.blocked_since)

	def test_limpia_al_quitar_la_etiqueta(self):
		task = self._task(tag_ids=[(6, 0, [self.tag.id])])
		task.tag_ids = [(5, 0, 0)]
		self.assertFalse(task.blocked_since)

	def test_no_se_repisa_mientras_siga_bloqueada(self):
		"""La fecha es la del primer bloqueo, no la del último cambio."""
		task = self._task(blocking_state="blocked")
		original = task.blocked_since
		task.name = "Otro nombre"
		task.tag_ids = [(6, 0, [self.tag.id])]
		self.assertEqual(task.blocked_since, original)

	def test_sigue_bloqueada_si_queda_otra_via(self):
		task = self._task(blocking_state="blocked")
		task.state = WAITING_STATE
		task.blocking_state = False
		self.assertTrue(task.blocked_since, "el estado sigue bloqueándola")

	# ------------------------------------------------------------------
	# Dominios
	# ------------------------------------------------------------------

	def test_dominio_de_bloqueadas_cubre_las_tres_vias(self):
		manual = self._task(blocking_state="blocked")
		por_estado = self._task(state=WAITING_STATE)
		por_etiqueta = self._task(tag_ids=[(6, 0, [self.tag.id])])
		normal = self._task()
		domain = [("project_id", "=", self.project.id)]
		domain += self.env["project.project"]._primate_blocked_task_domain()
		encontradas = self.env["project.task"].search(domain)
		self.assertIn(manual, encontradas)
		self.assertIn(por_estado, encontradas)
		self.assertIn(por_etiqueta, encontradas)
		self.assertNotIn(normal, encontradas)
