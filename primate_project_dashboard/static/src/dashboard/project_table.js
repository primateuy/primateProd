import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatDate, deserializeDate } from "@web/core/l10n/dates";
import { formatMonetary } from "@web/views/fields/formatters";

const HEALTH_LABELS = {
	on_track: _t("On Track"),
	at_risk: _t("Attention"),
	critical: _t("At Risk"),
	no_plan: _t("No Plan"),
};

const HEALTH_CLASSES = {
	on_track: "o_primate_health_on_track",
	at_risk: "o_primate_health_at_risk",
	critical: "o_primate_health_critical",
	no_plan: "o_primate_health_no_plan",
};

export class ProjectTable extends Component {
	static template = "primate_project_dashboard.ProjectTable";
	static props = {
		projects: Array,
		config: Object,
		onOpenProject: Function,
	};

	get noData() {
		return "—";
	}

	healthLabel(row) {
		return HEALTH_LABELS[row.health_state] || row.health_state;
	}

	healthClass(row) {
		return HEALTH_CLASSES[row.health_state] || "";
	}

	/** Ancho de la barra, acotado para que nunca desborde su carril. */
	barWidth(value) {
		return `${Math.min(Math.max(value || 0, 0), 100)}%`;
	}

	/** A nivel ejecutivo el decimal no aporta y ensucia: el cálculo interno lo conserva. */
	percentage(value) {
		return value === null || value === undefined ? this.noData : `${Math.round(value)}%`;
	}

	/** Con _t: armado como template literal, "real" y "planned" quedaban en inglés. */
	progressLabel(row) {
		return _t("%(real)s real / %(planned)s planned", {
			real: this.percentage(row.progress_real),
			planned: this.percentage(row.progress_planned),
		});
	}

	/** Cada mitad se muestra por separado: el dato que falta puede ser uno solo. */
	hoursLabel(row) {
		const consumed = row.consumed_hours ?? this.noData;
		const sold = row.sold_hours ?? this.noData;
		return `${consumed} / ${sold}`;
	}

	hoursTooltip(row) {
		if (row.consumed_hours === null && !this.props.config.can_see_timesheet_data) {
			return _t("You do not have access to the timesheets of these projects.");
		}
		if (row.sold_hours === null) {
			return this.props.config.can_see_sale_data
				? _t("No sales order linked to this project.")
				: _t("You do not have access to the sales data of these projects.");
		}
		return "";
	}

	get milestoneTooltip() {
		return _t("You do not have access to the milestones of these projects.");
	}

	planTooltip(row) {
		if (!row.has_plan_curve) {
			return _t("No plan loaded: the project is missing an end date or milestones.");
		}
		return _t(
			"Approximate plan: this project has no milestones with a planned progress, " +
				"so the expected progress is interpolated between its start and end dates."
		);
	}

	milestoneDate(row) {
		if (!row.next_milestone?.deadline) {
			return "";
		}
		return formatDate(deserializeDate(row.next_milestone.deadline));
	}

	overdueLabel(row) {
		const days = row.next_milestone?.overdue_days || 0;
		return _t("overdue by %s days", days);
	}

	formatMargin(row) {
		if (row.margin_estimate === null || row.margin_estimate === undefined) {
			return this.noData;
		}
		return formatMonetary(row.margin_estimate, { currencyId: this.props.config.currency_id });
	}

	marginTooltip(row) {
		if (row.margin_estimate !== null) {
			return "";
		}
		return this.props.config.can_see_sale_data
			? _t("No sales order linked to this project.")
			: _t("You do not have access to the sales data of these projects.");
	}

	/** Solo color: el semáforo mide cronograma, no economía. */
	marginClass(row) {
		return row.margin_estimate < 0 ? "text-danger" : "";
	}
}
