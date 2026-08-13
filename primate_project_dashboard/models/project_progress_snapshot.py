# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

import logging

from odoo import api, fields, models

from .project_project import HEALTH_SELECTION

_logger = logging.getLogger(__name__)


class ProjectProgressSnapshot(models.Model):
	_name = "project.progress.snapshot"
	_description = "Project Progress Snapshot"
	_order = "date desc, project_id"
	_rec_name = "project_id"

	project_id = fields.Many2one(
		comodel_name="project.project",
		string="Project",
		required=True,
		index=True,
		ondelete="cascade",
	)
	date = fields.Date(string="Date", required=True, index=True, default=fields.Date.context_today)
	progress_real = fields.Float(string="Real Progress (%)")
	progress_planned = fields.Float(string="Planned Progress (%)")
	consumed_hours = fields.Float(string="Consumed Hours")
	health_state = fields.Selection(selection=HEALTH_SELECTION, string="Health")
	company_id = fields.Many2one(
		comodel_name="res.company",
		string="Company",
		related="project_id.company_id",
		store=True,
		index=True,
	)

	_project_date_uniq = models.Constraint(
		"UNIQUE(project_id, date)",
		"There can only be one progress snapshot per project and date.",
	)

	@api.model
	def _cron_take_snapshot(self):
		"""Foto diaria del avance. En v1 solo se acumula; la curva llega en v2."""
		Project = self.env["project.project"]
		projects = Project.search([("active", "=", True), ("is_template", "=", False)])
		if not projects:
			return True
		today = fields.Date.context_today(self)
		metrics = projects._primate_health_metrics(today=today)
		existing = set(
			self.search([("date", "=", today), ("project_id", "in", projects.ids)]).mapped(
				"project_id.id"
			)
		)
		vals_list = []
		for project in projects:
			if project.id in existing:
				continue
			values = metrics.get(project.id, {})
			vals_list.append(
				{
					"project_id": project.id,
					"date": today,
					"progress_real": values.get("progress_real", 0.0),
					"progress_planned": values.get("progress_planned", 0.0),
					"consumed_hours": values.get("consumed_hours", 0.0),
					"health_state": values.get("health_state", "on_track"),
				}
			)
		if vals_list:
			self.create(vals_list)
		_logger.info("Dashboard: %s snapshots de avance creados.", len(vals_list))
		return True
