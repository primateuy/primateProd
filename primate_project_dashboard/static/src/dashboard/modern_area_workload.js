import { Component } from "@odoo/owl";
import { areaColors, capacityLabel, capacityState, capacityTooltip, capacityWidth, initialOf } from "./area_format";

/**
 * Carga por área de la vista moderna. El círculo lleva el mismo color que el segmento
 * del área en el donut; la barra de ocupación, el semáforo, igual que la tarjeta clásica.
 */
export class ModernAreaWorkload extends Component {
	static template = "primate_project_dashboard.ModernAreaWorkload";
	static props = {
		areas: Array,
		onOpenTasks: Function,
	};

	get rows() {
		const colors = areaColors(this.props.areas);
		return this.props.areas.map((area) => ({
			area,
			color: colors[area.area],
			initial: initialOf(area.name),
			state: capacityState(area),
			label: capacityLabel(area),
			tooltip: capacityTooltip(area),
			width: capacityWidth(area),
		}));
	}
}
