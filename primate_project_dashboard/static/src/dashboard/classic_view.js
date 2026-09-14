import { Component } from "@odoo/owl";
import { AlertsPanel } from "./alerts_panel";
import { AreaCards } from "./area_cards";
import { KpiCards } from "./kpi_cards";
import { ProjectTable } from "./project_table";
import { dashboardViewProps } from "./view_props";

/**
 * Vista clásica: sólo presentación. El estado, la carga y las acciones viven en el
 * componente raíz; la moderna recibe exactamente las mismas props.
 */
export class DashboardClassicView extends Component {
	static template = "primate_project_dashboard.DashboardClassicView";
	static components = { KpiCards, ProjectTable, AreaCards, AlertsPanel };
	static props = dashboardViewProps;
}
