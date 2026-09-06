# -*- coding: utf-8 -*-
# Desactiva el footer que dejo el generador viejo en el sitio 1. Uso:
#   odoo-bin shell -c <conf> -d <db> < theme_primate/desactivar_footer_viejo.py
#
# Es una vista ESPECIFICA del sitio (key website.footer_custom, website_id=1) creada por
# primate_website_generator: decia "B2B Service", mezclaba portugues y enlazaba a las anclas
# del sitio one-page. Se desactiva en vez de borrarse, para poder volver atras.
# website.footer_copyright_company_name: la misma herencia hardcodeaba "(c) 2026 B2B Service",
# con el anio fijo. Desactivada, vuelve el copyright nativo, que toma el nombre de la compania
# y el anio en curso solo.
CLAVES = ['website.footer_custom', 'website.footer_copyright_company_name']

vistas = env['ir.ui.view'].search([
    ('key', 'in', CLAVES),
    ('website_id', '=', 1),
    ('active', '=', True),
])
if not vistas:
    print('no hay vistas viejas activas en el sitio 1')
else:
    vistas.write({'active': False})
    env.registry.clear_all_caches()
    env.cr.commit()
    print('desactivadas:', [(v.id, v.key) for v in vistas])
