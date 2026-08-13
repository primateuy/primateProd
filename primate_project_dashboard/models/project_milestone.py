# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectMilestone(models.Model):
	_inherit = "project.milestone"

	planned_progress = fields.Float(
		string="Planned Progress (%)",
		help="Cumulative project progress expected when this milestone is reached.",
		tracking=True,
	)

	@api.constrains("planned_progress")
	def _check_planned_progress_range(self):
		for milestone in self:
			if not 0.0 <= milestone.planned_progress <= 100.0:
				raise ValidationError(_("The planned progress must be between 0 and 100."))

	@api.constrains("planned_progress", "deadline", "project_id")
	def _check_planned_progress_monotonic(self):
		"""El avance planificado debe crecer con la fecha dentro de cada proyecto."""
		projects = self.project_id
		if not projects:
			return
		milestones = self.search(
			[
				("project_id", "in", projects.ids),
				("deadline", "!=", False),
				("planned_progress", ">", 0.0),
			],
			order="project_id, deadline",
		)
		by_project = {}
		for milestone in milestones:
			by_project.setdefault(milestone.project_id, []).append(milestone)
		for project, project_milestones in by_project.items():
			previous = None
			for milestone in project_milestones:
				if previous is not None and milestone.planned_progress < previous.planned_progress:
					raise ValidationError(
						_(
							"In project %(project)s, milestone \"%(milestone)s\" (%(deadline)s) has a planned "
							"progress lower than the earlier milestone \"%(previous)s\". The planned progress "
							"must grow along with the deadlines.",
							project=project.display_name,
							milestone=milestone.name,
							deadline=milestone.deadline,
							previous=previous.name,
						)
					)
				previous = milestone
