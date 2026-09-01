# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ProjectMilestone(models.Model):
	"""El hito gana un avance planificado, y NADA MÁS.

	Acá no va ninguna validación. El dashboard es un observador del trabajo ajeno: no
	puede bloquear el guardado de un hito ni exigir un orden porque a él le conviene para
	dibujar una curva. Antes había dos constrains -rango 0-100 y avance creciente con la
	fecha- que impedían guardar; se sacaron. Un plan inconsistente lo detecta y lo degrada
	el propio dashboard, en `_primate_progress_planned_map`.
	"""

	_inherit = "project.milestone"

	planned_progress = fields.Float(
		string="Planned Progress (%)",
		help="Cumulative project progress expected when this milestone is reached.",
		tracking=True,
	)
