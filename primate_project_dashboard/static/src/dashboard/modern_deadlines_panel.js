import { Component } from "@odoo/owl";
import { formatDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import {
	alertChipLabel,
	alertDate,
	alertIcon,
	alertTypeLabel,
	hiddenAlertCount,
	isCritical,
	openRecordTooltip,
	snoozeTooltip,
} from "./alert_format";

/**
 * Alertas de la vista moderna. La fecha del badge sólo aparece donde es exacta; el color
 * es la severidad de la alerta, igual que en el panel clásico.
 */
export class ModernDeadlinesPanel extends Component {
	static template = "primate_project_dashboard.ModernDeadlinesPanel";
	static props = {
		alerts: Array,
		total: Number,
		today: { type: String, optional: true },
		onOpenRecord: Function,
		onSnooze: Function,
	};

	get items() {
		return this.props.alerts.map((alert) => {
			const date = alertDate(alert, this.props.today);
			return {
				alert,
				severity: isCritical(alert) ? "critical" : "at_risk",
				typeLabel: alertTypeLabel(alert),
				chip: alertChipLabel(alert),
				icon: alertIcon(alert),
				// El mes abreviado sale en el idioma del usuario; algunos locales le agregan punto.
				month: date ? date.toFormat("LLL").replace(".", "") : "",
				day: date ? date.toFormat("d") : "",
				dateTitle: date ? formatDate(date) : "",
			};
		});
	}

	get hiddenCount() {
		return hiddenAlertCount(this.props.alerts, this.props.total);
	}

	get hiddenLabel() {
		return _t("and %s more alerts", this.hiddenCount);
	}

	get openTooltip() {
		return openRecordTooltip();
	}

	get snoozeTooltip() {
		return snoozeTooltip();
	}
}
