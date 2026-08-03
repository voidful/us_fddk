"use client";

import { useEffect } from "react";

const REVEAL_SELECTOR = [
  "main .hero-copy",
  "main .decision-card",
  "main .truth-grid > article",
  "main .section-heading",
  "main .subsection-heading",
  "main article",
  "main .metric-table-wrap",
  "main .source-line",
  "main .faq-list details",
  "footer .footer-grid > div",
].join(",");

export default function MotionEffects() {
  useEffect(() => {
    const root = document.documentElement;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    if (reducedMotion.matches || !("IntersectionObserver" in window)) {
      root.dataset.motion = "reduced";
      return () => {
        delete root.dataset.motion;
      };
    }

    const elements = Array.from(document.querySelectorAll<HTMLElement>(REVEAL_SELECTOR));
    const viewportHeight = window.innerHeight;

    elements.forEach((element, index) => {
      element.classList.add("motion-reveal");
      element.style.setProperty("--motion-delay", `${(index % 4) * 55}ms`);

      const bounds = element.getBoundingClientRect();
      if (bounds.top < viewportHeight * 0.96 && bounds.bottom > 0) {
        element.classList.add("is-visible");
      }
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
    );

    elements.forEach((element) => {
      if (!element.classList.contains("is-visible")) observer.observe(element);
    });
    root.dataset.motion = "ready";

    return () => {
      observer.disconnect();
      elements.forEach((element) => {
        element.classList.remove("motion-reveal", "is-visible");
        element.style.removeProperty("--motion-delay");
      });
      delete root.dataset.motion;
    };
  }, []);

  return null;
}
