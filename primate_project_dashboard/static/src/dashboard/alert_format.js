import { deserializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

/**
 * Alertas: tipo, severidad y fecha, compartidos por el panel clásico y el moderno.
 */

// Tipos cuya fecha sale exacta de age_days: el vencimiento del hito y el día en que se
// bloqueó la tarea. En "sin actividad" age_days puede ser un relleno (proyecto que nunca
// tuvo actividad), y el resto no tiene edad: esos llevan ícono, no fecha.
const DATED_TYPES = new Set(["milestone_overdue", "task_blocked"]);

const TYPE_ICONS = {
	hours_budget: "fa-hourglass-half",
	no_plan: "fa-map-o",
	no_activity: "fa-pause-circle-o",
	missing_timesheets: "fa-clock-o",
};

export function isCritical(alert) {
	return alert.severity === "danger";
}

export function alertTypeLabel(alert) {
	const labels = {
		milestone_overdue: _t("Overdue milestone"),
		task_blocked: _t("Blocked task"),
		hours_budget: _t("Hours budget"),
		no_plan: _t("No plan loaded"),
		no_activity: _t("No recent activity"),
		missing_timesheets: _t("Missing timesheets"),
	};
	return labels[alert.type] || "";
}

/** La fecha detrás de la alerta, o null si no es derivable. `today` es la del servidor. */
export function alertDate(alert, today) {
	if (!DATED_TYPES.has(alert.type) || !today) {
		return null;
	}
	return deserializeDate(today).minus({ days: alert.age_days || 0 });
}

export function alertIcon(alert) {
	return TYPE_ICONS[alert.type] || "fa-bell-o";
}

export function alertChipLabel(alert) {
	if (alert.type === "milestone_overdue") {
		return _t("overdue by %s days", alert.age_days);
	}
	if (alert.type === "task_blocked") {
		return _t("blocked for %s days", alert.age_days);
	}
	return isCritical(alert) ? _t("Critical") : _t("Warning");
}

/** El panel no se pagina en v1: si hay más, al menos se dice cuántas. */
export function hiddenAlertCount(alerts, total) {
	return Math.max(total - alerts.length, 0);
}

export function openRecordTooltip() {
	return _t("Open the related record");
}

export function snoozeTooltip() {
	return _t("Dismiss this alert for a week");
}
