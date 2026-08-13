// Compila las plantillas OWL de un directorio fuera del navegador.
// Detecta errores de expresión (identificadores que OWL no resuelve, sintaxis inválida)
// sin necesidad de Chrome ni de un tour.
//
//   node check_templates.mjs <dir-con-xml> [ruta-a-owl.js]
//
// Sale con código 1 si alguna plantilla no compila.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import * as linkedom from "linkedom";

const { parseHTML, DOMParser } = linkedom;

const TARGET_DIR = process.argv[2];
const OWL_PATH =
	process.argv[3] ||
	process.env.OWL_PATH ||
	"/Users/darylyturraldelopez/Desktop/Odoo/shared/odoo/community-19.0/addons/web/static/lib/owl/owl.js";

if (!TARGET_DIR) {
	console.error("Uso: node check_templates.mjs <dir-con-xml> [ruta-a-owl.js]");
	process.exit(2);
}

// ---------------------------------------------------------------------------
// DOM mínimo para que owl.js cargue en Node.
// ---------------------------------------------------------------------------
const dom = parseHTML("<!doctype html><html><body></body></html>");
globalThis.window = dom.window || dom;
globalThis.document = dom.document;
globalThis.DOMParser = DOMParser;
globalThis.Element = dom.Element;
globalThis.Node = dom.Node;
globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 0);
globalThis.window.requestAnimationFrame = globalThis.requestAnimationFrame;
globalThis.window.document = globalThis.document;
globalThis.window.DOMParser = DOMParser;

for (const [key, value] of Object.entries(linkedom)) {
	if (globalThis[key] === undefined && typeof value === "function") {
		globalThis[key] = value;
		globalThis.window[key] = value;
	}
}
for (const key of ["DOMTokenList", "CSSStyleDeclaration", "DocumentFragment", "NodeList", "HTMLElement", "SVGElement"]) {
	if (globalThis[key] === undefined) {
		const stub = dom[key] || class {};
		globalThis[key] = stub;
		globalThis.window[key] = stub;
	}
}
if (!globalThis.document.implementation) {
	globalThis.document.implementation = {
		createDocument: () => new DOMParser().parseFromString("<root/>", "text/xml"),
		createHTMLDocument: () => parseHTML("<!doctype html><html><body></body></html>").document,
	};
}

// linkedom re-escapa ">" cada vez que se lee un atributo, lo que rompería las arrow
// functions de los t-on-*. Se decodifica en el punto de lectura, sobre el prototipo de
// los nodos XML, que es de donde OWL saca las plantillas.
const decodeEntities = (value) =>
	typeof value === "string"
		? value.replaceAll("&gt;", ">").replaceAll("&lt;", "<").replaceAll("&amp;", "&")
		: value;

const xmlProbe = new DOMParser().parseFromString("<t a='b'/>", "text/xml").documentElement;
const elementProto = Object.getPrototypeOf(xmlProbe);
const originalGetAttribute = elementProto.getAttribute;
elementProto.getAttribute = function (name) {
	return decodeEntities(originalGetAttribute.call(this, name));
};
const attrProto = Object.getPrototypeOf(xmlProbe.attributes[0]);
const attrValue = Object.getOwnPropertyDescriptor(attrProto, "value");
if (attrValue?.get) {
	Object.defineProperty(attrProto, "value", {
		...attrValue,
		get() {
			return decodeEntities(attrValue.get.call(this));
		},
	});
}

// ---------------------------------------------------------------------------
// Compilación
// ---------------------------------------------------------------------------
const owlModule = { exports: {} };
new Function("module", "exports", "window", "document", readFileSync(OWL_PATH, "utf8"))(
	owlModule,
	owlModule.exports,
	globalThis.window,
	globalThis.document
);
const owl = owlModule.exports.owl || globalThis.owl || globalThis.window.owl || owlModule.exports;
if (!owl?.App) {
	console.error("No se pudo cargar owl.js desde", OWL_PATH);
	process.exit(2);
}

function collectXml(dir) {
	const files = [];
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry);
		if (statSync(path).isDirectory()) {
			files.push(...collectXml(path));
		} else if (entry.endsWith(".xml")) {
			files.push(path);
		}
	}
	return files;
}

const app = new owl.App(class extends owl.Component {}, { test: true, name: "check" });
const names = [];
for (const file of collectXml(TARGET_DIR)) {
	const xml = readFileSync(file, "utf8");
	if (!xml.includes("t-name=")) {
		continue;
	}
	app.addTemplates(xml);
	for (const match of xml.matchAll(/t-name="([^"]+)"/g)) {
		names.push(match[1]);
	}
}

if (!names.length) {
	console.error("No se encontró ninguna plantilla OWL en", TARGET_DIR);
	process.exit(2);
}

let failed = false;
for (const name of names) {
	try {
		app.getTemplate(name);
		console.log("OK    ", name);
	} catch (error) {
		failed = true;
		console.log("FALLA ", name, "->", error.message);
	}
}
process.exit(failed ? 1 : 0);
