import { motion, useReducedMotion } from "motion/react";
import Lottie from "lottie-react";
import { Check } from "lucide-react";
const animation = {
  v: "5.7.4",
  fr: 30,
  ip: 0,
  op: 36,
  w: 120,
  h: 120,
  nm: "Kabisa confirmation",
  ddd: 0,
  assets: [],
  layers: [
    {
      ddd: 0,
      ind: 1,
      ty: 4,
      nm: "Confirmation ring",
      sr: 1,
      ks: {
        o: { a: 0, k: 100 },
        r: { a: 0, k: 0 },
        p: { a: 0, k: [60, 60, 0] },
        a: { a: 0, k: [0, 0, 0] },
        s: {
          a: 1,
          k: [
            {
              t: 0,
              s: [60, 60, 100],
              e: [100, 100, 100],
              i: { x: [0.2], y: [1] },
              o: { x: [0.2], y: [0] },
            },
            { t: 18, s: [100, 100, 100] },
          ],
        },
      },
      ao: 0,
      shapes: [
        {
          ty: "el",
          p: { a: 0, k: [0, 0] },
          s: { a: 0, k: [94, 94] },
          nm: "Circle",
        },
        {
          ty: "st",
          c: { a: 0, k: [0.196, 0.435, 0.541, 1] },
          o: { a: 0, k: 100 },
          w: { a: 0, k: 2 },
          lc: 2,
          lj: 2,
          nm: "Stroke",
        },
      ],
      ip: 0,
      op: 36,
      st: 0,
      bm: 0,
    },
  ],
};
export default function SuccessMotion() {
  const reduced = useReducedMotion();
  return (
    <motion.div
      className="success-animation"
      initial={reduced ? false : { opacity: 0, scale: 0.94 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
    >
      {!reduced && <Lottie animationData={animation} loop={false} />}
      <Check size={38} strokeWidth={1.7} />
    </motion.div>
  );
}
