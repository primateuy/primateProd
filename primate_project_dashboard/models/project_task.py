# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models

from . import dashboard_params

# Estado estándar de Odoo 19 que representa una tarea en espera.
WAITING_STATE = "04_waiting_normal"

# Campos que pueden cambiar el bloqueo. project.task es el modelo más caliente de Odoo:
# si ninguno viene en vals, el override sale sin costo.
BLOCKING_TRIGGER_FIELDS = ("blocking_state", "state", "tag_ids")

AREA_SELECTION = [
	("technical", "Technical"),
	("functional", "Functional"),
	("admin", "Administrative"),
]


class ProjectTask(models.Model):
	_inherit = "project.task"

	area = fields.Selection(
		selection=AREA_SELECTION,
		string="Area",
		index=True,
		tracking=True,
		help="Area in charge of the task. Used by the executive dashboard to group workload.",
	)
	# Caso borde asumido: al ser Selection, una tarea no puede estar "bloqueada" y
	# "esperando al cliente" a la vez. Si la operativa real lo necesita, se revisa en v2.
	blocking_state = fields.Selection(
		selection=[("blocked", "Blocked"), ("waiting_customer", "Waiting for Customer")],
		string="Blocking",
		copy=False,
		tracking=True,
		help="Manual blocking flag. A task is also considered blocked when it is in the "
		"Waiting state or carries one of the tags configured in the dashboard settings.",
	)
	blocked_since = fields.Datetime(
		string="Blocked Since",
		copy=False,
		readonly=True,
		help="Set automatically the first time the task becomes blocked, by any of the three "
		"criteria (manual flag, Waiting state or blocking tag). Cleared when it is unblocked.",
	)

	def _primate_blocking_tag_ids(self):
		"""Etiquetas configuradas como bloqueo / espera de cliente."""
		return (
			dashboard_params.get_ids(self.env, "blocked_tag_ids"),
			dashboard_params.get_ids(self.env, "waiting_customer_tag_ids"),
		)

	def _primate_is_blocked(self, blocked_tag_ids=None, waiting_tag_ids=None):
		"""True si la tarea está bloqueada por cualquiera de las tres vías."""
		self.ensure_one()
		if blocked_tag_ids is None or waiting_tag_ids is None:
			blocked_tag_ids, waiting_tag_ids = self._primate_blocking_tag_ids()
		if self.blocking_state:
			return True
		if self.state == WAITING_STATE:
			return True
		tag_ids = set(self.tag_ids.ids)
		return bool(tag_ids & set(blocked_tag_ids)) or bool(tag_ids & set(waiting_tag_ids))

	def _primate_sync_blocked_since(self, blocked_tag_ids=None, waiting_tag_ids=None):
		"""Sella la fecha de bloqueo; sin esto la alerta 'bloqueada hace X días' no se puede calcular."""
		if blocked_tag_ids is None or waiting_tag_ids is None:
			blocked_tag_ids, waiting_tag_ids = self._primate_blocking_tag_ids()
		now = fields.Datetime.now()
		to_stamp = self.browse()
		to_clear = self.browse()
		for task in self:
			blocked = task._primate_is_blocked(blocked_tag_ids, waiting_tag_ids)
			if blocked and not task.blocked_since:
				to_stamp |= task
			elif not blocked and task.blocked_since:
				to_clear |= task
		# El contexto corta la recursión del write que dispara esta misma sincronización.
		if to_stamp:
			to_stamp.with_context(primate_skip_blocked_sync=True).write({"blocked_since": now})
		if to_clear:
			to_clear.with_context(primate_skip_blocked_sync=True).write({"blocked_since": False})

	@api.model_create_multi
	def create(self, vals_list):
		tasks = super().create(vals_list)
		if self.env.context.get("primate_skip_blocked_sync"):
			return tasks
		# La enorme mayoría de las tareas nace desbloqueada: se filtra con campos ya en
		# caché antes de tocar etiquetas o de escribir nada.
		candidates = tasks.filtered(
			lambda task: task.blocking_state or task.state == WAITING_STATE
		)
		blocked_tag_ids, waiting_tag_ids = self._primate_blocking_tag_ids()
		if blocked_tag_ids or waiting_tag_ids:
			tag_ids = set(blocked_tag_ids) | set(waiting_tag_ids)
			candidates |= tasks.filtered(lambda task: tag_ids & set(task.tag_ids.ids))
		if candidates:
			candidates._primate_sync_blocked_since(blocked_tag_ids, waiting_tag_ids)
		return tasks

	def write(self, vals):
		sync_blocking = not self.env.context.get("primate_skip_blocked_sync") and any(
			field in vals for field in BLOCKING_TRIGGER_FIELDS
		)
		res = super().write(vals)
		if sync_blocking:
			self._primate_sync_blocked_since()
		return res

	@api.onchange("project_id", "area")
	def _onchange_area_warning(self):
		"""Aviso no bloqueante: en proyectos facturables el área debería estar cargada."""
		if self.project_id and self.project_id.sale_line_id and not self.area:
			return {
				"warning": {
					"title": _("Area not set"),
					"message": _(
						"This task belongs to a billable project. Set its area so it is counted "
						"in the workload of the executive dashboard."
					),
				}
			}
