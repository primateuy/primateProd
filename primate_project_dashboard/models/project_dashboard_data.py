# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from . import dashboard_params

MANAGER_GROUP = "primate_project_dashboard.group_dashboard_manager"
AREA_LEAD_GROUP = "primate_project_dashboard.group_dashboard_area_lead"

# Filas por página. Los KPIs y las áreas siguen agregando sobre el total.
DEFAULT_PAGE_SIZE = 30

# Orden de la tabla: primero lo que arde; los sin plan al final, no son un riesgo
# medido sino un dato faltante.
HEALTH_ORDER = {"critical": 0, "at_risk": 1, "on_track": 2, "no_plan": 3}


class ProjectProject(models.Model):
	_inherit = "project.project"

	# ------------------------------------------------------------------
	# Filtros
	# ------------------------------------------------------------------

	@api.model
	def _primate_dashboard_period(self, options, today=None):
		"""(desde, hasta) del período elegido. (None, None) significa sin límite."""
		today = today or fields.Date.context_today(self)
		period = options.get("period") or "month"
		if period == "all":
			return None, None
		if period == "custom":
			return (
				fields.Date.to_date(options.get("date_from")) or None,
				fields.Date.to_date(options.get("date_to")) or None,
			)
		if period == "quarter":
			date_from = today.replace(month=3 * ((today.month - 1) // 3) + 1, day=1)
			return date_from, date_from + relativedelta(months=3, days=-1)
		date_from = today.replace(day=1)
		return date_from, date_from + relativedelta(months=1, days=-1)

	@api.model
	def _primate_dashboard_domain(self, options, today=None, with_selectors=True):
		"""Dominio de los proyectos del dashboard.

		`with_selectors=False` deja fuera área, responsable y cliente: es el conjunto
		sobre el que se ofrecen las opciones de esos mismos filtros.
		"""
		domain = [("is_template", "=", False)]
		# Una etapa plegada es cerrada o cancelada. El campo está restringido por grupo,
		# así que solo se filtra por él si el usuario puede verlo.
		if self.env.user.has_group("project.group_project_stages"):
			domain.append(("stage_id.fold", "=", False))
		# El perfil PM se acota acá y no con una record rule sobre project.project, para
		# no interferir con la operativa del módulo Proyectos (sección 2.5).
		if not self.env.user.has_group(AREA_LEAD_GROUP):
			domain.append(("user_id", "=", self.env.uid))
		date_from, date_to = self._primate_dashboard_period(options, today)
		# Decisión: un proyecto sin fechas aparece en todos los períodos. Es preferible
		# que se vea siempre a que desaparezca del portafolio por un dato faltante.
		if date_to:
			domain += ["|", ("date_start", "=", False), ("date_start", "<=", date_to)]
		if date_from:
			domain += ["|", ("date", "=", False), ("date", ">=", date_from)]
		if with_selectors:
			if options.get("area"):
				domain.append(("task_ids.area", "=", options["area"]))
			if options.get("user_id"):
				domain.append(("user_id", "=", int(options["user_id"])))
			if options.get("partner_id"):
				domain.append(("partner_id", "=", int(options["partner_id"])))
		return domain

	@api.model
	def _primate_dashboard_selectors(self, options, today=None):
		"""Valores disponibles para los filtros de responsable y cliente."""
		domain = self._primate_dashboard_domain(options, today, with_selectors=False)
		users = [
			{"id": user.id, "name": user.display_name}
			for [user] in self._read_group(domain, ["user_id"])
			if user
		]
		partners = [
			{"id": partner.id, "name": partner.display_name}
			for [partner] in self._read_group(domain, ["partner_id"])
			if partner
		]
		areas = [
			{"value": value, "name": label}
			for value, label in self.env["project.task"].fields_get(["area"])["area"]["selection"]
		]
		return {
			"users": sorted(users, key=lambda item: item["name"]),
			"partners": sorted(partners, key=lambda item: item["name"]),
			"areas": areas,
		}

	# ------------------------------------------------------------------
	# RPC único del dashboard
	# ------------------------------------------------------------------

	@api.model
	def get_dashboard_data(self, options=None):
		"""KPIs, filas, áreas y alertas en una sola llamada. Sin sudo: cada usuario ve lo suyo."""
		options = options or {}
		params = dashboard_params.get_params(self.env)
		today = fields.Date.context_today(self)
		can_see_margin = self.env.user.has_group(MANAGER_GROUP)
		# "Sin dato" no es cero: sin lectura sobre las líneas de venta, las horas vendidas
		# y el margen viajan en None y el front muestra "—".
		can_read_sale = self.env["sale.order.line"].has_access("read")
		can_read_timesheet = self.env["account.analytic.line"].has_access("read")
		can_read_milestone = self.env.user.has_group("project.group_project_milestone")

		projects = self.search(self._primate_dashboard_domain(options, today))
		metrics = projects._primate_health_metrics(params, today)
		milestone_map = projects._primate_milestone_map()
		margin_map = {}
		if can_see_margin and can_read_sale and can_read_timesheet:
			margin_map = {project.id: project.margin_estimate for project in projects}

		rows = []
		for project in projects:
			values = metrics.get(project.id, {})
			next_milestone = values.get("next_milestone") if can_read_milestone else None
			# Sin SO vinculada no hay horas vendidas ni margen que mostrar (sección 1.10).
			has_sale_order = values.get("sold_hours") is not None
			rows.append(
				{
					"id": project.id,
					"name": project.display_name,
					"partner_name": project.partner_id.display_name or "",
					"user_id": project.user_id.id or False,
					"user_name": project.user_id.display_name or "",
					"health_state": values.get("health_state", "no_plan"),
					"progress_real": round(values.get("progress_real", 0.0), 1),
					"progress_planned": self._primate_round(values.get("progress_planned")),
					"plan_is_estimated": values.get("progress_plan_is_estimated", True),
					"has_plan": values.get("has_plan", False),
					"has_plan_curve": values.get("has_plan_curve", False),
					"has_sale_order": has_sale_order,
					"consumed_hours": self._primate_round(values.get("consumed_hours")),
					"sold_hours": self._primate_round(values.get("sold_hours")),
					# None = no calculable (proyecto muy nuevo o sin plan), no cero días.
					"deviation_days": values.get("deviation_days"),
					"margin_estimate": (
						margin_map.get(project.id) if can_see_margin and has_sale_order else None
					),
					"next_milestone": self._primate_serialize_milestone(next_milestone),
				}
			)
		if options.get("only_at_risk"):
			# Se filtra sobre el valor recién calculado, no sobre el almacenado, para que
			# el filtro coincida siempre con el semáforo que se está mostrando.
			rows = [row for row in rows if row["health_state"] == "critical"]
		rows.sort(key=lambda row: (HEALTH_ORDER.get(row["health_state"], 9), row["name"]))

		# Los KPIs y las tarjetas de área agregan sobre el total, nunca sobre la página
		# visible: paginar no puede cambiar lo que dice el portafolio.
		kpis = self._primate_dashboard_kpis(rows, can_read_sale, can_see_margin)
		alerts, alerts_total = projects._primate_dashboard_alerts(
			metrics, milestone_map, params, today
		)
		limit = int(options.get("limit") or DEFAULT_PAGE_SIZE)
		offset = int(options.get("offset") or 0)
		page = rows[offset : offset + limit] if limit else rows

		return {
			"kpis": kpis,
			"projects": page,
			"projects_total": len(rows),
			"projects_offset": offset,
			"areas": projects._primate_dashboard_areas(params, today),
			"alerts": alerts,
			"alerts_total": alerts_total,
			"selectors": self._primate_dashboard_selectors(options, today),
			"config": {
				"can_see_margin": can_see_margin,
				"can_see_sale_data": can_read_sale,
				"can_see_timesheet_data": can_read_timesheet,
				"can_see_milestones": can_read_milestone,
				"currency_id": self.env.company.currency_id.id,
				"auto_refresh_enabled": params["auto_refresh_enabled"],
				"auto_refresh_interval": params["auto_refresh_interval"],
				"page_size": DEFAULT_PAGE_SIZE,
				"today": fields.Date.to_string(today),
			},
		}

	@api.model
	def _primate_round(self, value, digits=1):
		"""None viaja tal cual: es "sin dato", no un cero."""
		return None if value is None else round(value, digits)

	@api.model
	def _primate_serialize_milestone(self, milestone):
		if not milestone:
			return None
		return {
			"id": milestone["id"],
			"name": milestone["name"],
			"deadline": fields.Date.to_string(milestone["deadline"]) if milestone["deadline"] else False,
			"overdue_days": milestone["overdue_days"],
		}

	@api.model
	def _primate_dashboard_kpis(self, rows, can_read_sale, can_see_margin):
		"""KPIs del portafolio (sección 1.4)."""
		compliance_weighted = 0.0
		compliance_weight = 0.0
		compliance_plain = 0.0
		compliance_rows = 0
		consumed_total = 0.0
		expected_total = 0.0
		margin_total = 0.0
		margin_rows = 0
		hours_rows = 0
		for row in rows:
			planned = row["progress_planned"]
			# Un proyecto sin curva de plan no entra en el cumplimiento: no hay contra qué
			# medirlo. Contarlo como 100% inflaba el KPI con proyectos sin plan cargado.
			if planned is not None:
				ratio = min(row["progress_real"] / planned, 1.0) if planned > 0 else 1.0
				compliance_plain += ratio
				compliance_rows += 1
				sold_hours = row["sold_hours"] or 0.0
				compliance_weighted += ratio * sold_hours
				compliance_weight += sold_hours
				# El desvío de horas necesita las dos mitades y una expectativa real.
				if row["consumed_hours"] is not None and row["sold_hours"] is not None:
					consumed_total += row["consumed_hours"]
					expected_total += sold_hours * planned / 100.0
					hours_rows += 1
			if row["margin_estimate"] is not None:
				margin_total += row["margin_estimate"]
				margin_rows += 1
		if compliance_weight:
			compliance = compliance_weighted / compliance_weight * 100.0
		elif compliance_rows:
			# Desvío deliberado de la spec 1.4, que pide ponderar siempre por horas
			# vendidas: un portafolio de proyectos internos no tiene ninguna, y ponderar
			# por cero daría siempre vacío. Se cae a promedio simple, que es un dato real.
			compliance = compliance_plain / compliance_rows * 100.0
		else:
			compliance = None
		hours_deviation = None
		if hours_rows and expected_total:
			hours_deviation = (consumed_total - expected_total) / expected_total * 100.0
		margin = None
		if can_see_margin and can_read_sale and margin_rows:
			margin = round(margin_total, 2)
		return {
			"active_projects": len(rows),
			"at_risk": sum(1 for row in rows if row["health_state"] == "critical"),
			"plan_compliance": round(compliance, 1) if compliance is not None else None,
			"hours_deviation": round(hours_deviation, 1) if hours_deviation is not None else None,
			"margin_estimate": margin,
			"currency_id": self.env.company.currency_id.id,
		}

	# ------------------------------------------------------------------
	# Acciones desde el dashboard
	# ------------------------------------------------------------------

	@api.model
	def action_open_dashboard_project(self, project_id):
		"""Abre el formulario del proyecto al hacer click en la fila."""
		return {
			"type": "ir.actions.act_window",
			"res_model": "project.project",
			"res_id": int(project_id),
			"views": [(False, "form")],
			"target": "current",
		}
