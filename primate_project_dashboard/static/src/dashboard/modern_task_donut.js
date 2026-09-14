import { Component, useState } from "@odoo/owl";
import { areaColors } from "./area_format";

// Geometría del anillo en unidades del viewBox (120 x 120).
const RADIUS = 48;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
// Separación entre segmentos, en las mismas unidades. Con un solo segmento no hay.
const GAP = 2.5;

/** Porcentajes enteros que suman 100 (resto mayor): la leyenda no puede decir 99%. */
export function roundedShares(counts) {
	const total = counts.reduce((sum, count) => sum + count, 0);
	if (!total) {
		return counts.map(() => 0);
	}
	const raw = counts.map((count) => (count / total) * 100);
	const shares = raw.map(Math.floor);
	let remaining = 100 - shares.reduce((sum, share) => sum + share, 0);
	const byRemainder = raw.map((value, index) => [value - shares[index], index]).sort((a, b) => b[0] - a[0]);
	for (const [, index] of byRemainder) {
		if (remaining <= 0) {
			break;
		}
		shares[index] += 1;
		remaining -= 1;
	}
	return shares;
}

export class ModernTaskDonut extends Component {
	static template = "primate_project_dashboard.ModernTaskDonut";
	static props = {
		areas: Array,
		onOpenTasks: Function,
	};

	setup() {
		// Sólo resalta: nada depende del hover.
		this.hover = useState({ area: null });
		this.radius = RADIUS;
	}

	get total() {
		return this.props.areas.reduce((sum, area) => sum + (area.open_tasks || 0), 0);
	}

	get slices() {
		const areas = this.props.areas;
		const total = this.total;
		const colors = areaColors(areas);
		const shares = roundedShares(areas.map((area) => area.open_tasks || 0));
		const gap = areas.filter((area) => area.open_tasks > 0).length > 1 ? GAP : 0;
		let start = 0;
		return areas.map((area, index) => {
			const count = area.open_tasks || 0;
			const length = total ? (count / total) * CIRCUMFERENCE : 0;
			const slice = {
				code: area.area,
				name: area.name,
				count,
				share: shares[index],
				color: colors[area.area],
				dash: `${Math.max(length - gap, 0)} ${CIRCUMFERENCE}`,
				offset: -(start + gap / 2),
			};
			start += length;
			return slice;
		});
	}

	segmentClass(slice) {
		return [
			"o_ppd_donut_segment",
			`o_ppd_color_${slice.color}`,
			this.hover.area === slice.code ? "o_ppd_active" : "",
			this.hover.area && this.hover.area !== slice.code ? "o_ppd_dimmed" : "",
		].join(" ");
	}

	legendClass(slice) {
		return [
			"o_ppd_legend_item",
			this.hover.area === slice.code ? "o_ppd_active" : "",
			slice.count ? "" : "o_ppd_legend_zero",
		].join(" ");
	}

	onHover(code) {
		this.hover.area = code;
	}
}
