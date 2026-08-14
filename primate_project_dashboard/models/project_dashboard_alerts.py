# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

"""Catálogo de alertas (sección 1.9)."""

from datetime import datetime, time, timedelta

from odoo import _, api, fields, models

from .project_project import CANCELED_STATE, DONE_STATE

CLOSED_TASK_STATES = [DONE_STATE, CANCELED_STATE]

SEVERITY_DANGER = "danger"
SEVERITY_WARNING = "warning"

# Tope de alertas devueltas por el RPC.
ALERT_LIMIT = 50


class ProjectProject(models.Model):
	_inherit = "project.project"

	# ------------------------------------------------------------------
	# Helpers
	# ------------------------------------------------------------------

	@api.model
	def _primate_alert(
		self, alert_type, severity, message, res_model, res_id,
		project_id=None, age_days=0, res_ids=None,
	):
		"""Una alerta. La clave es reproducible: sobrevive a que cambie el mensaje.

		`res_ids` es para las alertas agregadas: el botón abre la lista completa de los
		registros involucrados en vez de uno solo.
		"""
		return {
			"key": self.env["project.dashboard.alert.snooze"]._primate_alert_key(
				alert_type, res_model, res_id
			),
			"type": alert_type,
			"severity": severity,
			"message": message,
			"res_model": res_model,
			"res_id": res_id,
			"res_ids": res_ids or [],
			"project_id": project_id,
			# Ordena dentro de cada severidad: primero lo que lleva más tiempo pudriéndose.
			"age_days": age_days,
		}

	# ------------------------------------------------------------------
	# Alertas del catálogo
	# ------------------------------------------------------------------

	def _primate_alerts_milestone_overdue(self, milestone_map, today):
		"""Hito vencido y no alcanzado. Severidad roja."""
		alerts = []
		names = {project.id: project.display_name for project in self}
		for project_id, milestones in milestone_map.items():
			for milestone in milestones:
				if milestone["is_reached"] or not milestone["deadline"]:
					continue
				overdue_days = (today - milestone["deadline"]).days
				if overdue_days <= 0:
					continue
				alerts.append(
					self._primate_alert(
						"milestone_overdue",
						SEVERITY_DANGER,
						_(
							'%(project)s: milestone "%(milestone)s" is %(days)s days overdue',
							project=names.get(project_id, ""),
							milestone=milestone["name"],
							days=overdue_days,
						),
						"project.milestone",
						milestone["id"],
						project_id,
						age_days=overdue_days,
					)
				)
		return alerts

	def _primate_alerts_hours_budget(self, metrics, params):
		"""Presupuesto de horas por agotarse. Amarilla o roja según la brecha."""
		alerts = []
		for project in self:
			values = metrics.get(project.id, {})
			sold = values.get("sold_hours")
			consumed = values.get("consumed_hours")
			if not sold or consumed is None:
				continue
			consumed_ratio = consumed / sold * 100.0
			progress = values.get("progress_real", 0.0)
			if consumed_ratio < params["alert_hours_ratio"] or progress >= params["alert_hours_progress_max"]:
				continue
			gap = consumed_ratio - progress
			severity = (
				SEVERITY_DANGER
				if consumed_ratio >= params["alert_hours_red_ratio"]
				or gap >= params["alert_hours_red_gap"]
				else SEVERITY_WARNING
			)
			alerts.append(
				self._primate_alert(
					"hours_budget",
					severity,
					_(
						"%(project)s: %(consumed)s%% of the sold hours consumed with %(progress)s%% progress",
						project=project.display_name,
						consumed=round(consumed_ratio),
						progress=round(progress),
					),
					"project.project",
					project.id,
					project.id,
				)
			)
		return alerts

	def _primate_alerts_no_activity(self, params, today):
		"""Proyecto sin timesheets ni cambios de etapa en X días."""
		alerts = []
		limit_days = params["alert_no_activity_days"]
		limit_date = today - timedelta(days=limit_days)
		last_timesheet = {}
		if self._primate_can_read_timesheets():
			for project, last_date in self.env["account.analytic.line"]._read_group(
				self._primate_timesheet_domain(), ["project_id"], ["date:max"]
			):
				if project:
					last_timesheet[project.id] = last_date
		# El cambio de etapa es la señal de la spec, pero un proyecto sin etapas
		# configuradas no la tiene nunca: se toma también la última escritura de sus
		# tareas, que es actividad igual y siempre está.
		last_task_change = {}
		for project, last_stage, last_write in self.env["project.task"]._read_group(
			[("project_id", "in", self.ids)],
			["project_id"],
			["date_last_stage_update:max", "write_date:max"],
		):
			if not project:
				continue
			marks = [fields.Date.to_date(value) for value in (last_stage, last_write) if value]
			if marks:
				last_task_change[project.id] = max(marks)
		for project in self:
			dates = [
				value
				for value in (last_timesheet.get(project.id), last_task_change.get(project.id))
				if value
			]
			last_activity = max(dates) if dates else None
			if last_activity and last_activity > limit_date:
				continue
			alerts.append(
				self._primate_alert(
					"no_activity",
					SEVERITY_WARNING,
					_(
						"%(project)s: no timesheet or stage change in the last %(days)s days",
						project=project.display_name,
						days=limit_days,
					),
					"project.project",
					project.id,
					project.id,
					age_days=(today - last_activity).days if last_activity else limit_days,
				)
			)
		return alerts

	def _primate_alerts_missing_timesheets(self, today):
		"""Usuarios asignados a tareas abiertas con cero timesheets esta semana."""
		if not self.ids or not self._primate_can_read_timesheets():
			return []
		assigned = set()
		for [users] in self.env["project.task"]._read_group(
			[("project_id", "in", self.ids), ("state", "not in", CLOSED_TASK_STATES)],
			["user_ids"],
		):
			if users:
				assigned.add(users.id)
		if not assigned:
			return []
		week_start = today - timedelta(days=today.weekday())
		with_timesheets = set()
		for [user] in self.env["account.analytic.line"]._read_group(
			[("user_id", "in", list(assigned)), ("date", ">=", week_start), ("date", "<=", today)],
			["user_id"],
		):
			if user:
				with_timesheets.add(user.id)
		missing = assigned - with_timesheets
		if not missing:
			return []
		# Una sola alerta agregada: una por usuario ahogaría el panel.
		return [
			self._primate_alert(
				"missing_timesheets",
				SEVERITY_WARNING,
				_(
					"%(count)s users assigned to open tasks have not logged any timesheet this week",
					count=len(missing),
				),
				"res.users",
				sorted(missing)[0],
				res_ids=sorted(missing),
			)
		]

	def _primate_alerts_no_plan(self, metrics):
		"""Proyecto sin plan cargado: falta fecha de fin o hitos con avance planificado.

		Cubre tanto los que quedan en gris (sin curva) como los de plan aproximado: el
		semáforo es la señal pasiva, la alerta es la presión para cargar el plan.
		"""
		alerts = []
		for project in self:
			values = metrics.get(project.id, {})
			if values.get("has_plan"):
				continue
			alerts.append(
				self._primate_alert(
					"no_plan",
					SEVERITY_WARNING,
					_(
						"%(project)s: no plan loaded (missing end date or milestones with planned progress)",
						project=project.display_name,
					),
					"project.project",
					project.id,
					project.id,
				)
			)
		return alerts

	def _primate_alerts_blocked_tasks(self, params, today):
		"""Tarea bloqueada hace más de X días, por cualquiera de las tres vías."""
		limit_days = params["alert_blocked_days"]
		limit = datetime.combine(today - timedelta(days=limit_days), time.max)
		domain = [
			("project_id", "in", self.ids),
			("state", "not in", CLOSED_TASK_STATES),
			("blocked_since", "!=", False),
			("blocked_since", "<=", limit),
		]
		alerts = []
		for task in self.env["project.task"].search(domain, limit=50):
			days = (today - fields.Date.to_date(task.blocked_since)).days
			alerts.append(
				self._primate_alert(
					"task_blocked",
					SEVERITY_WARNING,
					_(
						"%(task)s: blocked for %(days)s days",
						task=task.display_name,
						days=days,
					),
					"project.task",
					task.id,
					task.project_id.id,
					age_days=days,
				)
			)
		return alerts

	# ------------------------------------------------------------------
	# Panel
	# ------------------------------------------------------------------

	def _primate_dashboard_alerts(self, metrics, milestone_map, params, today):
		"""Catálogo completo, ya filtrado por los snoozes vigentes del usuario."""
		alerts = []
		alerts += self._primate_alerts_milestone_overdue(milestone_map, today)
		alerts += self._primate_alerts_hours_budget(metrics, params)
		alerts += self._primate_alerts_no_plan(metrics)
		alerts += self._primate_alerts_blocked_tasks(params, today)
		alerts += self._primate_alerts_no_activity(params, today)
		alerts += self._primate_alerts_missing_timesheets(today)
		snoozed = self.env["project.dashboard.alert.snooze"]._primate_active_keys()
		alerts = [alert for alert in alerts if alert["key"] not in snoozed]
		# Primero las rojas y, dentro de cada severidad, lo que lleva más tiempo abierto.
		alerts.sort(
			key=lambda alert: (
				0 if alert["severity"] == SEVERITY_DANGER else 1,
				-alert["age_days"],
			)
		)
		# Cap defensivo: el panel no se pagina en v1, pero tampoco puede devolver mil
		# alertas. El lazy-load real queda anotado como pendiente de v2 en el README.
		total = len(alerts)
		return alerts[:ALERT_LIMIT], total

	@api.model
	def action_open_alert_record(self, res_model, res_id, res_ids=None):
		"""Abre lo que hay detrás de la alerta: un registro, o la lista si son varios."""
		if res_ids and len(res_ids) > 1:
			return {
				"type": "ir.actions.act_window",
				"res_model": res_model,
				"view_mode": "list,form",
				"domain": [("id", "in", [int(value) for value in res_ids])],
				"target": "current",
			}
		return {
			"type": "ir.actions.act_window",
			"res_model": res_model,
			"res_id": int(res_id),
			"views": [(False, "form")],
			"target": "current",
		}
