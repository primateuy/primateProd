# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

"""Carga de trabajo por área (sección 1.8).

El área es `primate.area` y vive en el módulo `primate_project_area`: la comparten este
dashboard y el rol Gestor de Proyectos de Sagui, así que no la define ninguno de los dos.

Internamente todo se indexa por ID de área (es lo que devuelve `_read_group` al agrupar por un
Many2one), pero HACIA AFUERA la clave sigue siendo el CODE: el payload, el filtro `options`, la
acción de la tarjeta y el tour hablan de 'technical', no de un id que cambia entre bases.
"""

from collections import defaultdict
from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .project_project import CANCELED_STATE, DONE_STATE

CLOSED_TASK_STATES = [DONE_STATE, CANCELED_STATE]


class ProjectProject(models.Model):
	_inherit = "project.project"

	@api.model
	def _primate_capacity_window(self, params, today):
		"""(desde, hasta) de la ventana de capacidad, contada en días hábiles."""
		remaining = max(params["capacity_window_days"], 1)
		end = today
		while remaining > 0:
			end += timedelta(days=1)
			if end.weekday() < 5:
				remaining -= 1
		return today, end

	def _primate_area_task_domain(self, area):
		return [
			("project_id", "in", self.ids),
			("area_id", "=", area.id),
			("state", "not in", CLOSED_TASK_STATES),
		]

	def _primate_area_counts(self, areas, today):
		"""Conteos por área resueltos con una agregación por métrica, no una por área."""
		Task = self.env["project.task"]
		base = [
			("project_id", "in", self.ids),
			("area_id", "in", areas.ids),
			("state", "not in", CLOSED_TASK_STATES),
		]
		counts = {area.id: {"open": 0, "blocked": 0, "waiting": 0, "overdue": 0} for area in areas}
		metrics = {
			"open": base,
			"blocked": base + self._primate_blocked_task_domain(),
			"waiting": base + self._primate_waiting_customer_task_domain(),
			# date_deadline es Datetime en v19: se compara contra el inicio del día de hoy.
			"overdue": base
			+ [("date_deadline", "<", datetime.combine(today, time.min))],
		}
		for name, domain in metrics.items():
			# Agrupar por un Many2one devuelve el RECORDSET del área, no su id.
			for area, count in Task._read_group(domain, ["area_id"], ["__count"]):
				if area.id in counts:
					counts[area.id][name] = count
		return counts

	def _primate_area_capacity(self, areas, params, today):
		"""{id de área: (horas comprometidas, horas disponibles)} en la ventana de capacidad."""
		date_from, date_to = self._primate_capacity_window(params, today)
		committed = self._primate_area_committed_hours(areas, date_from, date_to, params)
		available = self._primate_area_available_hours(areas, date_from, date_to)
		return {area.id: (committed.get(area.id, 0.0), available.get(area.id, 0.0)) for area in areas}

	def _primate_area_committed_hours(self, areas, date_from, date_to, params):
		"""Horas ya comprometidas: Planning si está y se pidió, si no las tareas del período."""
		if params["use_planning_capacity"] and "planning.slot" in self.env:
			return self._primate_planning_committed_hours(areas, date_from, date_to)
		committed = dict.fromkeys(areas.ids, 0.0)
		domain = [
			("project_id", "in", self.ids),
			("area_id", "in", areas.ids),
			("state", "not in", CLOSED_TASK_STATES),
			("date_deadline", ">=", datetime.combine(date_from, time.min)),
			("date_deadline", "<=", datetime.combine(date_to, time.max)),
		]
		for area, remaining in self.env["project.task"]._read_group(
			domain, ["area_id"], ["remaining_hours:sum"]
		):
			if area.id in committed:
				# Las tareas pasadas de horas no descuentan capacidad ajena.
				committed[area.id] = max(remaining or 0.0, 0.0)
		return committed

	def _primate_planning_committed_hours(self, areas, date_from, date_to):
		"""Soporte opcional de Planning, detectado en runtime y nunca en el manifest."""
		committed = dict.fromkeys(areas.ids, 0.0)
		# Mismo criterio que el denominador: el resultado es una suma por área.
		Slot = self.env["planning.slot"].sudo()
		employees_by_area = self._primate_employees_by_area(areas)
		for area_id, employees in employees_by_area.items():
			if not employees:
				continue
			domain = [
				("employee_id", "in", employees.ids),
				("start_datetime", "<=", datetime.combine(date_to, time.max)),
				("end_datetime", ">=", datetime.combine(date_from, time.min)),
			]
			groups = Slot._read_group(domain, [], ["allocated_hours:sum"])
			committed[area_id] = groups[0][0] if groups else 0.0
		return committed

	def _primate_employees_by_area(self, areas):
		"""{id de área: empleados} para el denominador de capacidad.

		SUDO DE AGREGACIÓN — única excepción a la regla de sin-sudo del módulo. El campo
		`hr.employee.area_id` sigue protegido con `groups="hr.group_hr_user"` a nivel de
		registro: el área de una persona concreta es dato de RRHH. Pero lo que sale de
		acá alimenta una suma por área (X horas comprometidas sobre Y de calendario) que
		no expone el área de ningún empleado individual, y los líderes de área son la
		audiencia principal de esas tarjetas: sin esto verían "—" siempre.

		Quien llame a este método SOLO puede agregar. Nada por empleado va al payload.
		"""
		Employee = self.env["hr.employee"].sudo()
		result = {area.id: Employee for area in areas}
		for area, employees in Employee._read_group(
			[("area_id", "in", areas.ids)], ["area_id"], ["id:recordset"]
		):
			if area.id in result:
				result[area.id] = employees
		return result

	def _primate_area_available_hours(self, areas, date_from, date_to):
		"""Horas laborables del equipo de cada área según su calendario de recursos."""
		available = dict.fromkeys(areas.ids, 0.0)
		start = datetime.combine(date_from, time.min)
		end = datetime.combine(date_to, time.max)
		for area_id, employees in self._primate_employees_by_area(areas).items():
			total = 0.0
			# Se agrupa por calendario para no pedir las horas una vez por empleado.
			by_calendar = defaultdict(int)
			for employee in employees:
				calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
				if calendar:
					by_calendar[calendar] += 1
			for calendar, headcount in by_calendar.items():
				total += calendar.get_work_hours_count(start, end) * headcount
			available[area_id] = total
		return available

	@api.model
	def _primate_dashboard_area_records(self):
		"""Las áreas que se muestran, en el orden que define el módulo del área."""
		return self.env["primate.area"].search([])

	def _primate_dashboard_areas(self, params, today):
		"""Tarjetas de carga por área.

		Se omite deliberadamente el "facturas pendientes de emitir" del mockup: exige el
		módulo de contabilidad y este módulo tiene que instalar con solo project,
		sale_timesheet y hr_timesheet. La tarjeta Administrativa muestra las mismas
		métricas que las otras dos.
		"""
		areas = self._primate_dashboard_area_records()
		counts = self._primate_area_counts(areas, today)
		capacity = self._primate_area_capacity(areas, params, today)
		result = []
		for area in areas:
			committed, availability = capacity[area.id]
			result.append(
				{
					# La clave del payload es el CODE, no el id: el front, el tour y los tests
					# enganchan por un valor que sobrevive a un dump restaurado en otra base.
					"area": area.code,
					"area_id": area.id,
					"name": area.display_name,
					"open_tasks": counts[area.id]["open"],
					"blocked_tasks": counts[area.id]["blocked"],
					"waiting_tasks": counts[area.id]["waiting"],
					"overdue_tasks": counts[area.id]["overdue"],
					"committed_hours": round(committed, 1),
					"available_hours": round(availability, 1),
					# None = no hay equipo con esa área cargada, distinto de 0% ocupado.
					"capacity_ratio": round(committed / availability * 100.0, 1) if availability else None,
				}
			)
		return result

	@api.model
	def action_open_area_tasks(self, area, metric, options=None):
		"""Abre la lista de tareas detrás de cada número de la tarjeta.

		`area` es el CODE que viajó en el payload, no un id.

		Se rearma el dominio de proyectos con los mismos filtros del dashboard para que
		la lista muestre exactamente lo que el usuario contó en la tarjeta.
		"""
		area_rec = self.env["primate.area"]._by_code(area)
		if not area_rec:
			raise UserError(_("The area «%s» no longer exists.", area))
		today = fields.Date.context_today(self)
		projects = self.search(self._primate_dashboard_domain(options or {}, today))
		domain = projects._primate_area_task_domain(area_rec)
		if metric == "blocked":
			domain += self._primate_blocked_task_domain()
		elif metric == "waiting":
			domain += self._primate_waiting_customer_task_domain()
		elif metric == "overdue":
			domain += [("date_deadline", "<", datetime.combine(today, time.min))]
		return {
			"type": "ir.actions.act_window",
			"name": _("%(area)s tasks", area=area_rec.display_name),
			"res_model": "project.task",
			# `views` explícito: el diccionario va directo a doAction, que no expande
			# `view_mode` por su cuenta como sí lo hace una ir.actions.act_window leída.
			"views": [(False, "list"), (False, "kanban"), (False, "form")],
			"view_mode": "list,kanban,form",
			"domain": domain,
			"target": "current",
		}
