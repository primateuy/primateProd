# primate_project_dashboard

Dashboard ejecutivo del portafolio de proyectos. Calcula un semáforo por proyecto con reglas objetivas —nunca marcado a mano— comparando el avance real contra el avance planificado a la fecha.

Muestra KPIs del portafolio, una tabla semáforo con barra de avance real y marcador de plan, la carga de trabajo por área y un panel de alertas accionables.

Está pensado para responder en menos de 30 segundos: qué proyectos están en problemas, por qué, y quién tiene la pelota.

## Dependencias

```python
"depends": ["project", "sale_timesheet", "hr_timesheet", "primate_project_area"]
```

`primate_project_area` es la única dependencia custom, y es deliberada: define `primate.area` —el área con responsable— que este dashboard comparte con el rol Gestor de Proyectos de Sagui. Un Selection propio no podía llevar el responsable y obligaba a mantener dos definiciones del área. Fuera de eso el módulo sigue instalando en cualquier Odoo 19 limpio, Community incluido, sin arrastrar nada de ningún cliente. `sale_timesheet` trae por su cuenta `sale_project` y `sale`, que es de donde salen `sale_line_id` y las líneas de venta.

**Planning es opcional y se detecta en runtime** (`"planning.slot" in self.env`), nunca en el manifest. Si está instalado y el toggle de Ajustes está activo, la capacidad comprometida sale de los slots; si no, de las horas restantes de las tareas con vencimiento en la ventana.

## Puesta en marcha

1. Instalar y asignar los grupos de *Project Dashboard*:
   - **Dirección**: todo el portafolio, incluido el margen económico.
   - **Líder de área**: todo el portafolio, sin margen.
   - **Responsable de proyecto**: solo los proyectos que tiene a cargo.
2. Cargar el **plan** de cada proyecto: fecha de inicio, fecha de fin y al menos dos hitos con `deadline` y **avance planificado**. Sin eso el proyecto queda en gris ("Sin plan") y aparece en las alertas.
3. Cargar las **áreas** en *Proyecto → Configuración → Áreas*, con su responsable, y ponerle área a los proyectos (las tareas la heredan) y a los empleados (son el denominador de la capacidad).
4. Revisar los umbrales en *Ajustes → Proyectos*.

## Parámetros (Ajustes → Proyectos)

Los 16 parámetros viven en `ir.config_parameter` con prefijo `primate_project_dashboard.`; ninguno está hardcodeado. Los defaults están en `models/dashboard_params.py`.

| Bloque | Parámetros |
|---|---|
| **Reglas del semáforo** | Método de avance (tareas cerradas / horas consumidas). Rojo: brecha 15pp, consumo 90% con avance <70%, hito vencido hace más de 3 días. Amarillo: brecha 5pp, consumo 80% con avance <80%, hito a menos de 7 días con más de 30% de tareas abiertas |
| **Alertas** | Presupuesto de horas: aviso al 90% con avance <90%, rojo al 100% o con 25pp de brecha. Sin actividad: 7 días. Tarea bloqueada: 5 días. Etiquetas de bloqueo y de espera de cliente |
| **Capacidad** | Ventana de 10 días hábiles; usar Planning (solo visible si está instalado) |
| **Comportamiento** | Estimar el desvío recién a los 7 días de proyecto; auto-refresco y su intervalo |

## Decisiones de diseño

- **"Sin dato" nunca es cero.** Si falta un permiso o el dato no existe —proyecto sin orden de venta, sin plan cargado—, el valor viaja en `null` y la interfaz muestra `—`. El cero queda reservado para el cero real. Los KPIs excluyen de la agregación lo que no tiene dato, en vez de sumarlo como cero.
- **El semáforo evalúa primero las reglas que no dependen del plan.** Un proyecto quemando el presupuesto o con un hito vencido marca rojo aunque nadie haya cargado el cronograma. El cuarto estado `no_plan` (gris) solo aparece cuando no hay nada más que reprochar: un verde sin plan sería un falso verde. El orden completo está en el docstring de `_primate_health_state`.
- **La curva del plan siempre termina en 100%**, anclada en la fecha más tardía entre el fin del proyecto y el último hito. Los hitos son puntos intermedios de esa curva, no su techo.
- **`health_state` es un campo almacenado que depende de la fecha de hoy.** Entre corridas del cron puede quedar desactualizado frente al dashboard, que recalcula al vuelo. Es un efecto conocido, no un bug: el campo almacenado existe para poder filtrar y agrupar en las vistas estándar.
- **Un solo `sudo()` en todo el módulo**, en `_primate_employees_by_area`. El campo `hr.employee.area` sigue protegido con `groups="hr.group_hr_user"` porque el área de una persona concreta es dato de RRHH; pero el agregado de capacidad es una suma por área que no expone a nadie individualmente, y los líderes de área son su audiencia principal. Sin esa excepción verían `—` siempre. Nada por empleado viaja en el payload, y el `act_window` del click **no** usa sudo: ahí aplican las reglas normales del usuario.
- **`blocking_state` es un Selection**, así que una tarea no puede estar "bloqueada" y "esperando al cliente" a la vez. `blocked_since` se sella por cualquiera de las tres vías —campo propio, estado `04_waiting_normal` o etiqueta configurada— y se limpia al desbloquear; sin esa fecha la alerta de tarea bloqueada no se podría calcular.
- **Las alertas se calculan al vuelo**, no son registros. Cada una se identifica con una clave reproducible `tipo:modelo:id`, así que el snooze por usuario sigue aplicando aunque el mensaje cambie de "vencido hace 5 días" a "6".

## Idioma

La interfaz está íntegramente traducida al **español rioplatense** (voseo: "cargá", "tenés"), que es el registro de Uruguay. Son 126 cadenas: etiquetas de campo, valores de selección, grupos, menús, acciones, crons, mensajes de error y todo el texto del dashboard OWL.

Los términos del **área** ya no están acá: se fueron a `primate_project_area/i18n/es.po` junto con el campo. El archivo es `i18n/es.po`, uno solo y a propósito: Odoo carga las traducciones en cascada `es.po` → `es_419.po` → `es_UY.po`, así que ese archivo ya aplica a `es_UY`, `es_419`, `es_AR` y cualquier variante. Duplicarlo en un `es_UY.po` solo agregaría dos archivos que hay que mantener sincronizados.

Para que se vea en español hay que **activar el idioma en la base** (*Ajustes → Traducciones → Idiomas*, o `odoo-bin i18n loadlang -l es_UY`) y ponérselo al usuario. `docs/seed_demo.py` ya lo hace para los usuarios de prueba.

Al agregar texto nuevo: los literales de JS visibles para el usuario van siempre dentro de `_t()` —si se arman con un template literal quedan en inglés aunque el resto esté traducido— y hay que regenerar el `.po` antes de cerrar la tarea.

## Correr los tests

```bash
odoo-bin -c <conf> -d <base_limpia> --db-filter='^<base_limpia>$' \
  -i primate_project_area,primate_project_dashboard \
  --test-enable --test-tags=/primate_project_dashboard --stop-after-init
```

132 tests, incluido el tour. Tres cosas que hacen fallar la corrida por el entorno y no por el
módulo, y que en el log no se leen como lo que son:

**1. `--db-filter` es obligatorio para el tour.** `-d <base>` decide contra qué base corre el
proceso, pero las requests que hace el navegador pasan por el `dbfilter` del `.conf`. Si el conf
apunta a otra base —el caso normal de un conf de cliente— el tour abre el dashboard contra ESA
base y falla con `Failed to load registry` / `some depends are not loaded`. Parece un problema de
dependencias del módulo y no lo es.

**2. Sin `websocket-client` el tour no falla: se saltea.** No está en el `requirements.txt` de
Odoo, así que un venv recién armado no lo tiene. El log dice `skipped ... websocket-client module
is not installed` y la corrida termina en verde **sin haber corrido el tour**. Mirar el log, no
el código de salida:

```bash
pip install websocket-client
```

También hace falta un Chrome/Chromium en las rutas estándar, o `ODOO_BROWSER_BIN` apuntando al
binario. Si falta, mismo comportamiento: salteado, no fallado.

**3. Una base clonada con `createdb -T` no trae el filestore.** El clon copia la base pero no
`~/.../Odoo/filestore/<base>/`, donde viven los bundles de assets. Sin eso la página nunca
termina de cargar el JS, el tour se queda esperando `isTourReady` y muere por timeout —con
`FileNotFoundError` de filestore sueltos en el log—. Se copia a mano:

```bash
rsync -a "$FILESTORE/<base_origen>/" "$FILESTORE/<base_clon>/"
```

## Datos de prueba

```bash
odoo-bin shell -c <conf> -d <base> --no-http < docs/seed_demo.py
```

Es re-ejecutable. Arma cuatro proyectos que cubren los cuatro estados del semáforo, dispara los seis tipos de alerta y crea cuatro usuarios (contraseña = login): `direccion`, `lider`, `pm` y `restringido`, este último sin permisos de ventas ni timesheets para ver la degradación a `—`.

## Pendiente para v2

- **Curva histórica de avance** (burn-up / burn-down). La infraestructura ya está: `project.progress.snapshot` acumula una foto diaria por proyecto desde v1; falta la visualización.
- **Lazy-load del panel de alertas.** Hoy el RPC devuelve como máximo 50 alertas ordenadas por severidad y antigüedad, con un contador de las restantes. Con portafolios grandes hay que paginarlas de verdad, como ya se hace con la tabla de proyectos.
- **Notificaciones push / email** de alertas, vía cron y actividades.
- **Bloqueo múltiple** en una misma tarea, si la operativa lo necesita.

## Herramientas

`tools/owl_template_check/` (en la raíz del repo) compila las plantillas OWL fuera del navegador y detecta errores de expresión sin necesidad de Chrome. No reemplaza al tour: no valida el render.
