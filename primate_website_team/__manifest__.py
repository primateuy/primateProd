# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

{
    "name": "Equipo en el sitio web",
    "summary": "Publica integrantes del equipo en el sitio a partir de los empleados, con control dato por dato.",
    "version": "19.0.1.0.0",
    "category": "Website",
    "author": "PrimateUY",
    "website": "https://primate.uy",
    "license": "AGPL-3",
    "depends": [
        "hr",
        "website",
    ],
    "data": [
        "views/hr_employee_views.xml",
        "views/team_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "primate_website_team/static/src/scss/team.scss",
        ],
    },
    "installable": True,
    "application": False,
}
