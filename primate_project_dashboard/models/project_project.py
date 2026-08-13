# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

import logging
from collections import defaultdict

from odoo import _, api, fields, models

from . import dashboard_params
from .project_task import WAITING_STATE

_logger = logging.getLogger(__name__)

DONE_STATE = "1_done"
CANCELED_STATE = "1_canceled"

HEALTH_SELECTION = [
	("on_track", "On Track"),
	("at_risk", "Attention"),
	("critical", "At Risk"),
]


class ProjectProject(models.Model):
	_inherit = "project.project"

	progress_real = fields.Float(
		string="Real Progress (%)",
		compute="_compute_progress_metrics",
		help="Task progress weighted by allocated hours, according to the method configured "
		"in Settings.",
	)
	progress_planned = fields.Float(
		string="Planned Progress (%)",
		compute="_compute_progress_metrics",
		help="Progress expected today, interpolated between milestones.",
	)
	progress_plan_is_estimated = fields.Boolean(
		string="Approximate Plan",
		compute="_compute_progress_metrics",
		help="The planned progress could not be interpolated from milestones and was "
		"estimated from the project start and end dates.",
	)
	has_dashboard_plan = fields.Boolean(
		string="Plan Loaded",
		compute="_compute_progress_metrics",
		help="The project has a start date, an end date and at least two milestones with "
		"deadline and planned progress.",
	)
	health_state = fields.Selection(
		selection=HEALTH_SELECTION,
		string="Health",
		compute="_compute_health_state",
		store=True,
		index=True,
		readonly=True,
		# Explícito aunque `store=True` ya lo ponga en True por default: el valor es global
		# y lo ven todos. Si un PM sin lectura sobre sale.order.line dispara el recompute al
		# cargar un timesheet, sin sudo sold_hours daría 0 y se guardaría un semáforo
		# equivocado para toda la empresa hasta el cron. No contradice la regla de "sin
		# sudo()": esa aplica a get_dashboard_data y a lo que cada usuario lee.
		compute_sudo=True,
		help="Calculated from objective rules; it is never set by hand.",
	)
	sold_hours = fields.Float(
		string="Sold Hours",
		compute="_compute_sale_metrics",
	)
	consumed_hours = fields.Float(
		string="Consumed Hours",
		compute="_compute_consumed_hours",
	)
	margin_estimate = fields.Monetary(
		string="Estimated Margin",
		currency_field="currency_id",
		compute="_compute_margin_estimate",
		groups="primate_project_dashboard.group_dashboard_manager",
	)
	deviation_days = fields.Integer(
		string="Deviation (days)",
		compute="_compute_deviation_days",
		help="Estimated delay in days, based on the progress gap and the recent pace.",
	)

	# ------------------------------------------------------------------
	# Avance real
	# ------------------------------------------------------------------

	def _primate_task_domain(self):
		"""Tareas que cuentan para el avance: las canceladas no suman ni al total."""
		return [("project_id", "in", self.ids), ("state", "!=", CANCELED_STATE)]

	def _primate_progress_real_map(self, method=None):
		"""{project_id: avance real} resuelto con agregaciones, sin recorrer registros."""
		result = dict.fromkeys(self.ids, 0.0)
		if not self.ids:
			return result
		if method is None:
			method = dashboard_params.get_str(self.env, "progress_method")
		domain = self._primate_task_domain()
		done_hours = defaultdict(float)
		total_hours = defaultdict(float)
		done_count = defaultdict(int)
		total_count = defaultdict(int)
		for project, state, hours, count in self.env["project.task"]._read_group(
			domain, ["project_id", "state"], ["allocated_hours:sum", "__count"]
		):
			total_hours[project.id] += hours
			total_count[project.id] += count
			if state == DONE_STATE:
				done_hours[project.id] += hours
				done_count[project.id] += count
		spent_progress = self._primate_progress_by_spent_hours(domain) if method == "hours" else {}
		for project_id in self.ids:
			if project_id in spent_progress:
				result[project_id] = spent_progress[project_id]
			elif total_hours[project_id]:
				result[project_id] = done_hours[project_id] / total_hours[project_id] * 100.0
			elif total_count[project_id]:
				# Sin horas por tarea: fallback a tareas cerradas sobre tareas totales.
				result[project_id] = done_count[project_id] / total_count[project_id] * 100.0
		return result

	def _primate_progress_by_spent_hours(self, domain):
		"""Avance por horas consumidas, capeado al 100% en cada tarea.

		read_group no puede expresar LEAST(effective, allocated) por fila, así que se traen
		las tres columnas en una sola consulta y el tope se aplica en memoria: sin él, una
		tarea pasada de horas infla el avance de todo el proyecto.
		"""
		spent = defaultdict(float)
		allocated = defaultdict(float)
		rows = self.env["project.task"].search_read(
			domain, ["project_id", "allocated_hours", "effective_hours"], load=None
		)
		for row in rows:
			task_allocated = row["allocated_hours"] or 0.0
			if not task_allocated:
				continue
			project_id = row["project_id"]
			allocated[project_id] += task_allocated
			spent[project_id] += min(row["effective_hours"] or 0.0, task_allocated)
		return {
			project_id: spent[project_id] / allocated[project_id] * 100.0
			for project_id in allocated
			if allocated[project_id]
		}

	# ------------------------------------------------------------------
	# Avance planificado
	# ------------------------------------------------------------------

	def _primate_milestone_map(self):
		"""{project_id: [hitos ordenados por fecha]} en una sola consulta."""
		result = defaultdict(list)
		if not self.ids:
			return result
		rows = self.env["project.milestone"].search_read(
			[("project_id", "in", self.ids)],
			["project_id", "name", "deadline", "planned_progress", "is_reached"],
			order="deadline asc, id asc",
			load=None,
		)
		for row in rows:
			row["deadline"] = fields.Date.to_date(row["deadline"])
			result[row["project_id"]].append(row)
		return result

	@api.model
	def _primate_interpolate(self, points, today):
		"""Interpolación lineal entre los puntos (fecha, % acumulado) del plan."""
		if not points:
			return 0.0
		points = sorted(points, key=lambda point: point[0])
		if today <= points[0][0]:
			return points[0][1]
		if today >= points[-1][0]:
			return points[-1][1]
		for (date_from, value_from), (date_to, value_to) in zip(points, points[1:]):
			if date_from <= today <= date_to:
				span = (date_to - date_from).days
				if span <= 0:
					return value_to
				ratio = (today - date_from).days / span
				return value_from + (value_to - value_from) * ratio
		return points[-1][1]

	def _primate_progress_planned_map(self, milestone_map=None, today=None):
		"""{project_id: (avance planificado, plan aproximado, plan cargado)}.

		El plan describe el proyecto completo; los hitos son puntos intermedios de esa
		curva, no su techo. Por eso la curva SIEMPRE termina en 100%, anclada en la fecha
		más tardía entre la fecha de fin del proyecto y el deadline del último hito: si
		los hitos topean en 70%, el tramo final interpola de 70% a 100% hasta esa ancla.

		Caso degenerado conocido: si el último hito es posterior a la fecha de fin, el
		ancla cae sobre ese mismo hito y el tramo final tiene longitud cero, así que el
		plan salta de 70% a 100% en esa fecha en vez de subir gradualmente.
		"""
		result = {}
		if not self.ids:
			return result
		today = today or fields.Date.context_today(self)
		if milestone_map is None:
			milestone_map = self._primate_milestone_map()
		for project in self:
			planned_milestones = [
				milestone
				for milestone in milestone_map.get(project._origin.id, [])
				if milestone["deadline"] and milestone["planned_progress"]
			]
			has_plan = bool(project.date_start and project.date and len(planned_milestones) >= 2)
			if has_plan:
				points = [(project.date_start, 0.0)]
				points += [(m["deadline"], m["planned_progress"]) for m in planned_milestones]
				last_deadline = planned_milestones[-1]["deadline"]
				end_date = max(project.date, last_deadline)
				if points[-1] != (end_date, 100.0):
					points.append((end_date, 100.0))
			elif project.date_start and project.date:
				# Plan aproximado: recta entre inicio y fin del proyecto.
				points = [(project.date_start, 0.0), (project.date, 100.0)]
			else:
				points = []
			result[project.id] = (
				self._primate_interpolate(points, today),
				not has_plan,
				has_plan,
			)
		return result

	@api.depends(
		"task_ids.state",
		"task_ids.allocated_hours",
		"task_ids.effective_hours",
		"milestone_ids.deadline",
		"milestone_ids.planned_progress",
		"date_start",
		"date",
	)
	def _compute_progress_metrics(self):
		real_map = self._primate_progress_real_map()
		planned_map = self._primate_progress_planned_map()
		for project in self:
			planned, estimated, has_plan = planned_map.get(project.id, (0.0, True, False))
			project.progress_real = real_map.get(project._origin.id, 0.0)
			project.progress_planned = planned
			project.progress_plan_is_estimated = estimated
			project.has_dashboard_plan = has_plan

	# ------------------------------------------------------------------
	# Horas y economía
	# ------------------------------------------------------------------

	def _primate_timesheet_domain(self, date_from=None, date_to=None):
		"""Solo líneas analíticas que son timesheets.

		El plan analítico del proyecto puede recibir líneas que no son horas de trabajo
		(facturas de proveedor, asientos manuales); sin este filtro el consumo y el margen
		quedarían contaminados.
		"""
		domain = [("project_id", "in", self.ids), ("employee_id", "!=", False)]
		if date_from:
			domain.append(("date", ">=", date_from))
		if date_to:
			domain.append(("date", "<=", date_to))
		return domain

	def _primate_can_read_timesheets(self):
		"""Un usuario sin acceso a las líneas analíticas no tiene el dato, no tiene un cero."""
		return self.env["account.analytic.line"].has_access("read")

	def _primate_consumed_hours_map(self, date_from=None, date_to=None):
		if not self.ids:
			return {}
		if not self._primate_can_read_timesheets():
			return dict.fromkeys(self.ids, None)
		result = dict.fromkeys(self.ids, 0.0)
		for project, unit_amount in self.env["account.analytic.line"]._read_group(
			self._primate_timesheet_domain(date_from, date_to), ["project_id"], ["unit_amount:sum"]
		):
			result[project.id] = unit_amount
		return result

	def _primate_timesheet_cost_map(self):
		"""Costo de las horas cargadas. `amount` ya trae unit_amount x costo horario, en negativo."""
		if not self.ids:
			return {}
		if not self._primate_can_read_timesheets():
			return dict.fromkeys(self.ids, None)
		result = dict.fromkeys(self.ids, 0.0)
		for project, amount in self.env["account.analytic.line"]._read_group(
			self._primate_timesheet_domain(), ["project_id"], ["amount:sum"]
		):
			result[project.id] = -amount
		return result

	def _primate_sale_line_domain(self):
		return [
			("project_id", "in", self.ids),
			("state", "=", "sale"),
			("product_id.type", "=", "service"),
		]

	def _primate_orphan_sale_lines(self):
		"""{línea de venta: id de proyecto} para las líneas que el agrupado no atrapa.

		Una línea con `project_id` ya tiene dueño y entra por el agrupado, así que no se
		vuelve a contar acá. Las que no lo tienen se imputan al proyecto que las apunta
		con `sale_line_id`; si varios proyectos apuntan a la misma, se asigna al de menor
		id —determinístico— y el resto la ignora, porque sumarla en todos inflaría los
		KPIs del portafolio.
		"""
		candidates = defaultdict(list)
		for project in self:
			project_id = project._origin.id
			line = project.sale_line_id
			if not project_id or not line or line.state != "sale" or line.project_id:
				continue
			candidates[line].append(project_id)
		orphans = {}
		for line, project_ids in candidates.items():
			project_ids.sort()
			if len(project_ids) > 1:
				# Es un problema de datos del cliente: se avisa, no se esconde.
				_logger.warning(
					"Dashboard: la línea de venta %s está referenciada como sale_line_id por "
					"los proyectos %s. Sus horas y su monto se imputan solo al proyecto %s "
					"para no contarlos dos veces.",
					line.id,
					project_ids,
					project_ids[0],
				)
			orphans[line] = project_ids[0]
		return orphans

	def _primate_sold_hours_map(self):
		if not self.ids:
			return {}
		if not self.env["sale.order.line"].has_access("read"):
			return dict.fromkeys(self.ids, None)
		result = dict.fromkeys(self.ids, 0.0)
		uom_hour = self.env.ref("uom.product_uom_hour", raise_if_not_found=False)
		if not uom_hour:
			return result
		for project, uom, qty in self.env["sale.order.line"]._read_group(
			self._primate_sale_line_domain(), ["project_id", "product_uom_id"], ["product_uom_qty:sum"]
		):
			if project and uom and uom._has_common_reference(uom_hour):
				result[project.id] = result.get(project.id, 0.0) + uom._compute_quantity(
					qty, uom_hour, round=False
				)
		for line, project_id in self._primate_orphan_sale_lines().items():
			if line.product_uom_id and line.product_uom_id._has_common_reference(uom_hour):
				qty = line.product_uom_id._compute_quantity(line.product_uom_qty, uom_hour, round=False)
				result[project_id] = result.get(project_id, 0.0) + qty
		return result

	def _primate_sold_amount_map(self):
		"""Monto vendido sin impuestos imputable a cada proyecto."""
		if not self.ids:
			return {}
		if not self.env["sale.order.line"].has_access("read"):
			return dict.fromkeys(self.ids, None)
		result = dict.fromkeys(self.ids, 0.0)
		for project, subtotal in self.env["sale.order.line"]._read_group(
			self._primate_sale_line_domain(), ["project_id"], ["price_subtotal:sum"]
		):
			if project:
				result[project.id] = subtotal
		for line, project_id in self._primate_orphan_sale_lines().items():
			result[project_id] = result.get(project_id, 0.0) + line.price_subtotal
		return result

	@api.depends("sale_line_id")
	def _compute_sale_metrics(self):
		sold_map = self._primate_sold_hours_map()
		for project in self:
			project.sold_hours = sold_map.get(project._origin.id) or 0.0

	@api.depends("timesheet_ids.unit_amount")
	def _compute_consumed_hours(self):
		# Un Float no puede ser nulo: el campo queda en 0 y es el RPC el que distingue
		# "sin permiso" de "cero real" mandando None.
		consumed_map = self._primate_consumed_hours_map()
		for project in self:
			project.consumed_hours = consumed_map.get(project._origin.id) or 0.0

	@api.depends("sale_line_id", "timesheet_ids.amount")
	def _compute_margin_estimate(self):
		revenue_map = self._primate_sold_amount_map()
		cost_map = self._primate_timesheet_cost_map()
		for project in self:
			project.margin_estimate = (revenue_map.get(project._origin.id) or 0.0) - (
				cost_map.get(project._origin.id) or 0.0
			)

	@api.model
	def _primate_deviation_days(self, project, values, params, today):
		"""Atraso estimado en días. Devuelve None cuando el número no sería creíble.

		ESTIMACIÓN GRUESA, NUNCA UNA FECHA COMPROMETIDA. La fórmula es:

			ritmo   = avance_real / días transcurridos desde date_start   [pp/día]
			atraso  = (avance_planificado − avance_real) / ritmo          [días]

		Si el proyecto todavía no tiene ritmo propio se usa el que el plan exige
		(100 pp repartidos en la duración del proyecto). Guardas, porque un ritmo
		calculado sobre pocos días proyecta desvíos absurdos:

		- None si el proyecto lleva menos días que el mínimo configurado (default 7).
		- None si no tiene plan cargado: sin plan no hay contra qué comparar.
		- Tope de ±90 días.

		Al exponerlo en el frontend va siempre etiquetado como "estimado".
		"""
		if not values.get("has_plan") or not project.date_start:
			return None
		elapsed = (today - project.date_start).days
		if elapsed < params["deviation_min_elapsed_days"]:
			return None
		gap = values["progress_planned"] - values["progress_real"]
		if gap <= 0:
			return 0
		progress_real = values["progress_real"]
		rate = progress_real / elapsed if elapsed > 0 and progress_real else 0.0
		if not rate:
			duration = (project.date - project.date_start).days if project.date else 0
			rate = 100.0 / duration if duration > 0 else 0.0
		if not rate:
			return None
		return max(-90, min(90, int(round(gap / rate))))

	@api.depends("progress_real", "progress_planned", "date_start", "date")
	def _compute_deviation_days(self):
		# Un Integer no puede ser nulo: el campo queda en 0 y es el RPC el que distingue
		# "no calculable" mandando None.
		params = dashboard_params.get_params(self.env)
		today = fields.Date.context_today(self)
		for project in self:
			values = {
				"has_plan": project.has_dashboard_plan,
				"progress_real": project.progress_real,
				"progress_planned": project.progress_planned,
			}
			project.deviation_days = self._primate_deviation_days(project, values, params, today) or 0

	# ------------------------------------------------------------------
	# Semáforo
	# ------------------------------------------------------------------

	def _primate_milestone_risk_map(self, milestone_map, params, today):
		"""{project_id: (días del hito más vencido, % de tareas abiertas del hito próximo)}."""
		overdue = dict.fromkeys(self.ids, 0)
		soon_ratio = dict.fromkeys(self.ids, 0.0)
		soon_milestone_ids = []
		soon_by_project = defaultdict(list)
		for project_id, milestones in milestone_map.items():
			for milestone in milestones:
				if milestone["is_reached"] or not milestone["deadline"]:
					continue
				delta = (today - milestone["deadline"]).days
				if delta > 0:
					overdue[project_id] = max(overdue.get(project_id, 0), delta)
				elif -delta < params["health_milestone_soon_days"]:
					soon_milestone_ids.append(milestone["id"])
					soon_by_project[project_id].append(milestone["id"])
		if soon_milestone_ids:
			open_count = defaultdict(int)
			total_count = defaultdict(int)
			for milestone, state, count in self.env["project.task"]._read_group(
				[("milestone_id", "in", soon_milestone_ids), ("state", "!=", CANCELED_STATE)],
				["milestone_id", "state"],
				["__count"],
			):
				total_count[milestone.id] += count
				if state != DONE_STATE:
					open_count[milestone.id] += count
			for project_id, milestone_ids in soon_by_project.items():
				ratios = [
					open_count[milestone_id] / total_count[milestone_id] * 100.0
					for milestone_id in milestone_ids
					if total_count[milestone_id]
				]
				if ratios:
					soon_ratio[project_id] = max(ratios)
		return overdue, soon_ratio

	@api.model
	def _primate_next_milestone(self, milestones, today):
		"""Primer hito no alcanzado, ordenado por fecha (los hitos ya vienen ordenados).

		No se usa el `next_milestone_id` del core porque ese ordena por secuencia antes
		que por fecha; acá interesa el próximo vencimiento, que es lo que mira el semáforo.
		"""
		for milestone in milestones:
			if milestone["is_reached"]:
				continue
			deadline = milestone["deadline"]
			overdue_days = (today - deadline).days if deadline else 0
			return {
				"id": milestone["id"],
				"name": milestone["name"],
				"deadline": deadline,
				"overdue_days": max(overdue_days, 0),
			}
		return None

	def _primate_health_metrics(self, params=None, today=None):
		"""Métricas por proyecto que alimentan el semáforo y el dashboard."""
		if params is None:
			params = dashboard_params.get_params(self.env)
		today = today or fields.Date.context_today(self)
		milestone_map = self._primate_milestone_map()
		real_map = self._primate_progress_real_map(params.get("progress_method"))
		planned_map = self._primate_progress_planned_map(milestone_map, today)
		sold_map = self._primate_sold_hours_map()
		consumed_map = self._primate_consumed_hours_map()
		overdue_map, soon_ratio_map = self._primate_milestone_risk_map(milestone_map, params, today)
		metrics = {}
		for project in self:
			origin_id = project._origin.id
			planned, estimated, has_plan = planned_map.get(project.id, (0.0, True, False))
			values = {
				"next_milestone": self._primate_next_milestone(milestone_map.get(origin_id, []), today),
				"progress_real": real_map.get(origin_id, 0.0),
				"progress_planned": planned,
				"progress_plan_is_estimated": estimated,
				"has_plan": has_plan,
				# None = el usuario no tiene permiso para ver el dato, distinto de cero.
				"sold_hours": sold_map.get(origin_id),
				"consumed_hours": consumed_map.get(origin_id),
				"overdue_milestone_days": overdue_map.get(origin_id, 0),
				"milestone_soon_open_ratio": soon_ratio_map.get(origin_id, 0.0),
			}
			values["health_state"] = self._primate_health_state(values, params)
			values["deviation_days"] = self._primate_deviation_days(project, values, params, today)
			metrics[project.id] = values
		return metrics

	@api.model
	def _primate_health_state(self, values, params):
		"""Reglas de la sección 1.6, evaluadas en orden: la primera que aplica gana."""
		progress_real = values["progress_real"]
		progress_planned = values["progress_planned"]
		# Si el usuario no puede leer ventas o timesheets no hay dato de horas: las reglas
		# que dependen de ellas se saltean en vez de evaluarse contra un cero inventado.
		sold_hours = values["sold_hours"] or 0.0
		consumed_hours = values["consumed_hours"]
		if consumed_hours is None:
			sold_hours = 0.0
			consumed_hours = 0.0
		hours_ratio = consumed_hours / sold_hours * 100.0 if sold_hours else 0.0
		if progress_real < progress_planned - params["health_red_progress_gap"]:
			return "critical"
		if (
			sold_hours
			and hours_ratio >= params["health_red_hours_ratio"]
			and progress_real < params["health_red_progress_max"]
		):
			return "critical"
		if values["overdue_milestone_days"] > params["health_milestone_overdue_days"]:
			return "critical"
		if progress_real < progress_planned - params["health_yellow_progress_gap"]:
			return "at_risk"
		if (
			sold_hours
			and hours_ratio >= params["health_yellow_hours_ratio"]
			and progress_real < params["health_yellow_progress_max"]
		):
			return "at_risk"
		if values["milestone_soon_open_ratio"] > params["health_milestone_open_ratio"]:
			return "at_risk"
		return "on_track"

	@api.depends(
		"task_ids.state",
		"task_ids.allocated_hours",
		"task_ids.effective_hours",
		"task_ids.milestone_id",
		"milestone_ids.deadline",
		"milestone_ids.planned_progress",
		"milestone_ids.is_reached",
		"timesheet_ids.unit_amount",
		"sale_line_id",
		"date_start",
		"date",
	)
	def _compute_health_state(self):
		metrics = self._primate_health_metrics()
		for project in self:
			project.health_state = metrics.get(project.id, {}).get("health_state", "on_track")

	def action_recompute_health_state(self):
		"""Recálculo manual del semáforo, para no esperar al cron."""
		self.env.add_to_compute(self._fields["health_state"], self)
		self.env.flush_all()
		return True

	@api.model
	def _cron_recompute_health_state(self):
		"""Respaldo diario: el semáforo depende de la fecha de hoy, no solo de los datos."""
		projects = self.search([("active", "=", True), ("is_template", "=", False)])
		projects.action_recompute_health_state()
		_logger.info("Dashboard: recalculado el semáforo de %s proyectos.", len(projects))
		return True

	# ------------------------------------------------------------------
	# Carga por área (usado por el dashboard y por los botones de las tarjetas)
	# ------------------------------------------------------------------

	@api.model
	def _primate_blocked_task_domain(self):
		"""Bloqueada por cualquiera de las tres vías: campo propio, estado o etiqueta."""
		blocked_tag_ids = dashboard_params.get_ids(self.env, "blocked_tag_ids")
		domain = ["|", ("blocking_state", "=", "blocked"), ("state", "=", WAITING_STATE)]
		if blocked_tag_ids:
			domain = ["|"] + domain + [("tag_ids", "in", blocked_tag_ids)]
		return domain

	@api.model
	def _primate_waiting_customer_task_domain(self):
		waiting_tag_ids = dashboard_params.get_ids(self.env, "waiting_customer_tag_ids")
		domain = [("blocking_state", "=", "waiting_customer")]
		if waiting_tag_ids:
			domain = ["|"] + domain + [("tag_ids", "in", waiting_tag_ids)]
		return domain
