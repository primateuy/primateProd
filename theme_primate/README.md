# Theme Primate

Identidad de marca Primate (rebranding **Design Pipa 2026**, variante oscura) y home del sitio,
portadas del mockup `primate-web-redesign-brief-moderno.html`.

## Páginas

El sitio es multipágina: cada ítem del menú es una URL propia, no un ancla.

| Menú | URL | Vista | Contenido |
|---|---|---|---|
| Home | `/` → `/inicio` | `theme_primate.home` | hero, problema, tres monos, qué hacemos, cómo trabajamos, independencia, teaser de casos, CTA |
| Sobre nosotros | `/sobre-nosotros` | `theme_primate.page_about` | sobre Primate, equipo, CTA |
| Casos de éxito | `/casos-de-exito` | `theme_primate.page_cases` | grid completo de casos, CTA |
| Agendar una reunión | `/agendar-reunion` | `theme_primate.page_booking` | antesala de marca + bloque nativo de Appointments |
| Contáctenos | `/contactus` | nativa de Odoo | formulario `website_form` |

Las páginas y el menú se declaran como `theme.website.page` y `theme.website.menu`
(`data/pages.xml`, `data/menu.xml`): al instalar o actualizar el tema, Odoo los copia a
`website.page` / `website.menu` de cada sitio que lo use. La estructura es reproducible en
cualquier base, sin crear páginas a mano.

## Qué se edita desde el website builder

Todo el copy. Cada página tiene su contenido dentro de zonas `oe_structure`, así que desde el
editor se puede editar cualquier texto in-place, y mover, duplicar o borrar cada bloque.

| Página | Zona | Qué contiene |
|---|---|---|
| Home | `oe_structure_primate_home` | todo el cuerpo |
| Sobre nosotros | `oe_structure_primate_about_top` | sobre Primate |
| Sobre nosotros | **fija** | **Equipo** (dinámica, ver abajo) |
| Sobre nosotros | `oe_structure_primate_about_bottom` | CTA final |
| Casos de éxito | `oe_structure_primate_cases` | casos y CTA |
| Agendar | `oe_structure_primate_booking` | copy y bloque de reserva |

**Por qué los ids llevan el prefijo `oe_structure_`:** con ese prefijo
(`html_editor/models/ir_ui_view.py:55`) Odoo guarda lo editado en una **vista hija heredada**,
en vez de escribirlo dentro del arch del módulo. Así el tema se sigue actualizando por código
sin pisar lo que editó el cliente.

Los atributos `data-oe-model` / `data-oe-field` / `data-oe-xpath` **no se escriben a mano**: los
inyecta el renderer en modo edición (`ir_ui_view.distribute_branding`).

No editables como texto libre, por diseño: los datos de los empleados (vienen del modelo). Los
números de ejemplo (40+, 6 países, etc.) sí son texto plano y se editan como cualquier otro.

## Bloques en el panel del builder

Los bloques de marca se registran en el panel bajo un grupo propio **Primate**
(`views/snippets/snippets.xml`, heredando `website.snippets`). El markup vive inline en la
página —ese es el contenido inicial— y además como template `s_primate_*`, que es lo que usa el
panel al insertarlo de nuevo o en otra página.

## Agendar una reunión

El calendario no es una `website.page`: lo sirve el controlador de `appointment`
(`/appointment/<id>`). La página es la antesala de marca y el salto lo hace el botón nativo
`.s_online_appointment`. Va con `data-appointment-types="[]"`, o sea al listado de tipos
publicados; cuando exista el tipo definitivo se lo apunta **desde el editor** (opción nativa del
bloque) y esa elección queda en la vista hija, sin tocar el módulo. Hardcodear el id del tipo en
el XML lo rompería en cualquier otra base.

## Cómo quedó conectada la sección Equipo

Reusa `primate_website_team` sin duplicar nada:

```
hr.employee._website_team_members()      <- única fuente de datos (modelo)
        │
        ├── controllers/main.py de primate_website_team  -> página /equipo
        └── theme_primate/views/home.xml                 -> sección Equipo de la home
```

En la home:

```xml
<t t-set="members" t-value="env['hr.employee']._website_team_members()"/>
<t t-call="primate_website_team.team_grid"/>
```

Ese es el mismo idiom que usa el core de Odoo (`t-value="env['res.lang']._get_data(...)"`).

**Por qué la sección es fija y no un snippet arrastrable:** un snippet guarda el DOM renderizado
al soltarlo, así que la lista de empleados quedaría congelada en ese momento. Como sección con
`t-call`, se recalcula en cada request. El título y la bajada de la sección sí se editan
in-place, porque están fuera del `t-call`.

**Estilo:** los overrides de la grilla están namespaceados bajo `.o_primate_home` (tarjeta
oscura, glow turquesa en hover, Montserrat). La página `/equipo` conserva su estilo propio: no
se toca `.pwt_*` fuera del wrapper de la home.

## Paleta y tipografía

Paleta por rol en `static/src/scss/primary_variables.scss`, que alimenta los combos de Odoo:

| Combo | Color | Rol |
|---|---|---|
| `o_cc1` | `#150C24` | fondo de página |
| `o_cc2` | `#1D1332` | superficie |
| `o_cc3` | `#241740` | tarjeta |
| `o_cc4` | `#56AEA0` | acento |
| `o_cc5` | `#2C1D4D` | banda |

El turquesa es el **`#56AEA0` del manual de marca**, no el `#5FC2B2` del mockup: da 7,2:1 sobre
`#150C24`, así que no hace falta desviarse del manual. `#8CE9D8` queda solo para glows y hovers.

Los botones primarios llevan texto violeta oscuro (5,7:1). Nunca blanco: el turquesa da 2,6:1
contra blanco y falla WCAG AA.

Tipografía Montserrat (400–800), cargada por el mecanismo de fuentes del tema.

## Header y footer

El mockup los dibuja con markup propio. Acá **no se duplican**: se estilan los selectores reales
de `website.layout` (`#top .navbar` como pill flotante, `.top_menu .nav-link`, `footer.o_footer`)
en `static/src/scss/header_footer.scss`. Duplicar el nav en el cuerpo fue justamente el bug que
tenía el sitio anterior: dos menús en pantalla.

El logo del header sigue siendo `website.logo` de Odoo, sin tocar. Las marcas del contenido
(hero, nosotros, footer) sí salen de `static/src/img/`, generadas desde los originales de
4500 px de la carpeta de marca y recoloreadas sobre el canal alpha.

## JS

Sistema de interacciones de Odoo 19 (`@web/public/interaction`), registrado **solo** en
`public.interactions` y no en `public.interactions.edit`: no corre con el editor abierto, así que
no interfiere con el builder.

- `reveal.js` — scroll reveal con `IntersectionObserver`.
- `hero_parallax.js` — parallax del isologo, solo ≥981px, agrupado en `requestAnimationFrame`.

El marquee es CSS puro (`@keyframes pw-marquee`, renombrado desde `scroll` del mockup para no
colisionar dentro de Odoo).

## prefers-reduced-motion

El mockup solo frenaba el marquee. Acá se frenan los tres: el marquee, el reveal (todo visible de
entrada) y el parallax (no se engancha al scroll).

## Responsive

Se mantiene el breakpoint del mockup en 980px.

## Revertir

`website.primate_prev_homepage_url` guarda la home anterior (`/b2b-service-2`). El cuerpo del
diseño previo está en `respaldos/website1_landing_html_prebrief_*.html` en la raíz del proyecto.
