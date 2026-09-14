import { _t } from "@web/core/l10n/translation";
import { NO_DATA } from "./kpi_format";

/**
 * Áreas: capacidad ocupada y color, compartidos por las tarjetas clásicas, el donut y la
 * carga por área de la vista moderna.
 */

function hasCapacity(area) {
	return area.capacity_ratio !== null && area.capacity_ratio !== undefined;
}

export function capacityLabel(area) {
	return hasCapacity(area) ? `${Math.round(area.capacity_ratio)}%` : NO_DATA;
}

export function capacityTooltip(area) {
	if (!hasCapacity(area)) {
		return _t("No employee is assigned to this area, so there is no capacity to compare against.");
	}
	return _t("%(committed)s h committed out of %(available)s h available", {
		committed: area.committed_hours,
		available: area.available_hours,
	});
}

/** Mismo criterio que el semáforo, pero sobre ocupación. Sin equipo cargado no hay lectura. */
export function capacityState(area) {
	if (!hasCapacity(area)) {
		return "no_plan";
	}
	if (area.capacity_ratio >= 90) {
		return "critical";
	}
	if (area.capacity_ratio >= 75) {
		return "at_risk";
	}
	return "on_track";
}

export function capacityWidth(area) {
	return `${Math.min(Math.max(area.capacity_ratio || 0, 0), 100)}%`;
}

// Orden de uso de la paleta: tres acentos de color, el gris azulado recién como cuarto
// (en este dashboard el gris ya dice "sin plan", no conviene dárselo a un área grande),
// y desde la quinta área las variantes de luminosidad.
const PREFERRED_COLORS = ["blue", "violet", "teal"];
const FALLBACK_COLORS = ["slate", "blue_alt", "violet_alt", "teal_alt", "slate_alt"];

/** Hash chico y determinístico: el mismo code da el mismo número en cualquier base. */
function codeHash(code) {
	let hash = 0;
	for (const char of code || "") {
		hash = (hash * 31 + char.codePointAt(0)) >>> 0;
	}
	return hash;
}

/**
 * Color por área, atado al code y no a la posición. Cada área prefiere el acento que le
 * toca por su code; si ya lo tomó un área anterior del catálogo, pasa al siguiente acento
 * libre y, agotados los tres, al resto de la paleta en orden. Con cuatro áreas o menos no
 * se repite ningún color, y sumar un área al final del catálogo no le cambia el color a
 * las demás. Con más de ocho se repite: el nombre del área las distingue.
 */
export function areaColors(areas) {
	const taken = new Set();
	const colors = {};
	for (const area of areas) {
		const preferred = codeHash(area.area) % PREFERRED_COLORS.length;
		const candidates = [
			...PREFERRED_COLORS.map((_, step) => PREFERRED_COLORS[(preferred + step) % PREFERRED_COLORS.length]),
			...FALLBACK_COLORS,
		];
		const color = candidates.find((candidate) => !taken.has(candidate)) || PREFERRED_COLORS[preferred];
		taken.add(color);
		colors[area.area] = color;
	}
	return colors;
}

/** Primera letra o dígito del nombre, para los círculos con inicial. */
export function initialOf(name) {
	const match = (name || "").match(/[\p{L}\p{N}]/u);
	return match ? match[0].toUpperCase() : "?";
}
