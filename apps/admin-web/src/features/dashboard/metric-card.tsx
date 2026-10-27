import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowDownRight, ArrowUpRight, Minus, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import type { DashboardMetric } from "@/features/reporting/types";

const MotionLink = motion.create(Link);

export function MetricCard({
  label,
  value,
  helper,
  metric,
  icon: Icon,
  warning,
  to,
  index,
}: {
  label: string;
  value: string;
  helper: string;
  metric: DashboardMetric;
  icon: LucideIcon;
  warning?: boolean;
  to: string;
  index: number;
}) {
  const reduced = useReducedMotion();
  const delta = metric.delta_percent;
  const DeltaIcon = delta === null ? Minus : delta >= 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <MotionLink
      to={to}
      className={`ops-metric ops-metric-action ${warning ? "ops-metric-warning" : ""}`}
      aria-label={`View ${label.toLowerCase()}: ${value}`}
      initial={reduced ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={reduced ? undefined : { y: -4, transition: { duration: 0.16, delay: 0 } }}
      whileTap={
        reduced ? undefined : { scale: 0.985, transition: { duration: 0.12, delay: 0 } }
      }
      transition={{
        duration: reduced ? 0 : 0.28,
        delay: reduced ? 0 : index * 0.045,
        ease: [0.2, 0, 0, 1],
      }}
    >
      <div className="ops-metric-heading">
        <span>{label}</span>
        <span className="ops-metric-icon">
          <Icon size={19} aria-hidden="true" />
        </span>
      </div>
      <div className="ops-metric-value">
        <AnimatePresence initial={false} mode="popLayout">
          <motion.span
            key={value}
            className="inline-block"
            initial={reduced ? false : { y: 8, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={reduced ? undefined : { y: -8, opacity: 0 }}
            transition={{ duration: reduced ? 0 : 0.22 }}
          >
            {value}
          </motion.span>
        </AnimatePresence>
      </div>
      <div className="ops-metric-footer">
        <span
          className={`ops-metric-delta ${delta !== null && delta < 0 ? "text-secondary" : ""}`}
        >
          <DeltaIcon size={13} aria-hidden="true" />
          {delta === null ? "—" : `${delta > 0 ? "+" : ""}${delta}%`}
        </span>
        <span>{metric.comparison}</span>
      </div>
      <div className="ops-metric-bottom">
        <p className="ops-metric-helper">{helper}</p>
        <span className="ops-metric-open">
          View list <ArrowUpRight size={15} aria-hidden="true" />
        </span>
      </div>
    </MotionLink>
  );
}
