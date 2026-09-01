# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

"""Área de trabajo con responsable."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PrimateArea(models.Model):
	_name = "primate.area"
	_description = "Área de trabajo"
	_order = "sequence, name"

	name = fields.Char(string="Name", required=True, translate=True)
	# El CODE es la clave estable, no el id. El id cambia entre bases; el code no, y es lo que
	# viaja en el payload del dashboard, en los tests y en los tours. Nunca enganchar por id.
	code = fields.Char(
		string="Code",
		required=True,
		index=True,
		copy=False,
		help="Stable identifier used by the dashboard payload, the tours and the tests. "
		"Unlike the database id, it is the same across databases.",
	)
	user_id = fields.Many2one(
		"res.users",
		string="Area Lead",
		ondelete="restrict",
		index=True,
		help="Person in charge of the area. Sagui's project manager role sends this area's "
		"proposals to them.",
	)
	sequence = fields.Integer(string="Sequence", default=10)
	active = fields.Boolean(string="Active", default=True)
	color = fields.Integer(string="Color")

	# En Odoo 19 `_sql_constraints` se IGNORA (sólo deja un warning y la constraint nunca llega a
	# Postgres). Se declara como atributo models.Constraint.
	_code_uniq = models.Constraint("UNIQUE (code)", "There is already an area with that code.")

	@api.constrains("code")
	def _check_code(self):
		"""El code se usa como clave en dominios y payloads: sin espacios ni vacío."""
		for area in self:
			code = (area.code or "").strip()
			if not code or code != area.code or " " in code:
				raise ValidationError(
					_("The code of the area «%s» cannot be empty nor contain spaces.", area.name)
				)

	@api.model
	def _by_code(self, code):
		"""El área con ese code, o un recordset vacío. No crea nada: un code que no existe es
		un dato a revisar, no un área a inventar."""
		if not code:
			return self.browse()
		return self.search([("code", "=", code)], limit=1)
