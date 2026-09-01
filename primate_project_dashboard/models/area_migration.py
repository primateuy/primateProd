# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

"""Migración del área: del Selection de este módulo a `primate.area` (primate_project_area).

POR QUÉ ESTO NO VIVE EN `migrations/`
-------------------------------------
Un script de `migrations/` no es importable: no forma parte del paquete Python del addon. Un test
sólo podría probar una COPIA de la lógica, y una copia que se desincroniza del original es peor
que no tener test. Así que el mapeo vive acá, el `post-migrate` lo llama con la base real y
`tests/test_area_migration.py` lo llama con datos sembrados. Se prueba el mismo código.

DECISIONES DE DATOS (aceptadas, no defaults técnicos)
-----------------------------------------------------
Esto contesta la pregunta "¿por qué este proyecto quedó sin área?":

* El área de un PROYECTO es la MAYORÍA de las áreas de sus tareas.
* EMPATE o proyecto SIN TAREAS → área vacía. No se desempata inventando.
* CODE DESCONOCIDO (un valor viejo de una base donde alguien extendió el Selection) → área
  vacía + WARNING en el log CON LOS IDS. Nunca se mapea al azar y nunca corta la migración.
* Vacío es un dato legítimo: es exactamente el hallazgo de la regla "proyecto sin área" del rol
  Gestor de Proyectos, que lo va a proponer con nombre y apellido.

Las escrituras van por SQL directo a propósito: el `write()` de `project.task` re-hereda el área
al mover de proyecto y `tracking=True` postaría un mensaje por tarea. En una migración eso es
ruido y minutos, no seguridad.
"""

import logging

_logger = logging.getLogger(__name__)

TABLA_RESPALDO = "primate_area_migracion"

# Modelo Odoo -> tabla, para los dos que llevaban el Selection.
TABLAS = {
	"project.task": "project_task",
	"hr.employee": "hr_employee",
}


def _areas_por_code(env):
	"""{code: id} de TODAS las áreas, archivadas incluidas: una tarea vieja puede apuntar a un
	área que hoy está fuera de circulación, y perder ese dato sería peor que conservarlo."""
	areas = env["primate.area"].with_context(active_test=False).search([])
	return {area.code: area.id for area in areas}


def _leer_respaldo(cr, tabla_respaldo):
	"""{modelo: {code: [res_id, ...]}} desde la tabla que dejó el pre-migrate."""
	cr.execute(
		"SELECT modelo, code, res_id FROM {} ORDER BY modelo, code, res_id".format(tabla_respaldo)
	)
	respaldo = {}
	for modelo, code, res_id in cr.fetchall():
		respaldo.setdefault(modelo, {}).setdefault(code, []).append(res_id)
	return respaldo


def _migrar_modelo(cr, modelo, por_code, areas, reporte):
	tabla = TABLAS[modelo]
	for code, ids in por_code.items():
		area_id = areas.get(code)
		if not area_id:
			# No se pierde en silencio: queda el code, la cantidad y los ids concretos.
			reporte["codes_desconocidos"].setdefault(code, []).extend(ids)
			_logger.warning(
				"primate_project_dashboard: el área «%s» no existe como primate.area; "
				"%s registros de %s quedan sin área. Ids: %s",
				code,
				len(ids),
				modelo,
				ids,
			)
			continue
		cr.execute(
			"UPDATE {} SET area_id = %s WHERE id IN %s".format(tabla),
			(area_id, tuple(ids)),
		)
		reporte[modelo] = reporte.get(modelo, 0) + cr.rowcount


def _area_por_mayoria(cr):
	"""{project_id: area_id} por mayoría de sus tareas. Empate -> no entra en el dict."""
	cr.execute(
		"""
		SELECT project_id, area_id, COUNT(*)
		  FROM project_task
		 WHERE project_id IS NOT NULL AND area_id IS NOT NULL
		 GROUP BY project_id, area_id
		"""
	)
	conteos = {}
	for project_id, area_id, cantidad in cr.fetchall():
		conteos.setdefault(project_id, []).append((cantidad, area_id))

	ganadores = {}
	for project_id, filas in conteos.items():
		tope = max(cantidad for cantidad, _area_id in filas)
		empatadas = [area_id for cantidad, area_id in filas if cantidad == tope]
		if len(empatadas) == 1:
			ganadores[project_id] = empatadas[0]
		else:
			_logger.info(
				"primate_project_dashboard: el proyecto %s empata entre %s áreas; queda sin área.",
				project_id,
				len(empatadas),
			)
	return ganadores


def migrar_area_por_code(cr, env, tabla_respaldo=TABLA_RESPALDO):
	"""Resuelve `area_id` desde el respaldo del Selection. Devuelve el reporte de la corrida.

	El reporte CIERRA POR CONTEO: `respaldo_total == mapeados + desconocidos`. Si no cierra,
	algo se perdió por el camino y hay que mirarlo, no seguir.
	"""
	reporte = {
		"project.task": 0,
		"hr.employee": 0,
		"project.project": 0,
		"codes_desconocidos": {},
		"respaldo_total": 0,
	}
	# Esto escribe por SQL y el ORM no lo sabe: si quedan escrituras pendientes en la caché, se
	# vuelcan DESPUÉS y pisan lo recién migrado. En el post-migrate el env viene limpio, pero un
	# test -o cualquier otro llamador- puede tener writes sin volcar. Se vacía antes de tocar SQL.
	env.flush_all()
	areas = _areas_por_code(env)
	if not areas:
		_logger.error(
			"primate_project_dashboard: no hay ninguna primate.area cargada; la migración del "
			"área no puede resolver nada. ¿Se instaló primate_project_area?"
		)
		return reporte

	respaldo = _leer_respaldo(cr, tabla_respaldo)
	for modelo, por_code in respaldo.items():
		if modelo not in TABLAS:
			_logger.warning("primate_project_dashboard: respaldo de un modelo inesperado: %s", modelo)
			continue
		reporte["respaldo_total"] += sum(len(ids) for ids in por_code.values())
		_migrar_modelo(cr, modelo, por_code, areas, reporte)

	# El área del proyecto se calcula DESPUÉS de las tareas: sale de ellas.
	# Sólo se completan los proyectos que no tienen área: uno ya cargado a mano manda.
	ganadores = _area_por_mayoria(cr)
	for project_id, area_id in ganadores.items():
		cr.execute(
			"UPDATE project_project SET area_id = %s WHERE id = %s AND area_id IS NULL",
			(area_id, project_id),
		)
		reporte["project.project"] += cr.rowcount

	desconocidos = sum(len(ids) for ids in reporte["codes_desconocidos"].values())
	mapeados = reporte["project.task"] + reporte["hr.employee"]
	reporte["mapeados"] = mapeados
	reporte["desconocidos"] = desconocidos
	reporte["cierra"] = reporte["respaldo_total"] == mapeados + desconocidos
	if not reporte["cierra"]:
		_logger.error(
			"primate_project_dashboard: la migración del área NO cierra por conteo: respaldo=%s, "
			"mapeados=%s, desconocidos=%s. Revisar antes de dar la migración por buena.",
			reporte["respaldo_total"],
			mapeados,
			desconocidos,
		)
	else:
		_logger.info(
			"primate_project_dashboard: área migrada. Tareas=%s, empleados=%s, proyectos=%s, "
			"codes desconocidos=%s.",
			reporte["project.task"],
			reporte["hr.employee"],
			reporte["project.project"],
			sorted(reporte["codes_desconocidos"]),
		)
	return reporte
