import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class AreaCards extends Component {
	static template = "primate_project_dashboard.AreaCards";
	static props = {
		areas: Array,
		onOpenTasks: Function,
	};

	get noData() {
		return "—";
	}

	capacityLabel(area) {
		if (area.capacity_ratio === null || area.capacity_ratio === undefined) {
			return this.noData;
		}
		return `${Math.round(area.capacity_ratio)}%`;
	}

	capacityTooltip(area) {
		if (area.capacity_ratio === null || area.capacity_ratio === undefined) {
			return _t("No employee is assigned to this area, so there is no capacity to compare against.");
		}
		return _t("%(committed)s h committed out of %(available)s h available", {
			committed: area.committed_hours,
			available: area.available_hours,
		});
	}

	/** Mismo criterio de color que el semáforo, pero sobre ocupación. */
	capacityClass(area) {
		const ratio = area.capacity_ratio;
		if (ratio === null || ratio === undefined) {
			return "o_primate_health_no_plan";
		}
		if (ratio >= 90) {
			return "o_primate_health_critical";
		}
		if (ratio >= 75) {
			return "o_primate_health_at_risk";
		}
		return "o_primate_health_on_track";
	}

	barWidth(area) {
		return `${Math.min(Math.max(area.capacity_ratio || 0, 0), 100)}%`;
	}
}
