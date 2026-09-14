import { _t } from "@web/core/l10n/translation";
import { deserializeDate, formatDate } from "@web/core/l10n/dates";
import { formatMonetary } from "@web/views/fields/formatters";
import { NO_DATA } from "./kpi_format";

/**
 * Formato de las filas de proyecto, compartido por la tabla clásica y la lista
 * moderna: las dos muestran lo mismo con los mismos textos.
 */

export const HEALTH_LABELS = {
	on_track: _t("On Track"),
	at_risk: _t("Attention"),
	critical: _t("At Risk"),
	no_plan: _t("No Plan"),
};

export function healthLabel(row) {
	return HEALTH_LABELS[row.health_state] || row.health_state;
}

/** Ancho de la barra, acotado para que nunca desborde su carril. */
export function barWidth(value) {
	return `${Math.min(Math.max(value || 0, 0), 100)}%`;
}

/** A nivel ejecutivo el decimal no aporta y ensucia: el cálculo interno lo conserva. */
export function percentage(value) {
	return value === null || value === undefined ? NO_DATA : `${Math.round(value)}%`;
}

/** Con _t: armado como template literal, "real" y "planned" quedaban en inglés. */
export function progressLabel(row) {
	return _t("%(real)s real / %(planned)s planned", {
		real: percentage(row.progress_real),
		planned: percentage(row.progress_planned),
	});
}

/** Cada mitad se muestra por separado: el dato que falta puede ser uno solo. */
export function hoursLabel(row) {
	const consumed = row.consumed_hours ?? NO_DATA;
	const sold = row.sold_hours ?? NO_DATA;
	return `${consumed} / ${sold}`;
}

export function hoursTooltip(row, config) {
	if (row.consumed_hours === null && !config.can_see_timesheet_data) {
		return _t("You do not have access to the timesheets of these projects.");
	}
	if (row.sold_hours === null) {
		return config.can_see_sale_data
			? _t("No sales order linked to this project.")
			: _t("You do not have access to the sales data of these projects.");
	}
	return "";
}

export function milestoneTooltip() {
	return _t("You do not have access to the milestones of these projects.");
}

export function planTooltip(row) {
	if (!row.has_plan_curve) {
		return _t("No plan loaded: the project is missing an end date or milestones.");
	}
	return _t(
		"Approximate plan: this project has no milestones with a planned progress, " +
			"so the expected progress is interpolated between its start and end dates."
	);
}

export function milestoneDate(row) {
	if (!row.next_milestone?.deadline) {
		return "";
	}
	return formatDate(deserializeDate(row.next_milestone.deadline));
}

export function overdueLabel(row) {
	const days = row.next_milestone?.overdue_days || 0;
	return _t("overdue by %s days", days);
}

export function formatRowMargin(row, currencyId) {
	if (row.margin_estimate === null || row.margin_estimate === undefined) {
		return NO_DATA;
	}
	return formatMonetary(row.margin_estimate, { currencyId });
}

export function marginTooltip(row, config) {
	if (row.margin_estimate !== null) {
		return "";
	}
	return config.can_see_sale_data
		? _t("No sales order linked to this project.")
		: _t("You do not have access to the sales data of these projects.");
}

/** Solo color: el semáforo mide cronograma, no economía. */
export function isNegativeMargin(row) {
	return row.margin_estimate < 0;
}
