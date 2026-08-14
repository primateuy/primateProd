# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from datetime import timedelta

from odoo import api, fields, models

DEFAULT_SNOOZE_DAYS = 7


class ProjectDashboardAlertSnooze(models.Model):
	_name = "project.dashboard.alert.snooze"
	_description = "Dashboard Alert Snooze"
	_order = "snooze_until desc"

	# Las alertas se calculan al vuelo, no son registros: se las identifica por una clave
	# reproducible (tipo + modelo + id) y nunca por su texto. Si el mensaje pasa de
	# "vencido hace 5 días" a "vencido hace 6", el snooze tiene que seguir aplicando.
	user_id = fields.Many2one(
		comodel_name="res.users",
		string="User",
		required=True,
		index=True,
		ondelete="cascade",
		default=lambda self: self.env.user,
	)
	alert_type = fields.Char(string="Alert Type", required=True, index=True)
	res_model = fields.Char(string="Model", required=True)
	res_id = fields.Integer(string="Record ID", required=True)
	snooze_until = fields.Datetime(string="Snoozed Until", required=True, index=True)

	_alert_key_uniq = models.Constraint(
		"UNIQUE(user_id, alert_type, res_model, res_id)",
		"An alert can only be snoozed once per user.",
	)

	@api.model
	def _primate_alert_key(self, alert_type, res_model, res_id):
		return f"{alert_type}:{res_model}:{res_id}"

	@api.model
	def _primate_active_keys(self):
		"""Claves silenciadas y todavía vigentes para el usuario actual."""
		snoozes = self.search(
			[("user_id", "=", self.env.uid), ("snooze_until", ">", fields.Datetime.now())]
		)
		return {
			self._primate_alert_key(snooze.alert_type, snooze.res_model, snooze.res_id)
			for snooze in snoozes
		}

	@api.model
	def action_snooze_alert(self, alert_type, res_model, res_id, days=DEFAULT_SNOOZE_DAYS):
		"""Silencia una alerta para el usuario actual durante N días."""
		until = fields.Datetime.now() + timedelta(days=days or DEFAULT_SNOOZE_DAYS)
		existing = self.search(
			[
				("user_id", "=", self.env.uid),
				("alert_type", "=", alert_type),
				("res_model", "=", res_model),
				("res_id", "=", int(res_id)),
			],
			limit=1,
		)
		if existing:
			existing.snooze_until = until
		else:
			self.create(
				{
					"user_id": self.env.uid,
					"alert_type": alert_type,
					"res_model": res_model,
					"res_id": int(res_id),
					"snooze_until": until,
				}
			)
		return True

	@api.model
	def _gc_expired_snoozes(self):
		"""Los snoozes vencidos no sirven para nada: se limpian con el cron diario."""
		expired = self.search([("snooze_until", "<", fields.Datetime.now())])
		count = len(expired)
		expired.unlink()
		return count
