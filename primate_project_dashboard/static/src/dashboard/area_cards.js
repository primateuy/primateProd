import { Component } from "@odoo/owl";
import { capacityLabel, capacityState, capacityTooltip, capacityWidth } from "./area_format";
import { NO_DATA } from "./kpi_format";

const CAPACITY_CLASSES = {
	on_track: "o_primate_health_on_track",
	at_risk: "o_primate_health_at_risk",
	critical: "o_primate_health_critical",
	no_plan: "o_primate_health_no_plan",
};

export class AreaCards extends Component {
	static template = "primate_project_dashboard.AreaCards";
	static props = {
		areas: Array,
		onOpenTasks: Function,
	};

	get noData() {
		return NO_DATA;
	}

	capacityLabel(area) {
		return capacityLabel(area);
	}

	capacityTooltip(area) {
		return capacityTooltip(area);
	}

	capacityClass(area) {
		return CAPACITY_CLASSES[capacityState(area)];
	}

	barWidth(area) {
		return capacityWidth(area);
	}
}
