import { Component } from "@odoo/owl";
import {
	NO_DATA,
	formatMargin,
	formatPercentage,
	formatSignedPercentage,
	hoursDeviationTone,
	hoursDeviationTooltip,
	marginTone,
} from "./kpi_format";

// Los tonos de salud en las clases de texto de Bootstrap que usa la vista clásica.
const TONE_CLASSES = {
	muted: "text-muted",
	on_track: "text-success",
	at_risk: "text-warning",
	critical: "text-danger",
};

export class KpiCards extends Component {
	static template = "primate_project_dashboard.KpiCards";
	static props = {
		kpis: Object,
		config: Object,
	};

	get noData() {
		return NO_DATA;
	}

	formatPercentage(value) {
		return formatPercentage(value);
	}

	formatSignedPercentage(value) {
		return formatSignedPercentage(value);
	}

	formatMargin(value) {
		return formatMargin(value, this.props.kpis.currency_id);
	}

	get hoursDeviationTooltip() {
		return hoursDeviationTooltip(this.props.kpis, this.props.config);
	}

	get deviationClass() {
		return TONE_CLASSES[hoursDeviationTone(this.props.kpis.hours_deviation)];
	}

	get marginClass() {
		return TONE_CLASSES[marginTone(this.props.kpis.margin_estimate)] || "";
	}
}
