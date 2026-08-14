import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { router } from "@web/core/browser/router";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { AlertsPanel } from "./alerts_panel";
import { AreaCards } from "./area_cards";
import { KpiCards } from "./kpi_cards";
import { ProjectTable } from "./project_table";

// Filtros que viajan en la URL para poder compartir una vista filtrada.
const URL_FILTERS = ["period", "date_from", "date_to", "area", "user_id", "partner_id", "only_at_risk"];

export class ProjectDashboard extends Component {
	static template = "primate_project_dashboard.ProjectDashboard";
	static components = { Layout, KpiCards, ProjectTable, AreaCards, AlertsPanel };
	static props = { ...standardActionServiceProps };
	static path = "primate-project-dashboard";
	static displayName = _t("Executive Dashboard");

	setup() {
		this.orm = useService("orm");
		this.action = useService("action");
		this.state = useState({
			loading: true,
			error: false,
			data: null,
			filters: this.readFiltersFromUrl(),
			// Las filas se acumulan al cargar más; los KPIs y las áreas llegan enteros.
			rows: [],
			offset: 0,
			loadingMore: false,
		});
		onWillStart(() => this.load());
		onWillUnmount(() => this.stopAutoRefresh());
	}

	get selectorAreas() {
		return this.state.data?.selectors?.areas || [];
	}

	get selectorUsers() {
		return this.state.data?.selectors?.users || [];
	}

	get selectorPartners() {
		return this.state.data?.selectors?.partners || [];
	}

	/** Sin esto, el primero que filtre "trimestre pasado" reporta como bug que las horas no cambian. */
	get periodTooltip() {
		return _t(
			"The period selects which projects are listed. Progress, hours and health are " +
				"always calculated as of today."
		);
	}

	get periods() {
		return [
			{ value: "month", label: _t("This month") },
			{ value: "quarter", label: _t("This quarter") },
			{ value: "custom", label: _t("Custom") },
			{ value: "all", label: _t("All time") },
		];
	}

	readFiltersFromUrl() {
		const current = router.current;
		const filters = { period: "month", only_at_risk: false };
		for (const key of URL_FILTERS) {
			const value = current[key];
			if (value === undefined || value === "") {
				continue;
			}
			if (key === "only_at_risk") {
				filters[key] = value === "1" || value === true;
			} else if (key === "user_id" || key === "partner_id") {
				filters[key] = parseInt(value, 10) || false;
			} else {
				filters[key] = value;
			}
		}
		return filters;
	}

	writeFiltersToUrl() {
		const state = {};
		for (const key of URL_FILTERS) {
			const value = this.state.filters[key];
			if (value === undefined || value === false || value === "") {
				state[key] = undefined;
			} else if (key === "only_at_risk") {
				state[key] = "1";
			} else {
				state[key] = String(value);
			}
		}
		router.pushState(state, { replace: true });
	}

	async load(offset = 0) {
		const loadingMore = offset > 0;
		this.state[loadingMore ? "loadingMore" : "loading"] = true;
		this.state.error = false;
		try {
			const data = await this.orm.call("project.project", "get_dashboard_data", [
				{ ...this.state.filters, offset },
			]);
			this.state.data = data;
			this.state.offset = offset;
			this.state.rows = loadingMore ? [...this.state.rows, ...data.projects] : data.projects;
			this.restartAutoRefresh();
		} catch {
			this.state.error = true;
		} finally {
			this.state[loadingMore ? "loadingMore" : "loading"] = false;
		}
	}

	get hasMoreRows() {
		return this.state.rows.length < (this.state.data?.projects_total || 0);
	}

	loadMore() {
		return this.load(this.state.rows.length);
	}

	async openAlertRecord(alert) {
		const action = await this.orm.call("project.project", "action_open_alert_record", [
			alert.res_model,
			alert.res_id,
			alert.res_ids,
		]);
		this.action.doAction(action);
	}

	async snoozeAlert(alert) {
		await this.orm.call("project.dashboard.alert.snooze", "action_snooze_alert", [
			alert.type,
			alert.res_model,
			alert.res_id,
		]);
		// Se saca del panel sin recargar todo el dashboard.
		this.state.data.alerts = this.state.data.alerts.filter((item) => item.key !== alert.key);
	}

	async openAreaTasks(area, metric) {
		const action = await this.orm.call("project.project", "action_open_area_tasks", [
			area,
			metric,
			this.state.filters,
		]);
		this.action.doAction(action);
	}

	async onFilterChange(key, value) {
		this.state.filters[key] = value;
		if (key === "period" && value !== "custom") {
			this.state.filters.date_from = undefined;
			this.state.filters.date_to = undefined;
		}
		this.writeFiltersToUrl();
		await this.load();  // vuelve a la primera página: los filtros cambiaron
	}

	/**
	 * El parseo va acá y no en la plantilla: OWL resuelve los identificadores sueltos
	 * contra el contexto del componente, así que un `parseInt` inline sería undefined.
	 */
	onIdFilterChange(key, value) {
		return this.onFilterChange(key, parseInt(value, 10) || false);
	}

	onToggleAtRisk() {
		return this.onFilterChange("only_at_risk", !this.state.filters.only_at_risk);
	}

	restartAutoRefresh() {
		this.stopAutoRefresh();
		const config = this.state.data?.config;
		if (!config?.auto_refresh_enabled || !config.auto_refresh_interval) {
			return;
		}
		// Pensado para una pantalla de oficina: recarga silenciosa, sin tocar los filtros.
		this.refreshTimer = setInterval(() => this.load(), config.auto_refresh_interval * 60 * 1000);
	}

	stopAutoRefresh() {
		if (this.refreshTimer) {
			clearInterval(this.refreshTimer);
			this.refreshTimer = null;
		}
	}

	openProject(projectId) {
		this.action.doAction({
			type: "ir.actions.act_window",
			res_model: "project.project",
			res_id: projectId,
			views: [[false, "form"]],
			target: "current",
		});
	}
}

registry.category("actions").add("primate_project_dashboard", ProjectDashboard);
