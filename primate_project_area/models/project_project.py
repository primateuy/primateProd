# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ProjectProject(models.Model):
	_inherit = "project.project"

	area_id = fields.Many2one(
		"primate.area",
		string="Area",
		# restrict: un área con proyectos colgando no se borra por accidente. Para sacarla de
		# circulación está `active`, que no toca los datos históricos.
		ondelete="restrict",
		index=True,
		tracking=True,
		help="Area in charge of the project. New tasks inherit it.",
	)
