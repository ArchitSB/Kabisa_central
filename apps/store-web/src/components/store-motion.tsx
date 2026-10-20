import { type ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";

/** Short, interruptible transitions; reduced-motion users see the final state immediately. */
export function PageMotion({ children }: { children: ReactNode }) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      className="store-page-motion"
      initial={reduced ? false : { opacity: 0.75, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduced ? 0 : 0.24, ease: [0.2, 0, 0, 1] }}
    >
      {children}
    </motion.div>
  );
}

export function Reveal({
  children,
  className,
  delay = 0,
  as = "div",
  id,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  as?: "div" | "section";
  id?: string;
}) {
  const reduced = useReducedMotion();
  const Element = as === "section" ? motion.section : motion.div;
  return (
    <Element
      id={id}
      className={className}
      initial={reduced ? false : { opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.08 }}
      transition={{
        duration: reduced ? 0 : 0.4,
        delay: reduced ? 0 : Math.min(delay, 0.15),
        ease: [0.2, 0, 0, 1],
      }}
    >
      {children}
    </Element>
  );
}

export function CartCount({ value }: { value: number }) {
  const reduced = useReducedMotion();
  return (
    <motion.span
      className="cart-count"
      key={value}
      initial={false}
      animate={reduced ? { scale: 1 } : { scale: [1, 1.25, 1] }}
      transition={{ duration: reduced ? 0 : 0.3, ease: [0.2, 0, 0, 1] }}
    >
      {value}
    </motion.span>
  );
}
