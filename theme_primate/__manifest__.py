# Copyright 2026 - PrimateUY
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

{
    "name": "Theme Primate",
    "description": "Identidad de marca Primate (rebranding Design Pipa 2026, variante oscura): "
                   "paleta, tipografía, home y estilo del sitio.",
    "category": "Theme",
    "version": "19.0.2.0.0",
    "author": "PrimateUY",
    "website": "https://primate.uy",
    "license": "AGPL-3",
    # primate_website_team: la home hace t-call a su template team_grid y llama a
    # hr.employee._website_team_members(). Sin esa dependencia la sección Equipo no renderiza.
    "depends": [
        "website",
        "primate_website_team",
    ],
    # La paleta y las fuentes se registran por ir.asset con directive="append" sobre
    # web._assets_primary_variables, para cargar DESPUÉS de website (donde se definen
    # $o-color-palettes y o-make-palette). Es el mismo patrón de los temas que shippea Odoo
    # (design-themes-19.0/theme_graphene/data/ir_asset.xml). Nunca prepend: rompe la
    # compilación con "undefined variable".
    "data": [
        "data/ir_asset.xml",
        # Los snippets se declaran ANTES que las paginas: la pagina inlinea el markup, pero
        # el registro en el panel debe existir para que el builder reconozca las instancias.
        "views/snippets/s_primate_hero.xml",
        "views/snippets/snippets.xml",
        # Paginas: las vistas primero, porque data/pages.xml las referencia por ref().
        "views/home.xml",
        "views/pages/page_about.xml",
        "views/pages/page_cases.xml",
        "views/pages/page_booking.xml",
        "data/pages.xml",
        "data/menu.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            # Orden importante: los tokens primero, después quien los consume.
            "theme_primate/static/src/scss/tokens.scss",
            "theme_primate/static/src/scss/theme.scss",
            "theme_primate/static/src/scss/header_footer.scss",
            "theme_primate/static/src/scss/sections.scss",
            "theme_primate/static/src/js/reveal.js",
            "theme_primate/static/src/js/hero_parallax.js",
        ],
    },
    "installable": True,
}
