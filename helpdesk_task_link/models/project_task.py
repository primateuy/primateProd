# Copyright 2025 - Abastecimientos
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ProjectTask(models.Model):
	"""
	Extensión de `project.task` para listar todos los tickets vinculados a
	la tarea, facilitando el seguimiento de impactos y resolución.
	"""

	_inherit = "project.task"

	ticket_ids = fields.One2many(
		comodel_name="helpdesk.ticket",
		inverse_name="task_id",
		string="Tickets relacionados",
		help="Tickets de Helpdesk que impactan en esta tarea.",
	)

	enable_ticket_task_link = fields.Boolean(
		string="Permitir asociación de tickets",
		related="project_id.enable_ticket_task_link",
		store=True,
		readonly=True,
		help=(
			"Indica si el proyecto permite la asociación de tickets. "
			"Se usa para controlar la visibilidad de tickets en la tarea."
		),
	)

