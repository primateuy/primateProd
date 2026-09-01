# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models


class HrEmployee(models.Model):
	_inherit = "hr.employee"

	area_id = fields.Many2one(
		"primate.area",
		string="Area",
		ondelete="restrict",
		index=True,
		# El área de una PERSONA concreta es dato de RRHH. Lo que se publica sin este grupo son
		# sumas por área (la capacidad del dashboard), nunca el área de alguien en particular.
		groups="hr.group_hr_user",
		help="Area this employee belongs to. The executive dashboard uses it as the denominator "
		"of each area's occupied capacity.",
	)
