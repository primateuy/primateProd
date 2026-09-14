# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDashboardViewPreference(TransactionCase):
	"""La vista del dashboard es una preferencia por usuario que llega con la sesión."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.user_a = new_test_user(cls.env, login="ppd_view_a", groups="base.group_user")
		cls.user_b = new_test_user(cls.env, login="ppd_view_b", groups="base.group_user")

	def _settings(self, user):
		# _find_or_create_for_user devuelve el registro en sudo: se baja al usuario.
		return self.env["res.users.settings"]._find_or_create_for_user(user).with_user(user)

	def test_por_defecto_es_la_clasica(self):
		self.assertEqual(self._settings(self.user_a).primate_dashboard_view, "classic")

	def test_viaja_en_el_formato_de_la_sesion(self):
		"""Es la misma llamada con la que web arma user_settings en session_info."""
		formatted = self._settings(self.user_a)._res_users_settings_format()
		self.assertEqual(formatted.get("primate_dashboard_view"), "classic")

	def test_cada_usuario_guarda_la_suya(self):
		self._settings(self.user_a).set_res_users_settings({"primate_dashboard_view": "modern"})
		self.assertEqual(self._settings(self.user_a).primate_dashboard_view, "modern")
		self.assertEqual(self._settings(self.user_b).primate_dashboard_view, "classic")

	def test_no_se_puede_cambiar_la_de_otro_usuario(self):
		settings_b = self._settings(self.user_b)
		with self.assertRaises(AccessError):
			settings_b.with_user(self.user_a).set_res_users_settings({"primate_dashboard_view": "modern"})
