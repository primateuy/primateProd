# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

"""Datos de prueba para la verificación visual del dashboard.

Crea cuatro proyectos que cubren los cuatro casos que el mockup tiene que mostrar
(verde, amarillo, rojo con hito vencido y sin plan cargado) y tres usuarios, uno por
perfil de seguridad. Se ejecuta contra una base de prueba, nunca contra producción:

    odoo-bin shell -c <conf> -d <base> --no-http < docs/seed_demo.py

Los usuarios quedan con contraseña igual al login.
"""

from datetime import date, timedelta

env = env  # noqa: F821 - lo inyecta el shell de Odoo

today = date.today()
Project = env["project.project"]

DEMO_PROJECT_NAMES = ["Implantación ERP", "Integración POS", "Migración v19", "Soporte mensual"]

# Re-ejecutable: se borra lo de la corrida anterior antes de volver a crear.
previous = env["project.project"].with_context(active_test=False).search(
	[("name", "in", DEMO_PROJECT_NAMES)]
)
if previous:
	# Los timesheets y las líneas de venta bloquean el unlink del proyecto.
	env["account.analytic.line"].search([("project_id", "in", previous.ids)]).unlink()
	env["sale.order.line"].search([("project_id", "in", previous.ids)]).order_id.filtered(
		lambda order: order.state != "cancel"
	)._action_cancel()
	previous.write({"sale_line_id": False})
	env["sale.order.line"].search([("project_id", "in", previous.ids)]).write({"project_id": False})
	previous.task_ids.unlink()
	previous.unlink()

Task = env["project.task"]
Milestone = env["project.milestone"]
Users = env["res.users"]
Partner = env["res.partner"]

# ---------------------------------------------------------------------------
# Usuarios, uno por perfil
# ---------------------------------------------------------------------------
BASE_GROUPS = [
	env.ref("base.group_user").id,
	env.ref("project.group_project_user").id,
	env.ref("project.group_project_milestone").id,
	env.ref("hr_timesheet.group_hr_timesheet_user").id,
]

PROFILES = [
	("direccion", "Dirección Demo", "primate_project_dashboard.group_dashboard_manager"),
	("lider", "Líder de Área Demo", "primate_project_dashboard.group_dashboard_area_lead"),
	("pm", "PM Demo", "primate_project_dashboard.group_dashboard_pm"),
]

users = {}
for login, name, group in PROFILES:
	user = Users.search([("login", "=", login)], limit=1)
	values = {
		"name": name,
		"login": login,
		"password": login,
		"group_ids": [(6, 0, BASE_GROUPS + [env.ref(group).id])],
	}
	if user:
		user.write(values)
	else:
		user = Users.create(values)
	users[login] = user

# El líder de área no debe ver el margen: se le quita el grupo de dirección por si
# quedó de una corrida anterior.
users["lider"].write({"group_ids": [(3, env.ref("primate_project_dashboard.group_dashboard_manager").id)]})

# Cuarto usuario, para ver la degradación: líder de área SIN acceso a timesheets ni a
# hitos. Es el que tiene que mostrar "—" en horas, margen y próximo hito.
restringido = Users.search([("login", "=", "restringido")], limit=1)
restringido_values = {
	"name": "Sin Permisos Demo",
	"login": "restringido",
	"password": "restringido",
	"group_ids": [(6, 0, [
		env.ref("base.group_user").id,
		env.ref("project.group_project_user").id,
		env.ref("primate_project_dashboard.group_dashboard_area_lead").id,
	])],
}
if restringido:
	restringido.write(restringido_values)
else:
	restringido = Users.create(restringido_values)
users["restringido"] = restringido

# ---------------------------------------------------------------------------
# Producto de servicio en horas y clientes
# ---------------------------------------------------------------------------
uom_hour = env.ref("uom.product_uom_hour")
service = env["product.product"].search([("name", "=", "Demo Consultoría")], limit=1)
if not service:
	service = env["product.product"].create({
		"name": "Demo Consultoría",
		"type": "service",
		"uom_id": uom_hour.id,
		"list_price": 60.0,
		"service_policy": "ordered_prepaid",
		"invoice_policy": "order",
	})

employee = env["hr.employee"].search([("user_id", "=", users["pm"].id)], limit=1)
if not employee:
	employee = env["hr.employee"].create({
		"name": "PM Demo",
		"user_id": users["pm"].id,
		"hourly_cost": 25.0,
	})
else:
	employee.hourly_cost = 25.0


def get_partner(name):
	partner = Partner.search([("name", "=", name)], limit=1)
	return partner or Partner.create({"name": name})


def make_sale_order(partner, project, hours):
	"""SO confirmada con una línea de servicio imputada al proyecto."""
	order = env["sale.order"].create({
		"partner_id": partner.id,
		"order_line": [(0, 0, {
			"product_id": service.id,
			"product_uom_qty": hours,
			"price_unit": 60.0,
		})],
	})
	order.action_confirm()
	order.order_line.write({"project_id": project.id})
	project.sale_line_id = order.order_line[0].id
	return order


def add_timesheet(project, hours, days_ago=1):
	env["account.analytic.line"].create({
		"name": "Trabajo demo",
		"project_id": project.id,
		"employee_id": employee.id,
		"unit_amount": hours,
		"date": today - timedelta(days=days_ago),
	})


def make_tasks(project, total, done, area, allocated=10.0):
	tasks = Task.create([
		{
			"name": f"{project.name} - tarea {index + 1}",
			"project_id": project.id,
			"allocated_hours": allocated,
			"area": area,
		}
		for index in range(total)
	])
	tasks[:done].write({"state": "1_done"})
	return tasks


# ---------------------------------------------------------------------------
# 1. VERDE: avance real por encima del planificado, hitos al día
# ---------------------------------------------------------------------------
verde = Project.create({
	"name": "Implantación ERP",
	"partner_id": get_partner("Agrosiembra").id,
	"user_id": users["pm"].id,
	"date_start": today - timedelta(days=30),
	"date": today + timedelta(days=30),
	"allow_milestones": True,
	"allow_billable": True,
})
Milestone.create([
	{"project_id": verde.id, "name": "Kickoff", "deadline": today - timedelta(days=20),
	 "planned_progress": 20.0, "is_reached": True},
	{"project_id": verde.id, "name": "Go-live", "deadline": today + timedelta(days=20),
	 "planned_progress": 90.0},
])
make_tasks(verde, total=10, done=8, area="technical")
make_sale_order(get_partner("Agrosiembra"), verde, hours=400)
add_timesheet(verde, 310)

# ---------------------------------------------------------------------------
# 2. AMARILLO: atrasado respecto del plan, pero sin hito vencido ni horas quemadas
# ---------------------------------------------------------------------------
amarillo = Project.create({
	"name": "Integración POS",
	"partner_id": get_partner("New Age Data").id,
	"user_id": users["lider"].id,
	"date_start": today - timedelta(days=30),
	"date": today + timedelta(days=30),
	"allow_milestones": True,
	"allow_billable": True,
})
Milestone.create([
	{"project_id": amarillo.id, "name": "Relevamiento", "deadline": today - timedelta(days=20),
	 "planned_progress": 30.0, "is_reached": True},
	# El plan exige ~63% para hoy contra un 50% real: brecha de 13pp, entre los umbrales
	# de amarillo (5pp) y rojo (15pp). El hito está a 10 días, fuera de la ventana de
	# "próximo a vencer", para que el amarillo salga por la regla de avance y no por otra.
	{"project_id": amarillo.id, "name": "UAT", "deadline": today + timedelta(days=10),
	 "planned_progress": 80.0},
])
make_tasks(amarillo, total=10, done=5, area="functional")
make_sale_order(get_partner("New Age Data"), amarillo, hours=200)
add_timesheet(amarillo, 120)

# ---------------------------------------------------------------------------
# 3. ROJO: hito vencido hace más de 3 días, horas casi agotadas y avance bajo
# ---------------------------------------------------------------------------
rojo = Project.create({
	"name": "Migración v19",
	"partner_id": get_partner("Cliente Retail").id,
	"user_id": users["pm"].id,
	"date_start": today - timedelta(days=60),
	"date": today + timedelta(days=15),
	"allow_milestones": True,
	"allow_billable": True,
})
Milestone.create([
	{"project_id": rojo.id, "name": "Entrega fase 1", "deadline": today - timedelta(days=30),
	 "planned_progress": 40.0, "is_reached": True},
	{"project_id": rojo.id, "name": "Entrega fase 2", "deadline": today - timedelta(days=5),
	 "planned_progress": 70.0},
])
make_tasks(rojo, total=10, done=3, area="technical")
make_sale_order(get_partner("Cliente Retail"), rojo, hours=250)
add_timesheet(rojo, 240)

# ---------------------------------------------------------------------------
# 4. SIN PLAN: sin fecha de fin ni hitos con avance planificado
# ---------------------------------------------------------------------------
sin_plan = Project.create({
	"name": "Soporte mensual",
	"partner_id": get_partner("Cliente Retail").id,
	"user_id": users["lider"].id,
	"date_start": today - timedelta(days=15),
	"allow_billable": True,
})
make_tasks(sin_plan, total=4, done=1, area="admin")
add_timesheet(sin_plan, 18)

# Una tarea bloqueada y una esperando al cliente, para la Fase 3.
bloqueada = Task.create({
	"name": "Esperando definición del cliente", "project_id": rojo.id,
	"allocated_hours": 8.0, "area": "functional", "blocking_state": "waiting_customer",
})
Task.create({
	"name": "Bloqueada por infraestructura", "project_id": rojo.id,
	"allocated_hours": 6.0, "area": "technical", "blocking_state": "blocked",
})

Project._cron_recompute_health_state()
env.cr.commit()

print("\n=== Datos de prueba creados ===")
for project in (verde, amarillo, rojo, sin_plan):
	metrics = project._primate_health_metrics()[project.id]
	print(
		f"{project.name:<22} semaforo={project.health_state:<10} "
		f"real={metrics['progress_real']:.0f}% plan={metrics['progress_planned']:.0f}% "
		f"horas={metrics['consumed_hours']:.0f}/{metrics['sold_hours'] or 0:.0f} "
		f"plan_cargado={metrics['has_plan']}"
	)
print("\nUsuarios (contraseña = login): direccion / lider / pm / restringido")
for login in ("direccion", "lider", "pm", "restringido"):
	data = Project.with_user(users[login]).get_dashboard_data({"period": "all"})
	print(
		f"  {login:<12} proyectos={data['kpis']['active_projects']} "
		f"margen={data['config']['can_see_margin']} "
		f"horas={data['config']['can_see_timesheet_data']} "
		f"hitos={data['config']['can_see_milestones']}"
	)
