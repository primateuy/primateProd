import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { router } from "@web/core/browser/router";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { KpiCards } from "./kpi_cards";
import { ProjectTable } from "./project_table";

// Filtros que viajan en la URL para poder compartir una vista filtrada.
const URL_FILTERS = ["period", "date_from", "date_to", "area", "user_id", "partner_id", "only_at_risk"];

export class ProjectDashboard extends Component {
	static template = "primate_project_dashboard.ProjectDashboard";
	static components = { Layout, KpiCards, ProjectTable };
	static props = { ...standardActionServiceProps };
	static path = "primate-project-dashboard";
	static displayName = _t("Project Dashboard");

	setup() {
		this.orm = useService("orm");
		this.action = useService("action");
		this.state = useState({
			loading: true,
			error: false,
			data: null,
			filters: this.readFiltersFromUrl(),
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

	async load() {
		this.state.loading = true;
		this.state.error = false;
		try {
			this.state.data = await this.orm.call("project.project", "get_dashboard_data", [
				this.state.filters,
			]);
			this.restartAutoRefresh();
		} catch {
			this.state.error = true;
		} finally {
			this.state.loading = false;
		}
	}

	async onFilterChange(key, value) {
		this.state.filters[key] = value;
		if (key === "period" && value !== "custom") {
			this.state.filters.date_from = undefined;
			this.state.filters.date_to = undefined;
		}
		this.writeFiltersToUrl();
		await this.load();
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
