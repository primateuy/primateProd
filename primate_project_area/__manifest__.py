# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

{
	"name": "Primate Project Area",
	"summary": "Área de trabajo con responsable, en el proyecto y heredada por la tarea.",
	"description": """
Área de trabajo (Primate)
=========================

Define `primate.area` -- un área con RESPONSABLE -- y la cuelga del proyecto, de la tarea y del
empleado. El área vive en el PROYECTO y la tarea la hereda, pero se puede cambiar en la tarea:
una tarea administrativa dentro de un proyecto técnico es un caso real, no un error de carga.

Es la definición ÚNICA del área para todo el ecosistema: la usan el dashboard ejecutivo de
proyectos (tarjetas de carga por área) y el rol Gestor de Proyectos de Sagui (alcance de la
auditoría y a quién se le proponen los cambios). Por eso vive en un módulo propio y no dentro de
ninguno de los dos.
""",
	"version": "19.0.1.0.0",
	"category": "Services/Project",
	"author": "PrimateUY",
	"website": "https://primateuy.com",
	"license": "AGPL-3",
	"depends": [
		"project",
		"hr",
	],
	"data": [
		"security/ir.model.access.csv",
		"data/primate_area_data.xml",
		"views/primate_area_views.xml",
		"views/project_project_views.xml",
		"views/project_task_views.xml",
		"views/hr_employee_views.xml",
	],
	"installable": True,
	"application": False,
}
