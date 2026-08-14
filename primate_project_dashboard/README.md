# primate_project_dashboard

Dashboard ejecutivo de proyectos para PrimateUY: semáforo calculado con reglas objetivas, avance real contra avance planificado, carga por área y alertas accionables.

Depende únicamente de `project`, `sale_timesheet` y `hr_timesheet`, así que instala en cualquier Odoo 19 limpio. El soporte de Planning para la capacidad es opcional y se detecta en runtime, nunca en el manifest.

La especificación funcional y técnica completa está en [`docs/especificacion_dashboard_proyectos.md`](docs/especificacion_dashboard_proyectos.md), y el diseño aprobado en [`docs/dashboard_proyectos_mockup.png`](docs/dashboard_proyectos_mockup.png).

## Puesta en marcha

1. Instalar el módulo y asignar los grupos de *Project Dashboard*: Dirección (ve el margen), Líder de área (todo el portafolio sin margen) y Responsable de proyecto (solo sus proyectos).
2. Cargar el plan de cada proyecto: fecha de inicio, fecha de fin y al menos dos hitos con `deadline` y **avance planificado**. Sin eso el proyecto aparece en gris ("Sin plan") y en el panel de alertas.
3. Cargar el **área** de las tareas y de los empleados. El área de la tarea alimenta las tarjetas de carga; el área del empleado es el denominador de la capacidad.
4. Ajustar los umbrales en *Ajustes → Proyectos → Executive Dashboard*.

Para probarlo con datos, `docs/seed_demo.py` arma un portafolio que cubre los cuatro estados del semáforo y dispara los seis tipos de alerta:

```bash
odoo-bin shell -c <conf> -d <base> --no-http < docs/seed_demo.py
```

## Decisiones que conviene conocer

- **"Sin dato" nunca es cero.** Si falta un permiso o el dato no existe (proyecto sin orden de venta, sin plan), el valor viaja en `null` y la interfaz muestra `—`. El cero queda reservado para el cero real.
- **El semáforo evalúa primero las reglas que no dependen del plan.** Un proyecto quemando el presupuesto marca rojo aunque nadie haya cargado el cronograma; el gris solo aparece cuando no hay nada que reprochar más que la falta de plan.
- **`health_state` es un campo almacenado que depende de la fecha de hoy**, así que entre corridas del cron puede quedar desactualizado frente a lo que muestra el dashboard, que recalcula al vuelo. Es un efecto conocido, no un bug.
- **Un solo `sudo()` en todo el módulo**, en el agregado de capacidad por área, justificado en el docstring de `_primate_employees_by_area`.

## Pendiente para v2

- **Curva histórica de avance** (burn-up / burn-down). La infraestructura ya está: `project.progress.snapshot` acumula una foto diaria por proyecto desde v1; falta la visualización.
- **Lazy-load del panel de alertas.** Hoy el RPC devuelve como máximo 50 alertas ordenadas por severidad y antigüedad, con un contador de las restantes. Con portafolios grandes hay que paginarlas de verdad, como ya se hace con la tabla de proyectos.
- **Notificaciones push / email de alertas**, vía cron y actividades.
- **`blocking_state` es un Selection**, así que una tarea no puede estar "bloqueada" y "esperando al cliente" a la vez. Si la operativa lo necesita, se revisa.

## Herramientas

`tools/owl_template_check/` (en la raíz del repo) compila las plantillas OWL fuera del navegador y detecta errores de expresión sin necesidad de Chrome.
