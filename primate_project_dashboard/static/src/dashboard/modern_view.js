import { Component } from "@odoo/owl";
import { ModernKpiCards } from "./modern_kpi_cards";
import { dashboardViewProps } from "./view_props";

/**
 * Vista moderna: sólo presentación, con las mismas props que la clásica. Todo su
 * estilo cuelga de .o_ppd_modern para no tocar la clásica ni los estilos de Odoo.
 */
export class DashboardModernView extends Component {
	static template = "primate_project_dashboard.DashboardModernView";
	static components = { ModernKpiCards };
	static props = dashboardViewProps;
}
