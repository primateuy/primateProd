import { Component } from "@odoo/owl";
import { NO_DATA } from "./kpi_format";
import {
	barWidth,
	formatRowMargin,
	healthLabel,
	hoursLabel,
	hoursTooltip,
	isNegativeMargin,
	marginTooltip,
	milestoneDate,
	milestoneTooltip,
	overdueLabel,
	percentage,
	planTooltip,
	progressLabel,
} from "./project_format";

const HEALTH_CLASSES = {
	on_track: "o_primate_health_on_track",
	at_risk: "o_primate_health_at_risk",
	critical: "o_primate_health_critical",
	no_plan: "o_primate_health_no_plan",
};

export class ProjectTable extends Component {
	static template = "primate_project_dashboard.ProjectTable";
	static props = {
		projects: Array,
		config: Object,
		onOpenProject: Function,
	};

	get noData() {
		return NO_DATA;
	}

	healthLabel(row) {
		return healthLabel(row);
	}

	healthClass(row) {
		return HEALTH_CLASSES[row.health_state] || "";
	}

	barWidth(value) {
		return barWidth(value);
	}

	percentage(value) {
		return percentage(value);
	}

	progressLabel(row) {
		return progressLabel(row);
	}

	hoursLabel(row) {
		return hoursLabel(row);
	}

	hoursTooltip(row) {
		return hoursTooltip(row, this.props.config);
	}

	get milestoneTooltip() {
		return milestoneTooltip();
	}

	planTooltip(row) {
		return planTooltip(row);
	}

	milestoneDate(row) {
		return milestoneDate(row);
	}

	overdueLabel(row) {
		return overdueLabel(row);
	}

	formatMargin(row) {
		return formatRowMargin(row, this.props.config.currency_id);
	}

	marginTooltip(row) {
		return marginTooltip(row, this.props.config);
	}

	marginClass(row) {
		return isNegativeMargin(row) ? "text-danger" : "";
	}
}
