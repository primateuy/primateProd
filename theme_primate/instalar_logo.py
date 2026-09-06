# -*- coding: utf-8 -*-
# Instala el logo del header en el website. Uso:
#   odoo-bin shell -c <conf> -d <db> < theme_primate/instalar_logo.py
#
# Por que un script y no un dato del tema: el logo del header sale de website.logo, un campo
# binario del registro website. Los temas pueden declarar vistas, paginas, menus y attachments
# (theme.ir.*), pero no escribir un campo de website, asi que no hay forma declarativa.
# El cliente lo puede cambiar despues desde el editor sin que esto lo pise.
import base64
import os

from odoo.modules.module import get_module_path

# get_module_path y no __file__: el script se ejecuta por stdin en el shell de Odoo, donde
# __file__ no existe.
RUTA = os.path.join(get_module_path('theme_primate'),
                    'static', 'src', 'img', 'primate_logo_header.png')
website = env['website'].browse(1)
website.logo = base64.b64encode(open(RUTA, 'rb').read())
env.registry.clear_all_caches()
env.cr.commit()
print('logo instalado en el sitio %s (%s bytes)' % (website.name, os.path.getsize(RUTA)))
