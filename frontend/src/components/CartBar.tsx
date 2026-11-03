import { AnimatePresence, motion } from "motion/react";
import { Link } from "react-router";
import { formatCents } from "../lib/money";

type CartBarProps = { count: number; totalCents: number; to: string };

// Fixed bar at the bottom of the public page. It only exists when the cart has items, and it is
// the only element with shadow-md on that page. The total is only for display (the backend recomputes it).
export function CartBar({ count, totalCents, to }: CartBarProps) {
  return (
    <AnimatePresence>
      {count > 0 && (
        <motion.div
          key="cart-bar"
          initial={{ y: "120%" }}
          animate={{ y: 0 }}
          exit={{ y: "120%" }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="fixed inset-x-0 bottom-0 z-30 mx-auto max-w-[480px] px-4 pb-[max(var(--space-4),env(safe-area-inset-bottom))]"
        >
          <Link
            to={to}
            className="flex min-h-14 items-center justify-between gap-4 rounded-lg bg-accent px-4 py-3 text-[16px] font-semibold leading-6 text-on-accent no-underline shadow-md transition-tint hover:bg-accent-hover focus-ring"
          >
            <span className="flex items-center gap-3">
              <span className="inline-flex h-7 min-w-7 items-center justify-center rounded-pill bg-on-accent px-2 font-mono text-[14px] leading-5 text-accent">
                {count}
              </span>
              Ver pedido
            </span>
            <span className="font-mono tabular-nums">{formatCents(totalCents)}</span>
          </Link>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
