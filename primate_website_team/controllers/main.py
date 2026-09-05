# -*- coding: utf-8 -*-
# Pagina publica de Equipo.
#
# La logica de datos NO vive aca: esta en hr.employee._website_team_members(), para que la
# comparta la home del tema (theme_primate) sin duplicar la query ni la whitelist.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class PrimateWebsiteTeam(http.Controller):

    @http.route("/equipo", type="http", auth="public", website=True, sitemap=True)
    def team_page(self, **kwargs):
        members = request.env["hr.employee"]._website_team_members()
        return request.render("primate_website_team.team_page", {"members": members})

    @http.route("/equipo/foto/<int:employee_id>", type="http", auth="public", website=True,
                sitemap=False)
    def team_photo(self, employee_id, width=0, height=0, **kwargs):
        """Sirve la foto sin dar acceso publico al modelo: revalida publicacion en cada request."""
        employee = request.env["hr.employee"].sudo().browse(employee_id).exists()
        if not employee or not employee.is_published or not employee.website_show_photo:
            raise NotFound()
        stream = request.env["ir.binary"]._get_image_stream_from(
            employee, "image_512", width=int(width or 0), height=int(height or 0))
        return stream.get_response()
