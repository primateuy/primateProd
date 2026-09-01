# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

"""Resuelve `area_id` desde el respaldo que dejó el pre-migrate.

Este script es sólo el disparador: la lógica vive en `models/area_migration.py` para que un test
pueda probar EL MISMO código y no una copia (ver el docstring de ese módulo).
"""

from odoo import SUPERUSER_ID, api

from odoo.addons.primate_project_dashboard.models.area_migration import migrar_area_por_code


def migrate(cr, version):
	if not version:
		return
	env = api.Environment(cr, SUPERUSER_ID, {})
	migrar_area_por_code(cr, env)
