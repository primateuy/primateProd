# primate_project_dashboard

Dashboard ejecutivo del portafolio de proyectos. Calcula un semáforo por proyecto con reglas objetivas —nunca marcado a mano— comparando el avance real contra el avance planificado a la fecha.

Muestra KPIs del portafolio, una tabla semáforo con barra de avance real y marcador de plan, la carga de trabajo por área y un panel de alertas accionables.

Está pensado para responder en menos de 30 segundos: qué proyectos están en problemas, por qué, y quién tiene la pelota.

## Dependencias

```python
"depends": ["project", "sale_timesheet", "hr_timesheet"]
```

Y nada más, a propósito: el módulo tiene que poder instalarse en cualquier Odoo 19 limpio, Community incluido, sin arrastrar módulos custom de Primate ni de ningún cliente. `sale_timesheet` trae por su cuenta `sale_project` y `sale`, que es de donde salen `sale_line_id` y las líneas de venta.

**Planning es opcional y se detecta en runtime** (`"planning.slot" in self.env`), nunca en el manifest. Si está instalado y el toggle de Ajustes está activo, la capacidad comprometida sale de los slots; si no, de las horas restantes de las tareas con vencimiento en la ventana.

## Puesta en marcha

1. Instalar y asignar los grupos de *Project Dashboard*:
   - **Dirección**: todo el portafolio, incluido el margen económico.
   - **Líder de área**: todo el portafolio, sin margen.
   - **Responsable de proyecto**: solo los proyectos que tiene a cargo.
2. Cargar el **plan** de cada proyecto: fecha de inicio, fecha de fin y al menos dos hitos con `deadline` y **avance planificado**. Sin eso el proyecto queda en gris ("Sin plan") y aparece en las alertas.
3. Cargar el **área** de las tareas (alimenta las tarjetas de carga) y de los empleados (es el denominador de la capacidad).
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

## Correr los tests

```bash
odoo-bin -c <conf> -d <base_limpia> -i primate_project_dashboard \
  --test-enable --test-tags=/primate_project_dashboard --stop-after-init
```

86 tests. El tour necesita `websocket-client` en el entorno y un Chrome/Chromium en las rutas estándar (o `ODOO_BROWSER_BIN` apuntando al binario); si falta alguno, Odoo lo saltea sin fallar, así que conviene mirar el log y no solo el código de salida.

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
