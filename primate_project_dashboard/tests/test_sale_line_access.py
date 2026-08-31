# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
"""El dashboard con acceso PARCIAL a las líneas de venta.

Bug real de producción: un usuario del dashboard que además tenía el grupo de ventas
"Usuario: Solo documentos propios" recibía «No se pudieron cargar los datos del dashboard».
Detrás había un AccessError sobre `sale.order.line`.

La causa: el código se protegía con `has_access("read")`, que mira la ACL del MODELO, y
después leía `project.sale_line_id.state` de un registro concreto. La record rule
`Personal Order Lines` niega las líneas de órdenes ajenas, así que el chequeo pasaba y la
lectura reventaba. Con otro perfil de ventas —"Todos los documentos" o administrador— el
mismo código andaba, y por eso el error parecía aleatorio entre usuarios.

Dos cosas se fijan acá:
  1. No revienta.
  2. Con visibilidad parcial el resultado es SIN DATO, no una suma de lo que se alcanza a
     ver. Un total incompleto presentado como total es peor que un guion.
"""
from odoo.exceptions import AccessError

from .common import DashboardCommon


class TestSaleLineAccess(DashboardCommon):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Vendedor "dueño" de la orden: alguien distinto de quien mira el dashboard.
		cls.otro_vendedor = cls.env["res.users"].create(
			{
				"name": "Otro Vendedor",
				"login": "otro_vendedor",
				"group_ids": [
					(6, 0, [
						cls.env.ref("base.group_user").id,
						cls.env.ref("sales_team.group_sale_salesman_all_leads").id,
					])
				],
			}
		)

	def _restringir_ventas(self, user):
		"""Le deja al usuario el perfil de ventas 'Solo documentos propios'."""
		user.write({
			"group_ids": [
				(3, self.env.ref("sales_team.group_sale_salesman_all_leads").id),
				(3, self.env.ref("sales_team.group_sale_manager").id),
				(4, self.env.ref("sales_team.group_sale_salesman").id),
			]
		})
		return user

	def _proyecto_con_orden_ajena(self):
		"""Proyecto cuya línea de venta pertenece a una orden de OTRO vendedor."""
		project = self._make_project("Con orden ajena")
		order = self._make_sale_order(project)
		order.write({"user_id": self.otro_vendedor.id})
		# La línea queda apuntada por el proyecto pero sin project_id: es el caso "huérfana",
		# que es justo el que hacía la lectura directa del registro.
		order.order_line.write({"project_id": False})
		return project, order

	# ------------------------------------------------------------------
	# 1. No revienta
	# ------------------------------------------------------------------

	def test_el_dashboard_carga_con_ventas_restringidas(self):
		"""Es el bug tal cual se veía: el dashboard no cargaba para ese usuario."""
		project, _order = self._proyecto_con_orden_ajena()
		user = self._restringir_ventas(self.manager_user)

		datos = self.env["project.project"].with_user(user).get_dashboard_data({})

		self.assertTrue(datos["projects"], "el dashboard tiene que devolver proyectos")
		ids = [row["id"] for row in datos["projects"]]
		self.assertIn(project.id, ids)

	def test_tambien_carga_para_un_lider_de_area(self):
		"""No era exclusivo de Dirección: el mismo camino corre para cualquier perfil."""
		self._proyecto_con_orden_ajena()
		user = self._restringir_ventas(self.lead_user)

		datos = self.env["project.project"].with_user(user).get_dashboard_data({})

		self.assertTrue(datos["projects"])

	def test_la_linea_ajena_no_se_lee_directo(self):
		"""La lectura directa del registro era el punto exacto donde saltaba el AccessError."""
		project, order = self._proyecto_con_orden_ajena()
		user = self._restringir_ventas(self.manager_user)

		# Se confirma que la regla efectivamente niega esa línea: si no, el test no probaría nada.
		with self.assertRaises(AccessError):
			order.order_line.with_user(user).read(["state"])

		# Y aun así el mapa de huérfanas no revienta: filtra lo que no puede leer.
		huerfanas = project.with_user(user)._primate_orphan_sale_lines()
		self.assertEqual(huerfanas, {}, "una línea ilegible no puede entrar como huérfana")

	# ------------------------------------------------------------------
	# 2. Sin dato, no un número incompleto
	# ------------------------------------------------------------------

	def test_con_visibilidad_parcial_es_sin_dato(self):
		"""Sumar solo lo visible daría un total más chico presentado como el total."""
		project, _order = self._proyecto_con_orden_ajena()
		user = self._restringir_ventas(self.manager_user)

		proyecto_usuario = project.with_user(user)
		self.assertFalse(proyecto_usuario._primate_can_read_sale_lines())
		self.assertIsNone(proyecto_usuario._primate_sold_hours_map()[project.id])
		self.assertIsNone(proyecto_usuario._primate_sold_amount_map()[project.id])

	def test_la_fila_del_dashboard_dice_sin_dato(self):
		"""Lo que llega al front: horas vendidas y margen en None, no en cero."""
		project, _order = self._proyecto_con_orden_ajena()
		user = self._restringir_ventas(self.manager_user)

		datos = self.env["project.project"].with_user(user).get_dashboard_data({})
		fila = next(row for row in datos["projects"] if row["id"] == project.id)

		self.assertIsNone(fila["sold_hours"])
		self.assertIsNone(fila["margin_estimate"])
		self.assertFalse(fila["has_sale_order"])

	# ------------------------------------------------------------------
	# 3. Que el arreglo no le saque el dato a quien SÍ puede verlo
	# ------------------------------------------------------------------

	def test_con_acceso_completo_el_dato_sigue_estando(self):
		"""La red de seguridad no puede volverse una mordaza para el usuario legítimo."""
		project, _order = self._proyecto_con_orden_ajena()

		proyecto_usuario = project.with_user(self.manager_user)
		self.assertTrue(proyecto_usuario._primate_can_read_sale_lines())
		self.assertEqual(proyecto_usuario._primate_sold_hours_map()[project.id], 100.0)

		datos = self.env["project.project"].with_user(self.manager_user).get_dashboard_data({})
		fila = next(row for row in datos["projects"] if row["id"] == project.id)
		self.assertEqual(fila["sold_hours"], 100.0)
		self.assertIsNotNone(fila["margin_estimate"])

	def test_sin_ninguna_linea_involucrada_no_hay_restriccion(self):
		"""Un proyecto sin órdenes no tiene por qué quedar marcado como 'sin dato'."""
		project = self._make_project("Sin orden")
		user = self._restringir_ventas(self.manager_user)

		self.assertTrue(project.with_user(user)._primate_can_read_sale_lines())
