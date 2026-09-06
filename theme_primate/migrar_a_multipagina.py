# -*- coding: utf-8 -*-
# Migracion del sitio one-page al sitio multipagina. Uso:
#   odoo-bin shell -c <conf> -d <db> < theme_primate/migrar_a_multipagina.py
#
# Se corre UNA VEZ por base, ANTES de actualizar el tema (-u theme_primate). Es idempotente:
# si ya se corrio, no encuentra nada y no hace nada.
#
# Que saca, y por que:
#  - la home /inicio creada a mano (theme_template_id vacio). El tema ahora la declara como
#    theme.website.page; si la vieja sigue ahi, el upgrade crea una SEGUNDA pagina con la
#    misma URL, porque _update_records vincula por theme_template_id y no por url.
#  - los items de menu con ancla (/#hacemos, /#trabajamos...), del sitio one-page. Los
#    reemplazan los cinco items de data/menu.xml, que apuntan a paginas reales.
#
# El contenido no se pierde: vive en las vistas del modulo, que el upgrade vuelve a copiar.
WEBSITE_ID = 1

home = env['website.page'].search([
    ('website_id', '=', WEBSITE_ID),
    ('url', '=', '/inicio'),
    ('theme_template_id', '=', False),
])
if home:
    print('home creada a mano, se borra:', home.ids)
    home.unlink()
else:
    print('no hay home manual (ya migrada o base nueva)')

anclas = env['website.menu'].search([
    ('website_id', '=', WEBSITE_ID),
    ('url', '=like', '/#%'),
])
if anclas:
    print('menus con ancla, se borran:', [(m.id, m.url) for m in anclas])
    anclas.unlink()
else:
    print('no hay menus con ancla')

# Paginas del sitio anterior: se despublican, no se borran.
viejas = env['website.page'].search([
    ('website_id', '=', WEBSITE_ID),
    ('url', 'in', ['/soluciones', '/nosotros', '/equipo']),
    ('is_published', '=', True),
])
if viejas:
    viejas.write({'is_published': False})
    print('paginas viejas despublicadas:', [(p.id, p.url) for p in viejas])

env.registry.clear_all_caches()
env.cr.commit()
print('listo. Ahora si: -u theme_primate')
