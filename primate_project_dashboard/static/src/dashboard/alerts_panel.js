import { Component } from "@odoo/owl";
import { hiddenAlertCount, isCritical, openRecordTooltip, snoozeTooltip } from "./alert_format";

export class AlertsPanel extends Component {
	static template = "primate_project_dashboard.AlertsPanel";
	static props = {
		alerts: Array,
		total: Number,
		onOpenRecord: Function,
		onSnooze: Function,
	};

	get hiddenCount() {
		return hiddenAlertCount(this.props.alerts, this.props.total);
	}

	severityClass(alert) {
		return isCritical(alert) ? "o_primate_alert_danger" : "o_primate_alert_warning";
	}

	get snoozeTooltip() {
		return snoozeTooltip();
	}

	get openTooltip() {
		return openRecordTooltip();
	}
}
