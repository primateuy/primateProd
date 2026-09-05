// Parallax del isologo del hero. Igual que el brief (translateY hasta 60px, solo >=981px),
// pero con dos mejoras: respeta prefers-reduced-motion y agrupa la escritura de estilo en un
// requestAnimationFrame para no forzar layout en cada evento de scroll.
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PrimateHeroParallax extends Interaction {
    static selector = ".o_primate_home .hero-monkey";

    setup() {
        this.enabled =
            window.matchMedia("(min-width: 981px)").matches &&
            !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        this.pending = false;
    }

    start() {
        if (!this.enabled) {
            return;
        }
        this.addListener(window, "scroll", () => this.onScroll(), { passive: true });
    }

    onScroll() {
        if (this.pending) {
            return;
        }
        this.pending = true;
        window.requestAnimationFrame(() => {
            this.pending = false;
            const y = Math.min(window.scrollY * 0.15, 60);
            this.el.style.transform = `translateY(${y}px)`;
        });
    }
}

registry.category("public.interactions").add("theme_primate.hero_parallax", PrimateHeroParallax);
