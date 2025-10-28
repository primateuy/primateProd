# Copyright 2025 - Abastecimientos
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ProjectProject(models.Model):
	"""
	Extiende `project.project` agregando una bandera para habilitar la
	asociación de tickets con tareas dentro de este proyecto.
	"""

	_inherit = "project.project"

	enable_ticket_task_link = fields.Boolean(
		string="Permitir asociación de tickets",
		help=(
			"Si se activa, las tareas de este proyecto podrán vincularse con "
			"tickets de Helpdesk y se mostrará la pestaña de Tickets en las tareas."
		),
		default=True,
	)

