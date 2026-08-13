# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

"""Parámetros de configuración del dashboard.

Todos los umbrales viven en ir.config_parameter y se editan desde
Ajustes → Proyectos. Este módulo centraliza las claves y sus defaults para que
no haya constantes repartidas por el código.
"""

PARAM_PREFIX = "primate_project_dashboard."

# Umbrales del semáforo (sección 1.6 de la especificación) y demás parámetros.
PARAM_DEFAULTS = {
	# Rojo
	"health_red_progress_gap": 15.0,
	"health_red_hours_ratio": 90.0,
	"health_red_progress_max": 70.0,
	"health_milestone_overdue_days": 3,
	# Amarillo
	"health_yellow_progress_gap": 5.0,
	"health_yellow_hours_ratio": 80.0,
	"health_yellow_progress_max": 80.0,
	"health_milestone_soon_days": 7,
	"health_milestone_open_ratio": 30.0,
	# Alertas
	"alert_no_activity_days": 7,
	"alert_blocked_days": 5,
	# Carga por área
	"capacity_window_days": 10,
	"use_planning_capacity": False,
	# Avance
	"progress_method": "closed",
	"deviation_min_elapsed_days": 7,
	# Dashboard
	"auto_refresh_enabled": False,
	"auto_refresh_interval": 5,
	# Etiquetas (ids de project.tags separados por coma)
	"blocked_tag_ids": "",
	"waiting_customer_tag_ids": "",
}


def _raw(env, key):
	value = env["ir.config_parameter"].sudo().get_param(PARAM_PREFIX + key)
	if value in (None, False, ""):
		return PARAM_DEFAULTS.get(key)
	return value


def get_float(env, key):
	try:
		return float(_raw(env, key))
	except (TypeError, ValueError):
		return float(PARAM_DEFAULTS.get(key) or 0.0)


def get_int(env, key):
	try:
		return int(float(_raw(env, key)))
	except (TypeError, ValueError):
		return int(PARAM_DEFAULTS.get(key) or 0)


def get_bool(env, key):
	value = _raw(env, key)
	if isinstance(value, bool):
		return value
	return str(value).strip().lower() in ("1", "true", "yes")


def get_str(env, key):
	value = _raw(env, key)
	return str(value) if value is not None else ""


def get_ids(env, key):
	"""Devuelve la lista de ids guardada como cadena separada por comas."""
	value = _raw(env, key) or ""
	ids = []
	for chunk in str(value).split(","):
		chunk = chunk.strip()
		if chunk.isdigit():
			ids.append(int(chunk))
	return ids


def get_params(env):
	"""Todos los parámetros resueltos de una sola vez, para el RPC del dashboard."""
	return {
		"health_red_progress_gap": get_float(env, "health_red_progress_gap"),
		"health_red_hours_ratio": get_float(env, "health_red_hours_ratio"),
		"health_red_progress_max": get_float(env, "health_red_progress_max"),
		"health_milestone_overdue_days": get_int(env, "health_milestone_overdue_days"),
		"health_yellow_progress_gap": get_float(env, "health_yellow_progress_gap"),
		"health_yellow_hours_ratio": get_float(env, "health_yellow_hours_ratio"),
		"health_yellow_progress_max": get_float(env, "health_yellow_progress_max"),
		"health_milestone_soon_days": get_int(env, "health_milestone_soon_days"),
		"health_milestone_open_ratio": get_float(env, "health_milestone_open_ratio"),
		"alert_no_activity_days": get_int(env, "alert_no_activity_days"),
		"alert_blocked_days": get_int(env, "alert_blocked_days"),
		"capacity_window_days": get_int(env, "capacity_window_days"),
		"use_planning_capacity": get_bool(env, "use_planning_capacity"),
		"progress_method": get_str(env, "progress_method"),
		"deviation_min_elapsed_days": get_int(env, "deviation_min_elapsed_days"),
		"auto_refresh_enabled": get_bool(env, "auto_refresh_enabled"),
		"auto_refresh_interval": get_int(env, "auto_refresh_interval"),
		"blocked_tag_ids": get_ids(env, "blocked_tag_ids"),
		"waiting_customer_tag_ids": get_ids(env, "waiting_customer_tag_ids"),
	}
