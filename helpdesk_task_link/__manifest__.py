# Copyright 2025 - Abastecimientos
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

{
	"name": "Helpdesk Ticket - Project Task Link",
	"summary": "Asocia tickets de Helpdesk con tareas de Proyecto en ambos sentidos.",
	"version": "19.0.1.0.1",
	"category": "Project",
	"author": "PrimateUY",
	"website": "https://primateuy.com",
	"license": "AGPL-3",
	"depends": [
		"helpdesk",
		"project",
	],
	"data": [
		# Vista del form de ticket fuera en v19 (el form de helpdesk cambió);
		# el vínculo se usa desde la tarea (ticket_ids en project.task).
		"views/project_task_views.xml",
		"views/project_project_views.xml",
	],
	"installable": True,
	"application": False,
}

