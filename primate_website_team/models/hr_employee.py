# -*- coding: utf-8 -*-
# Publicación de empleados en el sitio web.
#
# Criterio de privacidad (definido con el cliente): NADA se publica por defecto. Publicar al
# empleado (website_published) no expone ningún dato por sí solo; cada dato tiene su propio
# flag y todos arrancan en False.
#
# Por qué los datos NO se exponen vía hr.employee.public: darle ACL de lectura al público
# sobre ese modelo (el patrón que usa website_hr_recruitment con hr.job) habilitaría leer por
# RPC work_phone, mobile_phone y address_id de cualquier empleado publicado. En su lugar el
# controlador lee con sudo() y devuelve una whitelist explícita (ver controllers/main.py).
#
# Además: NUNCA agregar un campo *almacenado* a hr.employee.public. Ese modelo es una vista SQL
# (_auto = False) y un campo stored nuevo rompe el CREATE VIEW de hr/models/hr_employee_public.py.

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

# Redes soportadas: (campo, etiqueta, clase de icono FontAwesome del frontend).
# Fuente única de verdad: la usan el constraint de acá y el controlador.
WEBSITE_SOCIAL_FIELDS = [
    ("website_linkedin", "LinkedIn", "fa-linkedin"),
    ("website_github", "GitHub", "fa-github"),
    ("website_x", "X", "fa-twitter"),
]

# Solo http(s). Un Char que termina dentro de un href puede traer 'javascript:' y volverse XSS.
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


class HrEmployee(models.Model):
    _name = "hr.employee"
    _inherit = ["hr.employee", "website.published.mixin"]

    # --- Publicación general ---------------------------------------------------------------
    # website_published / is_published vienen del mixin, con default False.
    website_sequence = fields.Integer(
        string="Orden en el sitio", default=10,
        help="Orden de aparición en la página de Equipo. Menor primero.")

    # --- Qué se muestra (todo en False por defecto) ----------------------------------------
    website_show_photo = fields.Boolean(string="Mostrar foto", default=False, copy=False)
    website_show_role = fields.Boolean(string="Mostrar cargo público", default=False, copy=False)
    website_show_bio = fields.Boolean(string="Mostrar bio", default=False, copy=False)
    website_show_email = fields.Boolean(string="Mostrar email de contacto", default=False, copy=False)
    website_show_socials = fields.Boolean(string="Mostrar redes", default=False, copy=False)

    # --- Contenido público -----------------------------------------------------------------
    # Cargo propio del sitio: el título interno (job_title) y el público pueden diferir.
    website_role = fields.Char(
        string="Cargo público", translate=True, copy=False,
        help="Cargo tal como se muestra en el sitio. Independiente del puesto interno.")
    website_bio = fields.Text(
        string="Bio", translate=True, copy=False,
        help="Presentación breve, 1 a 3 líneas.")
    website_linkedin = fields.Char(string="LinkedIn", copy=False)
    website_github = fields.Char(string="GitHub", copy=False)
    website_x = fields.Char(string="X", copy=False)

    def _compute_website_url(self):
        super()._compute_website_url()
        for employee in self:
            if employee.is_published:
                employee.website_url = "/equipo#empleado-%s" % employee.id

    @api.constrains(*[field_name for field_name, _label, _icon in WEBSITE_SOCIAL_FIELDS])
    def _check_website_social_urls(self):
        """Rechaza URLs que no sean http(s): evita 'javascript:' y similares en el href."""
        for employee in self:
            for field_name, label, _icon in WEBSITE_SOCIAL_FIELDS:
                url = (employee[field_name] or "").strip()
                if url and not _URL_RE.match(url):
                    raise ValidationError(_(
                        "La URL de %(red)s debe empezar con http:// o https:// (recibido: %(url)s).",
                        red=label, url=url,
                    ))

    # ---------------------------------------------------------------------------------------
    # Datos para el frontend. UNICA fuente de la seccion Equipo: la consumen el controlador
    # de /equipo y la home del tema, para no duplicar la query ni la whitelist.
    # ---------------------------------------------------------------------------------------

    @api.model
    def _website_team_members(self, website=None):
        """Integrantes publicados del sitio, como lista de dicts ya blanqueados.

        Se eleva a sudo() adentro a proposito: el publico NO tiene ACL sobre hr.employee ni
        sobre hr.employee.public, asi que no puede leer el modelo por RPC. Lo unico que sale
        de aca es la whitelist de _website_team_values().

        Multi-sitio: filtra por la compania del website, para que el equipo de una no aparezca
        en el sitio de otra.
        """
        if website is None:
            website = self.env['website'].get_current_website()
        domain = [('is_published', '=', True)]
        company = website.company_id if website else self.env['res.company']
        if company:
            domain.append(('company_id', '=', company.id))
        empleados = self.sudo().search(domain, order='website_sequence, name')
        return [empleado._website_team_values() for empleado in empleados]

    def _website_team_values(self):
        """Whitelist explicita de un integrante. Cada dato sale solo si su flag esta activo."""
        self.ensure_one()
        redes = []
        if self.website_show_socials:
            for field_name, label, icon in WEBSITE_SOCIAL_FIELDS:
                url = (self[field_name] or "").strip()
                if url:
                    redes.append({"label": label, "url": url, "icon": icon})
        return {
            "id": self.id,
            "name": self.name,
            "role": self.website_role if self.website_show_role else "",
            "bio": self.website_bio if self.website_show_bio else "",
            "email": self.work_email if self.website_show_email else "",
            "photo_url": "/equipo/foto/%s" % self.id if (self.website_show_photo and self.image_512) else "",
            "socials": redes,
        }
