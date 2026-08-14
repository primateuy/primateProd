import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class AlertsPanel extends Component {
	static template = "primate_project_dashboard.AlertsPanel";
	static props = {
		alerts: Array,
		total: Number,
		onOpenRecord: Function,
		onSnooze: Function,
	};

	/** El panel no se pagina en v1: si hay más, al menos se dice cuántas. */
	get hiddenCount() {
		return Math.max(this.props.total - this.props.alerts.length, 0);
	}

	severityClass(alert) {
		return alert.severity === "danger" ? "o_primate_alert_danger" : "o_primate_alert_warning";
	}

	get snoozeTooltip() {
		return _t("Dismiss this alert for a week");
	}

	get openTooltip() {
		return _t("Open the related record");
	}
}
