import { registry } from "@web/core/registry";

/**
 * Recorrido mínimo del dashboard. Es la única verificación que ejecuta el render de
 * verdad en un navegador: si una plantilla o un componente se rompe, esto falla.
 */
registry.category("web_tour.tours").add("primate_project_dashboard_tour", {
	url: "/odoo/action-primate_project_dashboard.action_project_dashboard",
	steps: () => [
		{
			content: "El dashboard carga y muestra la tabla de proyectos",
			trigger: ".o_primate_dashboard .o_primate_table tbody tr",
			run: () => {},
		},
		{
			content: "Los KPIs del portafolio están",
			trigger: ".o_primate_kpi_row .o_primate_kpi_card:first-child .o_primate_kpi_value",
			run: () => {},
		},
		{
			content: "Aplicar el filtro de solo en riesgo",
			trigger: ".o_primate_dashboard_content button:contains('At risk only')",
			run: "click",
		},
		{
			content: "Queda solo lo crítico",
			trigger: ".o_primate_table tbody tr .o_primate_health_critical",
			run: () => {},
		},
		{
			content: "Quitar el filtro",
			trigger: ".o_primate_dashboard_content button:contains('At risk only')",
			run: "click",
		},
		{
			content: "Las tarjetas de área se dibujan",
			trigger: ".o_primate_area_row .o_primate_card",
			run: () => {},
		},
		{
			content: "Click en un número de área abre la lista de tareas",
			trigger: ".o_primate_area_row a.o_primate_area_link:first",
			run: "click",
		},
		{
			content: "Estamos en la lista de tareas",
			trigger: ".o_list_view, .o_kanban_view",
			run: () => {},
		},
		{
			content: "Volver al dashboard",
			trigger: ".o_breadcrumb .o_back_button, .breadcrumb-item:first a",
			run: "click",
		},
		{
			content: "El panel de alertas está",
			trigger: ".o_primate_alerts .o_primate_alert",
			run: () => {},
		},
		{
			content: "Silenciar la primera alerta",
			trigger: ".o_primate_alerts .o_primate_alert:first .fa-bell-slash-o",
			run: "click",
		},
		{
			content: "El dashboard sigue en pie después del snooze",
			trigger: ".o_primate_dashboard .o_primate_table",
			run: () => {},
		},
		{
			content: "Abrir un proyecto desde la fila",
			trigger: ".o_primate_table tbody tr:first",
			run: "click",
		},
		{
			content: "Se abre el formulario del proyecto",
			trigger: ".o_form_view .o_form_sheet",
			run: () => {},
		},
	],
});
