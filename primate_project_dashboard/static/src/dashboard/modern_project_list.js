import { Component } from "@odoo/owl";
import { initialOf } from "./area_format";
import { NO_DATA } from "./kpi_format";
import * as projectFormat from "./project_format";

export class ModernProjectList extends Component {
	static template = "primate_project_dashboard.ModernProjectList";
	static props = {
		projects: Array,
		config: Object,
		total: Number,
		hasMore: Boolean,
		loadingMore: Boolean,
		onOpenProject: Function,
		onLoadMore: Function,
	};

	setup() {
		// Los formatos que dependen de la configuración se resuelven acá; el resto se
		// usa tal cual desde la plantilla.
		this.format = {
			...projectFormat,
			hoursTooltip: (row) => projectFormat.hoursTooltip(row, this.props.config),
			marginTooltip: (row) => projectFormat.marginTooltip(row, this.props.config),
			formatMargin: (row) => projectFormat.formatRowMargin(row, this.props.config.currency_id),
		};
	}

	get noData() {
		return NO_DATA;
	}

	initial(row) {
		return initialOf(row.name);
	}

	/** La fila es un botón: Enter y espacio abren el proyecto, como el click. */
	onRowKeydown(ev, row) {
		if (ev.key === "Enter" || ev.key === " ") {
			ev.preventDefault();
			this.props.onOpenProject(row.id);
		}
	}
}
