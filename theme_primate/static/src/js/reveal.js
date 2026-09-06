// Scroll reveal de la home. Portado del script inline del brief al sistema de interacciones
// de Odoo 19 (@web/public/interaction).
//
// Se registra SOLO en "public.interactions" y no en "public.interactions.edit": asi no corre
// con el editor abierto y no interfiere con el website builder. El SCSS ademas fuerza los
// .reveal visibles en modo edicion, para que el copy nunca quede invisible al editarlo.
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PrimateReveal extends Interaction {
    static selector = ".o_primate_site";

    setup() {
        this.reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    start() {
        const targets = this.el.querySelectorAll(".reveal");
        // El mockup no lo hacia: si el usuario pidio menos movimiento, se muestra todo de una.
        if (this.reduceMotion) {
            targets.forEach((el) => el.classList.add("in"));
            return;
        }
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("in");
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.12 }
        );
        targets.forEach((el) => observer.observe(el));
        this.registerCleanup(() => observer.disconnect());
    }
}

registry.category("public.interactions").add("theme_primate.reveal", PrimateReveal);
