import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import {
	formatMargin,
	formatPercentage,
	formatSignedPercentage,
	hoursDeviationTone,
	hoursDeviationTooltip,
	marginTone,
} from "./kpi_format";

/**
 * Acento del badge fijado por KPI y no por posición: si cambia el orden o el usuario
 * no ve el margen, cada uno conserva el suyo. Los KPIs que expresan salud no llevan
 * acento: su badge toma el color del tono, igual que el número.
 */
const KPI_ACCENTS = {
	active_projects: "blue",
	plan_compliance: "violet",
	margin_estimate: "teal",
};
// El cuarto acento queda para el KPI sin dato: gris, como el "—" que muestra.
const NO_DATA_ACCENT = "slate";

export class ModernKpiCards extends Component {
	static template = "primate_project_dashboard.ModernKpiCards";
	static props = {
		kpis: Object,
		config: Object,
	};

	get cards() {
		const { kpis, config } = this.props;
		const cards = [
			{
				key: "active_projects",
				icon: "fa-folder-open-o",
				label: _t("Active projects"),
				value: String(kpis.active_projects ?? ""),
				tone: null,
			},
			{
				key: "at_risk",
				icon: "fa-exclamation-triangle",
				label: _t("At risk"),
				value: String(kpis.at_risk ?? ""),
				// Como en la clásica: el número de proyectos en riesgo va siempre en rojo.
				tone: "critical",
			},
			{
				key: "plan_compliance",
				icon: "fa-bullseye",
				label: _t("Plan compliance"),
				value: formatPercentage(kpis.plan_compliance),
				tone: null,
			},
			{
				key: "hours_deviation",
				icon: "fa-clock-o",
				label: _t("Hours deviation"),
				value: formatSignedPercentage(kpis.hours_deviation),
				tone: hoursDeviationTone(kpis.hours_deviation),
				tooltip: hoursDeviationTooltip(kpis, config),
			},
		];
		if (config.can_see_margin) {
			cards.push({
				key: "margin_estimate",
				icon: "fa-money",
				label: _t("Estimated margin"),
				value: formatMargin(kpis.margin_estimate, kpis.currency_id),
				tone: marginTone(kpis.margin_estimate),
			});
		}
		return cards.map((card) => ({ ...card, color: this.badgeColor(card) }));
	}

	badgeColor(card) {
		if (card.tone === "muted") {
			return NO_DATA_ACCENT;
		}
		return card.tone || KPI_ACCENTS[card.key];
	}
}
