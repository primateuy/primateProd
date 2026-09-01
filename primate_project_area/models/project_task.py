# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class ProjectTask(models.Model):
	_inherit = "project.task"

	area_id = fields.Many2one(
		"primate.area",
		string="Area",
		ondelete="restrict",
		index=True,
		tracking=True,
		help="Area in charge of the task. It is inherited from the project and can be changed "
		"here: an administrative task inside a technical project is a real case.",
	)

	# ------------------------------------------------------------------
	#  Herencia proyecto -> tarea
	#
	#  Deliberadamente NO es un related ni un compute stored editable. Los dos se recalculan al
	#  mover la tarea de proyecto y BORRAN la edición manual sin avisar, que es justo el dato que
	#  hay que respetar. La regla se escribe a mano y es explícita:
	#
	#    - al crear, si no viene área, toma la del proyecto;
	#    - al cambiar de proyecto, re-hereda SÓLO si el área que tenía era la del proyecto
	#      anterior. Si alguien la cambió a mano, se queda como está.
	#
	#  Lo que NO hace: cambiar el área de un proyecto no re-cascadea a sus tareas. Ese caso queda
	#  como hallazgo de la regla «tarea en proyecto de otra área» del rol Gestor de Proyectos, que
	#  lo propone con nombre y apellido en vez de reescribir tareas en silencio.
	# ------------------------------------------------------------------
	@api.model_create_multi
	def create(self, vals_list):
		sin_area = [vals for vals in vals_list if not vals.get("area_id") and vals.get("project_id")]
		if sin_area:
			proyectos = self.env["project.project"].browse(
				{vals["project_id"] for vals in sin_area}
			)
			areas = {project.id: project.area_id.id for project in proyectos.exists()}
			for vals in sin_area:
				area_id = areas.get(vals["project_id"])
				if area_id:
					vals["area_id"] = area_id
		return super().create(vals_list)

	def write(self, vals):
		if "project_id" not in vals or "area_id" in vals:
			return super().write(vals)
		destino = self.env["project.project"].browse(vals["project_id"] or [])
		a_heredar = self.filtered(lambda task: task.area_id == task.project_id.area_id)
		resto = self - a_heredar
		if a_heredar:
			super(ProjectTask, a_heredar).write(dict(vals, area_id=destino.area_id.id))
		if resto:
			super(ProjectTask, resto).write(vals)
		return True

	@api.onchange("project_id")
	def _onchange_project_id_area(self):
		"""Lo mismo que hace write, pero visible en el formulario antes de guardar."""
		for task in self:
			if not task.area_id or task.area_id == task._origin.project_id.area_id:
				task.area_id = task.project_id.area_id
