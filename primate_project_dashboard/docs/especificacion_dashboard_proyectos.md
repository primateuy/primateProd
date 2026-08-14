# Dashboard general de proyectos — Especificación funcional y técnica

**Módulo:** `primate_project_dashboard`
**Versión Odoo:** 19.0 (Enterprise o Community con `project` + `sale_timesheet`)
**Fecha:** Agosto 2026
**Estado:** Implementado — este documento describe el módulo tal como quedó

> **Nota de revisión (agosto 2026).** El borrador original se ajustó durante la
> implementación. Las decisiones que cambiaron respecto de aquel documento están
> marcadas en línea con **[Cambio]** y resumidas en la sección 3.

---

## 1. Especificación funcional

### 1.1 Objetivo

Ofrecer una vista única del portafolio de proyectos de la empresa que permita, en menos de 30 segundos, responder: qué proyectos están en problemas, por qué, y quién tiene la pelota. El dashboard compara el avance real contra el avance planificado a la fecha, expone la carga de trabajo por área (Técnica, Funcional, Administrativa) y genera alertas accionables con reglas objetivas, sin depender de estados marcados manualmente por los responsables.

### 1.2 Usuarios y perfiles

| Perfil | Grupo Odoo | Acceso |
|---|---|---|
| Dirección | `group_dashboard_manager` | Todo el portafolio, todas las áreas, datos económicos |
| Líder de área | `group_dashboard_area_lead` | Todos los proyectos, sin margen económico |
| Responsable de proyecto (PM) | `group_dashboard_pm` | Solo sus proyectos asignados |

El dashboard se accede desde un menú propio dentro de Proyectos ("Dashboard ejecutivo").

### 1.3 Estructura de la pantalla

La pantalla tiene cuatro niveles, de lo agregado a lo específico:

1. **KPIs del portafolio** (fila superior de tarjetas)
2. **Estado por proyecto** (tabla semáforo)
3. **Carga por área** (tres tarjetas: Técnica, Funcional, Administrativa)
4. **Alertas** (lista de excepciones con link al registro)

Filtros globales: período (mes actual, trimestre, personalizado), área, responsable, cliente, y toggle "solo en riesgo".

### 1.4 KPIs del portafolio

| KPI | Definición / fórmula |
|---|---|
| Proyectos activos | Proyectos con `stage` no cerrada ni cancelada |
| En riesgo | Proyectos cuyo semáforo calculado = rojo |
| Cumplimiento de plan | Promedio ponderado (por horas vendidas) de `avance_real / avance_planificado`, tope 100% por proyecto |
| Desvío de horas | `(horas consumidas − horas esperadas a la fecha) / horas esperadas a la fecha` agregado del portafolio |
| Margen estimado (solo dirección) | Σ (monto vendido − horas consumidas × costo hora por empleado) |

### 1.5 Tabla de estado por proyecto

Columnas por fila:

| Columna | Origen |
|---|---|
| Proyecto + cliente | `project.project.name`, `partner_id` |
| Estado (semáforo) | Campo calculado `health_state` (ver 1.6) |
| Avance real vs plan | Barra de progreso con marcador del avance planificado a la fecha (ver 1.7) |
| Horas | `horas consumidas / horas vendidas` (timesheets vs líneas de la SO vinculada) |
| Próximo hito | Primer `project.milestone` no alcanzado, con fecha; en rojo si está vencido |
| Responsable | `user_id` (avatar) |
| Margen (solo dirección) | Calculado, oculto para otros perfiles |

Click en la fila abre el formulario del proyecto.

### 1.6 Semáforo: reglas de cálculo

El estado NUNCA se marca a mano. Se calcula con estas reglas, evaluadas en orden (la primera que aplica gana):

**Rojo (En riesgo)** si se cumple al menos una:
- Avance real < avance planificado − 15 puntos porcentuales
- Horas consumidas ≥ 90% de las vendidas con avance real < 70%
- Existe al menos un hito vencido hace más de N días (parámetro, default 3)

**Amarillo (Atención)** si se cumple al menos una:
- Avance real < avance planificado − 5 pp
- Horas consumidas ≥ 80% de las vendidas con avance real < 80%
- Hito próximo a vencer en menos de 7 días con tareas del hito abiertas > 30%

**Verde (En plan)**: solo si el proyecto tiene un plan contra el cual medirse.

**Gris (Sin plan)** — **[Cambio]** cuarto estado agregado en la implementación: el
proyecto no tiene fecha de fin ni hitos, así que no hay curva que interpolar y no se
puede evaluar ninguna regla de cronograma. Un verde sin plan sería un falso verde.

**Orden de evaluación** — **[Cambio]**, la spec original no lo definía:

1. Reglas que **no** dependen del plan (horas consumidas, hito vencido). Se evalúan
   siempre, tenga plan o no: un proyecto quemando el presupuesto marca rojo aunque
   nadie haya cargado el cronograma.
2. Reglas de brecha contra el plan, que se saltean si no hay curva.
3. Si nada aplicó: verde si hubo plan, gris si no.

El gris **no** cuenta en el KPI "En riesgo" ni en el filtro "solo en riesgo": su lugar
de presión es la alerta "proyecto sin plan cargado". Tampoco entra en el KPI de
cumplimiento de plan.

Los umbrales (15 pp, 5 pp, 90%, 80%, N días) son parámetros de configuración del módulo (`ir.config_parameter` o modelo de reglas), no constantes en código.

### 1.7 Avance planificado y avance real

- **Avance real**: promedio de avance de tareas ponderado por horas planificadas de cada tarea (`allocated_hours`). Si el proyecto no usa horas por tarea, fallback a `tareas cerradas / tareas totales`.
- **Avance planificado a la fecha**: interpolación lineal entre hitos. Cada `project.milestone` lleva un campo nuevo `planned_progress` (% acumulado esperado al alcanzarlo) y su `deadline`. El avance esperado hoy se interpola entre el último hito vencido y el próximo. Si el proyecto no tiene hitos con fechas, se interpola linealmente entre `date_start` y `date` (fecha fin) del proyecto, y el dashboard lo marca con un ícono de "plan aproximado".

**[Cambio] La curva del plan siempre termina en 100%**, anclada en la fecha más tardía
entre la fecha de fin del proyecto y el deadline del último hito. Los hitos son puntos
intermedios de la curva, no su techo: si topan en 70%, el tramo final interpola de 70% a
100% hasta esa ancla. Sin esta regla, un proyecto cuyos hitos suman 70% mostraba "70%
planificado" para siempre, que es un dato que miente.

**Requisito de datos:** todo proyecto activo debe tener fecha de inicio, fecha de fin y al menos dos hitos con fecha y `planned_progress`. El dashboard muestra en Alertas los proyectos que no cumplen este mínimo ("proyecto sin plan cargado"), tanto los que quedan en gris como los de plan aproximado.

### 1.8 Carga por área

Cada tarea lleva un campo **Área** (Técnica / Funcional / Administrativa). Por área se muestra:

- Tareas abiertas (etapas no cerradas)
- Tareas bloqueadas (`state = waiting/blocked` o etiqueta "Bloqueada") y tareas esperando al cliente (etiqueta o etapa "Espera cliente")
- Tareas vencidas (`date_deadline < hoy`)
- Capacidad ocupada: Σ horas restantes asignadas de los próximos 10 días hábiles / capacidad del equipo del área según `resource.calendar`. Si se usa el módulo Planning, se toma de ahí; si no, de `allocated_hours − effective_hours` de tareas con deadline en la ventana.

**[Cambio]** El área vive en la tarea, pero el denominador necesita personas: se agregó un
campo `area` a `hr.employee` y la capacidad disponible es el tiempo laborable de los
empleados de esa área. Un área sin empleados cargados muestra `—`, no `0%`. La tarjeta
Administrativa muestra **las mismas métricas que las otras dos**: el "facturas pendientes
de emitir" del mockup exigiría el módulo de contabilidad y rompería la independencia del
módulo.

Click en cualquier número abre la lista de tareas filtrada.

### 1.9 Catálogo de alertas

| Alerta | Regla | Severidad |
|---|---|---|
| Hito vencido | `milestone.deadline < hoy` y no alcanzado | Roja |
| Presupuesto de horas por agotarse | Consumo ≥ 90% con avance < 90% | Amarilla / roja según brecha |
| Proyecto sin actividad | Sin timesheets ni cambios de etapa en X días (default 7) | Amarilla |
| Timesheets sin cargar | Usuarios con horas planificadas y 0 timesheets en la semana | Amarilla |
| Proyecto sin plan cargado | Falta fecha fin o hitos con `planned_progress` | Amarilla |
| Tarea bloqueada hace más de X días | Default 5 días | Amarilla |

Cada alerta tiene botón de acción que abre el registro correspondiente. Las alertas se pueden descartar (snooze) por usuario con vencimiento.

### 1.10 Fuera de alcance (v1)

- Notificaciones push/email de alertas (candidato a v2, vía cron + actividades)
- Curva histórica de avance (burn-up/burn-down) — v2, requiere snapshots (ver 2.6, la infraestructura sí se deja pronta en v1)
- Proyectos internos sin SO vinculada: se muestran pero sin métricas de horas vendidas ni margen

**[Cambio] "Sin dato" nunca es cero.** Regla transversal que atraviesa todo el módulo: si
un valor no existe —proyecto sin orden de venta, sin plan cargado— o el usuario no tiene
permiso para verlo —líneas de venta, timesheets, hitos—, viaja en `null` y la interfaz
muestra `—` con un tooltip que explica cuál es el caso. El cero queda reservado para el
cero real. Los KPIs del portafolio **excluyen** de la agregación lo que no tiene dato en
vez de sumarlo como cero, para que un proyecto interno no diluya el margen ni el
cumplimiento de plan.

---

## 2. Especificación técnica

### 2.1 Módulo y dependencias

```
primate_project_dashboard/
├── __manifest__.py
├── models/
│   ├── project_project.py
│   ├── project_task.py
│   ├── project_milestone.py
│   ├── project_progress_snapshot.py
│   └── res_config_settings.py
├── controllers/          (solo si se exponen endpoints propios; default: ORM services)
├── security/
│   ├── security.xml      (3 grupos + record rules)
│   └── ir.model.access.csv
├── views/
│   ├── menu.xml
│   └── project_views.xml (campos nuevos en form de proyecto, milestone y tarea)
├── static/src/
│   ├── dashboard/        (componentes OWL)
│   │   ├── dashboard.js / .xml / .scss
│   │   ├── kpi_cards.js
│   │   ├── project_table.js
│   │   ├── area_cards.js
│   │   └── alerts_panel.js
│   └── ...
└── data/
    └── ir_cron.xml       (snapshot diario)
```

**Dependencias:** `project`, `sale_timesheet`, `hr_timesheet`. Opcional (auto-detectado en runtime, no en `depends`): `planning` para capacidad, `sale_project` según edición.

### 2.2 Extensiones de modelos

**`project.project`** — campos nuevos (todos `compute`, no almacenados salvo indicación):

| Campo | Tipo | Cálculo |
|---|---|---|
| `progress_real` | Float | Promedio ponderado por `allocated_hours` del avance de tareas |
| `progress_planned` | Float | Interpolación de hitos (ver 1.7); usa `fields.Date.context_today` |
| `health_state` | Selection `on_track/at_risk/critical/no_plan` | Reglas de 1.6, almacenado + recomputado por cron diario y por triggers (timesheets, hitos, etapas) para poder filtrar/agrupar. **[Cambio]** lleva `compute_sudo=True` explícito: el valor es global y lo ven todos, así que no puede quedar mal guardado porque quien disparó el recompute no tuviera permiso sobre las ventas |
| `sold_hours` | Float | Σ `product_uom_qty` de líneas de la SO vinculada con producto de servicio en horas |
| `consumed_hours` | Float | Σ `unit_amount` de `account.analytic.line` del proyecto |
| `margin_estimate` | Monetary | `amount_untaxed` SO − Σ (`unit_amount × employee.hourly_cost`) — visible solo para `group_dashboard_manager` (`groups=` en el campo) |
| `deviation_days` | Integer | Desvío estimado en días según brecha de avance y ritmo reciente. **[Cambio]** es una estimación gruesa y lleva guardas: no se calcula si el proyecto lleva menos días que el mínimo configurable (default 7) ni si no tiene plan, y está topeado en ±90 días. Un ritmo medido sobre pocos días proyecta desvíos absurdos |
| `next_milestone_id` | Many2one | **[Cambio]** ya existe en el core de Odoo 19, no se redefine. El dashboard calcula el próximo hito por fecha desde su propio mapa (el core ordena por secuencia antes que por fecha) y lo omite para quien no tenga `project.group_project_milestone` |
| `has_dashboard_plan`, `progress_plan_is_estimated` | Boolean | **[Cambio]** campos agregados: distinguen plan completo, plan aproximado (fechas sin hitos) y sin plan, que es lo que alimenta el gris, el ícono de la fila y la alerta |

**`project.task`:**

| Campo | Tipo | Notas |
|---|---|---|
| `area` | Selection: `technical / functional / admin` | Requerido en proyectos facturables (aviso por `onchange`, no bloqueo, para no trabar la operativa) |
| `blocking_state` | Selection: `blocked / waiting_customer` | **[Cambio]** el estado `blocked` que asumía la spec no existe en Odoo 19. Una tarea cuenta como bloqueada por este campo, por el estado `04_waiting_normal` **o** por una etiqueta configurada |
| `blocked_since` | Datetime | **[Cambio]** se sella automáticamente al bloquearse por cualquiera de las tres vías y se limpia al desbloquear. Sin esta fecha, la alerta "tarea bloqueada hace más de X días" no se puede calcular |

Se agrega el campo al form y a los filtros/agrupadores de la vista de tareas para poder pivotear también fuera del dashboard.

**`project.milestone`:**

| Campo | Tipo | Notas |
|---|---|---|
| `planned_progress` | Float (0–100) | % acumulado esperado del proyecto al alcanzar este hito. `constrains`: monótono creciente por fecha dentro del proyecto |

**`project.progress.snapshot`** (modelo nuevo, para histórico y futura curva burn-up):

| Campo | Tipo |
|---|---|
| `project_id` | Many2one |
| `date` | Date |
| `progress_real`, `progress_planned`, `consumed_hours`, `health_state` | Float / Selection |

Poblado por cron diario (`ir.cron`, 06:00). En v1 solo se acumula; la visualización llega en v2.

### 2.3 Frontend (OWL)

- **Client action** registrada en `web` (`tag: primate_project_dashboard`), menú bajo Proyectos.
- Componentes OWL 2 puros, sin depender de las vistas dashboard estándar. Carga de datos vía `orm.readGroup` / `orm.searchRead` y un método `get_dashboard_data()` en `project.project` (un solo RPC que devuelve KPIs + filas + áreas + alertas, para evitar N llamadas).
- Estado de filtros en el hash de la URL para poder compartir vistas filtradas.
- Semáforos y barras con SCSS propio usando variables de color estándar de Odoo (`$o-success`, `$o-warning`, `$o-danger`) para respetar theming.
- Auto-refresh opcional cada 5 minutos (configurable), pensado para pantalla de oficina.

### 2.4 Performance

- `health_state` almacenado con recompute dirigido (`@api.depends` sobre timesheets agregados vía campo puente, y triggers en write de milestone/stage) + cron de respaldo diario.
- `get_dashboard_data()` usa `read_group` sobre `account.analytic.line` y `project.task` (nunca iterar registros en Python para sumar horas).
- Con más de ~50 proyectos activos, paginación de la tabla y lazy-load del panel de alertas.

### 2.5 Seguridad

- Record rule para `group_dashboard_pm`: `[('user_id','=',user.id)]` sobre la lectura del dashboard (no sobre `project.project` global, para no interferir con la operativa existente — se filtra en `get_dashboard_data`).
- `margin_estimate` y KPI de margen con `groups="primate_project_dashboard.group_dashboard_manager"` a nivel de campo y de componente.
- Sin `sudo()` en los cálculos: cada usuario ve lo que sus reglas permiten.
- **[Cambio] Una única excepción documentada**: el agregado de capacidad por área
  (`_primate_employees_by_area`) lee `hr.employee.area` con `sudo()`. El campo sigue
  protegido con `groups="hr.group_hr_user"` a nivel de registro, pero el resultado es una
  suma por área que no expone a ningún empleado individual, y los líderes de área son la
  audiencia principal de esas tarjetas: sin la excepción verían `—` siempre. Nada por
  empleado viaja en el payload y el `act_window` del click no usa sudo.

### 2.6 Configuración (Ajustes → Proyectos)

**[Cambio]** Terminaron siendo **16 parámetros**, no 5: las reglas del semáforo mencionan
también los topes de avance (70% y 80%), la ventana del hito próximo y el ratio de tareas
abiertas, y la alerta de presupuesto necesita sus propios cortes de amarillo y rojo. Todos
en `ir.config_parameter` con prefijo `primate_project_dashboard.`, agrupados en la vista en
cuatro bloques (semáforo, alertas, capacidad, comportamiento) para que no sean una pared de
inputs. Los defaults viven en `models/dashboard_params.py`.

- Umbrales del semáforo (7 valores, ver 1.6)
- Umbrales de la alerta de presupuesto de horas (4 valores)
- Días mínimos de proyecto para estimar el desvío
- Días para "sin actividad" y "bloqueada hace X días"
- Ventana de capacidad (default 10 días hábiles)
- Toggle auto-refresh y su intervalo
- Toggle "usar Planning para capacidad" (visible solo si el módulo está instalado)

### 2.7 Plan de trabajo sugerido

| Fase | Contenido | Estimación |
|---|---|---|
| 1 | Modelos, campos calculados, semáforo, seguridad, snapshot + cron | 3–4 días |
| 2 | Client action OWL: KPIs + tabla de proyectos con filtros | 4–5 días |
| 3 | Carga por área + alertas + configuración | 3–4 días |
| 4 | Carga de datos reales (áreas en tareas, hitos con %), ajuste de umbrales con dirección, QA | 2–3 días |

**Total estimado: 12–16 días** de desarrollo, más el trabajo operativo de disciplina de carga (áreas y planes por proyecto), que es condición necesaria para que el dashboard diga la verdad.

### 2.8 Riesgos y supuestos

- **El dato manda:** si los timesheets no se cargan al día o los hitos no tienen fechas reales, el dashboard va a mostrar rojo por falta de datos, no por problemas reales. La alerta "proyecto sin plan cargado" existe justamente para forzar esa disciplina las primeras semanas.
- Se asume relación 1 proyecto ↔ 1 SO principal. Si hay proyectos con múltiples SO (upsells), `sold_hours` suma todas las SO vinculadas al proyecto vía `project_id` en las líneas.
- La interpolación lineal entre hitos es una aproximación deliberadamente simple; si más adelante se quiere curva S o pesos por fase, el modelo de snapshot ya deja los datos prontos.


---

## 3. Resumen de cambios respecto del borrador

| # | Cambio | Por qué |
|---|---|---|
| 1 | Cuarto estado `no_plan` (gris) y orden de evaluación explícito | Un verde sin plan es un falso verde; pero el gris no puede esconder un rojo real |
| 2 | La curva del plan siempre termina en 100% | Hitos que topan en 70% dejaban el plan mintiendo para siempre |
| 3 | "Sin dato" nunca es cero, en toda la interfaz y en los KPIs | Un proyecto interno mostraba "18 / 0 horas" y un margen negativo que era solo costo |
| 4 | `blocking_state` + `blocked_since` en la tarea | El estado `blocked` que asumía la spec no existe en Odoo 19, y sin fecha no hay alerta de bloqueo |
| 5 | 16 parámetros configurables en cuatro bloques | Las reglas usaban más umbrales de los 5 que la spec listaba |
| 6 | Campo `area` en `hr.employee` + sudo de agregación acotado | El área vive en la tarea, pero la capacidad necesita personas |
| 7 | `next_milestone_id` se reusa del core | Ya existe en Odoo 19 con la misma semántica |
| 8 | Guardas en `deviation_days` | Un ritmo medido sobre pocos días proyecta desvíos absurdos |
| 9 | Sin "facturas pendientes de emitir" en la tarjeta Administrativa | Exigiría el módulo de contabilidad y rompería la independencia |
| 10 | Estado de filtros en el query string, no en el hash | Odoo 19 abandonó el hash en las URLs `/odoo/` |
| 11 | El período filtra proyectos; las métricas son siempre al día de hoy | Es lo que significan avance, horas y semáforo. El selector lo aclara en un tooltip |
| 12 | Paginación server-side de 30 filas | Sección 2.4; los KPIs y las áreas siguen agregando sobre el total |
