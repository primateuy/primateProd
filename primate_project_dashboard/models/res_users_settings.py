# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ResUsersSettings(models.Model):
	_inherit = "res.users.settings"

	# Va acá y no en res.users: web ya manda estos campos en la sesión (user_settings),
	# así que el dashboard abre en la vista elegida sin RPC extra ni parpadeo, y cada
	# usuario puede escribir la suya sin abrir SELF_WRITEABLE_FIELDS.
	primate_dashboard_view = fields.Selection(
		[("classic", "Classic"), ("modern", "Modern")],
		string="Project Dashboard View",
		default="classic",
		required=True,
	)
