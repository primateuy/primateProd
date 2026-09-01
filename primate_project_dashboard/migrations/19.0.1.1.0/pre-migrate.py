# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

"""Respalda el Selection `area` antes de que el campo deje de existir.

Odoo NO borra la columna de un campo que se quita del código -sólo deja de conocerla-, pero
apoyarse en eso es frágil: alcanza con que alguien desinstale y reinstale para perder el dato.
Se copia a una tabla propia, que además es lo que hace testeable la migración: el post-migrate
lee de acá y el test siembra acá.

La tabla NO se borra al terminar. Una vez que la columna vieja se va, es el único registro de
qué área tenía cada tarea antes, y es lo que permite auditar la migración meses después.
"""

import logging

from odoo.addons.primate_project_dashboard.models.area_migration import TABLA_RESPALDO, TABLAS

_logger = logging.getLogger(__name__)


def _tiene_columna(cr, tabla, columna):
	cr.execute(
		"""
		SELECT 1 FROM information_schema.columns
		 WHERE table_name = %s AND column_name = %s
		""",
		(tabla, columna),
	)
	return bool(cr.fetchone())


def migrate(cr, version):
	if not version:
		return

	cr.execute(
		"""
		CREATE TABLE IF NOT EXISTS {} (
			modelo VARCHAR NOT NULL,
			res_id INTEGER NOT NULL,
			code VARCHAR NOT NULL
		)
		""".format(TABLA_RESPALDO)
	)
	# Idempotente: si el pre-migrate ya corrió, no se duplican filas.
	cr.execute("DELETE FROM {}".format(TABLA_RESPALDO))

	total = 0
	for modelo, tabla in TABLAS.items():
		if not _tiene_columna(cr, tabla, "area"):
			_logger.info(
				"primate_project_dashboard: %s no tiene columna `area`; nada que respaldar.", tabla
			)
			continue
		cr.execute(
			"""
			INSERT INTO {respaldo} (modelo, res_id, code)
			SELECT %s, id, area FROM {tabla} WHERE area IS NOT NULL
			""".format(respaldo=TABLA_RESPALDO, tabla=tabla),
			(modelo,),
		)
		total += cr.rowcount
		_logger.info(
			"primate_project_dashboard: respaldadas %s filas de %s.", cr.rowcount, tabla
		)
	_logger.info(
		"primate_project_dashboard: %s filas en %s, listas para el post-migrate.",
		total,
		TABLA_RESPALDO,
	)
