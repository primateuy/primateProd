# Copyright 2025 - Abastecimientos
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class HelpdeskTicket(models.Model):
	"""
	Modelo extendido de `helpdesk.ticket` para vincular un ticket con una
	tarea de proyecto específica, permitiendo trazabilidad bidireccional.
	Se utiliza para identificar qué tarea está impactada por el ticket.
	"""

	_inherit = "helpdesk.ticket"

	task_id = fields.Many2one(
		comodel_name="project.task",
		string="Tarea asociada",
		index=True,
		help=(
			"Tarea de proyecto afectada por este ticket. "
			"Permite navegar entre ticket y tarea."
		),
	)

	project_id = fields.Many2one(
		comodel_name="project.project",
		string="Proyecto",
		related="task_id.project_id",
		store=True,
		readonly=True,
		help="Proyecto de la tarea asociada.",
	)

	@api.onchange("task_id")
	def _onchange_task_id(self):
		"""
		Sincroniza el `partner_id` del ticket con el de la tarea si está vacío
		para mejorar contexto; no fuerza cambios si ya existe un partner.
		"""
		for ticket in self:
			if ticket.task_id and not ticket.partner_id:
				ticket.partner_id = ticket.task_id.partner_id

