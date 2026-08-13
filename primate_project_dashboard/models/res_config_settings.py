# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models

from .dashboard_params import PARAM_PREFIX

# Parámetros que se guardan como lista de ids y no soportan `config_parameter`.
TAG_PARAMS = ("blocked_tag_ids", "waiting_customer_tag_ids")


class ResConfigSettings(models.TransientModel):
	_inherit = "res.config.settings"

	# Umbrales del semáforo — rojo
	health_red_progress_gap = fields.Float(
		string="Critical progress gap (pp)",
		default=15.0,
		config_parameter=PARAM_PREFIX + "health_red_progress_gap",
	)
	health_red_hours_ratio = fields.Float(
		string="Critical hours consumption (%)",
		default=90.0,
		config_parameter=PARAM_PREFIX + "health_red_hours_ratio",
	)
	health_red_progress_max = fields.Float(
		string="Critical progress below (%)",
		default=70.0,
		config_parameter=PARAM_PREFIX + "health_red_progress_max",
	)
	health_milestone_overdue_days = fields.Integer(
		string="Critical overdue milestone (days)",
		default=3,
		config_parameter=PARAM_PREFIX + "health_milestone_overdue_days",
	)
	# Umbrales del semáforo — amarillo
	health_yellow_progress_gap = fields.Float(
		string="Attention progress gap (pp)",
		default=5.0,
		config_parameter=PARAM_PREFIX + "health_yellow_progress_gap",
	)
	health_yellow_hours_ratio = fields.Float(
		string="Attention hours consumption (%)",
		default=80.0,
		config_parameter=PARAM_PREFIX + "health_yellow_hours_ratio",
	)
	health_yellow_progress_max = fields.Float(
		string="Attention progress below (%)",
		default=80.0,
		config_parameter=PARAM_PREFIX + "health_yellow_progress_max",
	)
	health_milestone_soon_days = fields.Integer(
		string="Milestone due soon (days)",
		default=7,
		config_parameter=PARAM_PREFIX + "health_milestone_soon_days",
	)
	health_milestone_open_ratio = fields.Float(
		string="Open tasks of the upcoming milestone (%)",
		default=30.0,
		config_parameter=PARAM_PREFIX + "health_milestone_open_ratio",
	)
	# Alertas
	alert_no_activity_days = fields.Integer(
		string="No activity after (days)",
		default=7,
		config_parameter=PARAM_PREFIX + "alert_no_activity_days",
	)
	alert_blocked_days = fields.Integer(
		string="Blocked task after (days)",
		default=5,
		config_parameter=PARAM_PREFIX + "alert_blocked_days",
	)
	# Carga por área
	capacity_window_days = fields.Integer(
		string="Capacity window (working days)",
		default=10,
		config_parameter=PARAM_PREFIX + "capacity_window_days",
	)
	use_planning_capacity = fields.Boolean(
		string="Use Planning for capacity",
		config_parameter=PARAM_PREFIX + "use_planning_capacity",
	)
	is_planning_installed = fields.Boolean(compute="_compute_is_planning_installed")
	# Avance
	progress_method = fields.Selection(
		selection=[
			("closed", "Closed tasks, weighted by allocated hours"),
			("hours", "Consumed hours, capped at 100% per task"),
		],
		string="Real progress method",
		default="closed",
		config_parameter=PARAM_PREFIX + "progress_method",
	)
	# Dashboard
	auto_refresh_enabled = fields.Boolean(
		string="Auto-refresh the dashboard",
		config_parameter=PARAM_PREFIX + "auto_refresh_enabled",
	)
	auto_refresh_interval = fields.Integer(
		string="Auto-refresh every (minutes)",
		default=5,
		config_parameter=PARAM_PREFIX + "auto_refresh_interval",
	)
	# Etiquetas
	blocked_tag_ids = fields.Many2many(
		comodel_name="project.tags",
		relation="primate_dashboard_blocked_tag_rel",
		column1="config_id",
		column2="tag_id",
		string="Blocking tags",
	)
	waiting_customer_tag_ids = fields.Many2many(
		comodel_name="project.tags",
		relation="primate_dashboard_waiting_tag_rel",
		column1="config_id",
		column2="tag_id",
		string="Waiting for customer tags",
	)

	def _compute_is_planning_installed(self):
		"""El soporte de Planning se detecta en runtime, nunca por `depends` del manifest."""
		installed = "planning.slot" in self.env
		for record in self:
			record.is_planning_installed = installed

	@api.model
	def get_values(self):
		res = super().get_values()
		params = self.env["ir.config_parameter"].sudo()
		for name in TAG_PARAMS:
			raw = params.get_param(PARAM_PREFIX + name) or ""
			tag_ids = [int(chunk) for chunk in raw.split(",") if chunk.strip().isdigit()]
			res[name] = [(6, 0, self.env["project.tags"].browse(tag_ids).exists().ids)]
		return res

	def set_values(self):
		res = super().set_values()
		params = self.env["ir.config_parameter"].sudo()
		for name in TAG_PARAMS:
			value = ",".join(str(tag_id) for tag_id in self[name].ids)
			params.set_param(PARAM_PREFIX + name, value)
		return res
