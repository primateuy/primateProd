import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

/**
 * Formato y semántica de los KPIs del portafolio, compartidos por las dos vistas: la
 * clásica y la moderna muestran los mismos valores con los mismos criterios.
 */

/** El guion largo marca "sin dato"; el cero se reserva para el cero real. */
export const NO_DATA = "—";

function isMissing(value) {
	return value === null || value === undefined;
}

export function formatPercentage(value) {
	return isMissing(value) ? NO_DATA : `${Math.round(value)}%`;
}

export function formatSignedPercentage(value) {
	if (isMissing(value)) {
		return NO_DATA;
	}
	const sign = value > 0 ? "+" : "";
	return `${sign}${Math.round(value)}%`;
}

export function formatMargin(value, currencyId) {
	return isMissing(value) ? NO_DATA : formatMonetary(value, { currencyId });
}

export function hoursDeviationTooltip(kpis, config) {
	if (kpis.hours_deviation !== null) {
		return "";
	}
	if (!config.can_see_sale_data || !config.can_see_timesheet_data) {
		return _t("You do not have access to the hours data of these projects.");
	}
	return _t("No project in this selection has sold hours to compare against.");
}

/**
 * Tonos de salud con los nombres del semáforo: "muted" es sin dato y null es un valor
 * sin lectura de salud. Cada vista los traduce a sus propias clases.
 */
export function hoursDeviationTone(value) {
	if (isMissing(value)) {
		return "muted";
	}
	// Consumir más horas de las previstas es riesgo; quedar por debajo, no.
	return value > 0 ? "at_risk" : "on_track";
}

export function marginTone(value) {
	if (isMissing(value)) {
		return "muted";
	}
	return value < 0 ? "critical" : null;
}
