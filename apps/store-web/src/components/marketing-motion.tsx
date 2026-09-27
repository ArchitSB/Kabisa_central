import { useEffect } from "react";
export default function MarketingMotion() {
  useEffect(() => {
    if (
      matchMedia("(prefers-reduced-motion: reduce), (max-width: 767px)").matches
    )
      return;
    const connection = (
      navigator as Navigator & {
        connection?: { saveData?: boolean; effectiveType?: string };
      }
    ).connection;
    if (
      connection?.saveData ||
      navigator.hardwareConcurrency <= 4 ||
      ((navigator as Navigator & { deviceMemory?: number }).deviceMemory ??
        8) <= 4 ||
      ["slow-2g", "2g", "3g"].includes(connection?.effectiveType || "")
    )
      return;
    let cleanup = () => {};
    let cancelled = false;
    Promise.all([import("gsap"), import("lenis")])
      .then(([{ gsap }, { default: Lenis }]) => {
        if (cancelled) return;
        const lenis = new Lenis({
          duration: 0.75,
          smoothWheel: true,
          autoRaf: true,
        });
        const observer = new IntersectionObserver(
          (entries) => {
            for (const entry of entries)
              if (entry.isIntersecting) {
                gsap.fromTo(
                  entry.target,
                  { y: 14 },
                  {
                    y: 0,
                    duration: 0.55,
                    ease: "power2.out",
                    clearProps: "transform",
                  },
                );
                observer.unobserve(entry.target);
              }
          },
          { threshold: 0.15 },
        );
        document
          .querySelectorAll("[data-reveal]")
          .forEach((node) => observer.observe(node));
        cleanup = () => {
          observer.disconnect();
          lenis.destroy();
        };
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      cleanup();
    };
  }, []);
  return null;
}
