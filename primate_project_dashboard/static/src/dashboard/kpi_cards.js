import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class KpiCards extends Component {
	static template = "primate_project_dashboard.KpiCards";
	static props = {
		kpis: Object,
		config: Object,
	};

	/** El guion largo marca "sin dato"; el cero se reserva para el cero real. */
	get noData() {
		return "—";
	}

	formatPercentage(value) {
		if (value === null || value === undefined) {
			return this.noData;
		}
		return `${value.toFixed(0)}%`;
	}

	formatSignedPercentage(value) {
		if (value === null || value === undefined) {
			return this.noData;
		}
		const sign = value > 0 ? "+" : "";
		return `${sign}${value.toFixed(0)}%`;
	}

	formatMargin(value) {
		if (value === null || value === undefined) {
			return this.noData;
		}
		return formatMonetary(value, { currencyId: this.props.kpis.currency_id });
	}

	get hoursDeviationTooltip() {
		if (this.props.kpis.hours_deviation !== null) {
			return "";
		}
		if (!this.props.config.can_see_sale_data || !this.props.config.can_see_timesheet_data) {
			return _t("You do not have access to the hours data of these projects.");
		}
		return _t("No project in this selection has sold hours to compare against.");
	}

	get deviationClass() {
		const value = this.props.kpis.hours_deviation;
		if (value === null || value === undefined) {
			return "text-muted";
		}
		return value > 0 ? "text-warning" : "text-success";
	}

	get marginClass() {
		const value = this.props.kpis.margin_estimate;
		if (value === null || value === undefined) {
			return "text-muted";
		}
		return value < 0 ? "text-danger" : "";
	}
}
