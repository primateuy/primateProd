# owl_template_check

Compila las plantillas OWL de un módulo fuera del navegador, para detectar errores de expresión (identificadores que OWL no resuelve contra el contexto del componente, sintaxis inválida) sin necesidad de Chrome ni de un tour.

```bash
npm install linkedom          # una sola vez, en esta carpeta
node check_templates.mjs ../../primate_project_dashboard/static/src/dashboard
```

Sale con código 1 si alguna plantilla no compila, así que sirve en un pre-commit o en CI. La ruta a `owl.js` se toma de `$OWL_PATH` o del segundo argumento; por defecto apunta a `shared/odoo/community-19.0`.

**Qué detecta y qué no.** Detecta lo que rompe en tiempo de compilación de la plantilla: por ejemplo `parseInt(...)` inline, que OWL compila como `ctx['parseInt']` y en ejecución es `undefined` (sus `RESERVED_WORDS` son `true,false,NaN,null,undefined,debugger,console,window,in,instanceof,new,function,return,eval,void,Math,RegExp,Array,Object,Date`). **No** reemplaza al tour: no valida el render, ni los props de los subcomponentes, ni el CSS. Antes de confiar en un resultado negativo, corré el chequeo contra una plantilla del core (`base_import/static/src/import_action`) para confirmar que el arnés está sano.
