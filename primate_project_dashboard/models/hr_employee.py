# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models

from .project_task import AREA_SELECTION


class HrEmployee(models.Model):
	_inherit = "hr.employee"

	area = fields.Selection(
		selection=AREA_SELECTION,
		string="Dashboard Area",
		groups="hr.group_hr_user",
		help="Area this employee belongs to. The executive dashboard uses it as the "
		"denominator of the occupied capacity of each area.",
	)
