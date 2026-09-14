# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

{
	"name": "Project Executive Dashboard",
	"summary": "Executive project dashboard: health status, real vs planned progress, workload by area and alerts.",
	"version": "19.0.1.2.0",
	"category": "Services/Project",
	"author": "PrimateUY",
	"website": "https://primateuy.com",
	"license": "AGPL-3",
	"depends": [
		"project",
		"primate_project_area",
		"sale_timesheet",
		"hr_timesheet",
	],
	"data": [
		"security/security.xml",
		"security/ir.model.access.csv",
		"data/ir_cron.xml",
		"views/project_project_views.xml",
		"views/project_task_views.xml",
		"views/project_milestone_views.xml",
		"views/project_progress_snapshot_views.xml",
		"views/res_config_settings_views.xml",
		"views/dashboard_views.xml",
	],
	"assets": {
		"web.assets_backend": [
			"primate_project_dashboard/static/src/dashboard/**/*",
			# El oscuro va sólo en su bundle; sin esto el glob lo mete también en el claro.
			("remove", "primate_project_dashboard/static/src/dashboard/**/*.dark.scss"),
		],
		"web.assets_web_dark": [
			"primate_project_dashboard/static/src/dashboard/**/*.dark.scss",
		],
		"web.assets_tests": [
			"primate_project_dashboard/static/tests/tours/**/*",
		],
	},
	"installable": True,
	"application": False,
}
