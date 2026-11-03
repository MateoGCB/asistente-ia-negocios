import type { OrderStatus } from "../api/types";
import { STATUS_LABEL } from "../lib/orderStatus";
import { cn } from "../lib/cn";

// Status colors exist ONLY for these six states. The word is always shown: color alone is not
// enough to tell "Listo" from "Cancelado" (color blindness).
const STYLE: Record<OrderStatus, { badge: string; dot: string }> = {
  pending: { badge: "bg-status-pending-bg text-status-pending-fg", dot: "bg-status-pending-dot" },
  confirmed: { badge: "bg-status-confirmed-bg text-status-confirmed-fg", dot: "bg-status-confirmed-dot" },
  preparing: { badge: "bg-status-preparing-bg text-status-preparing-fg", dot: "bg-status-preparing-dot" },
  ready: { badge: "bg-status-ready-bg text-status-ready-fg", dot: "bg-status-ready-dot" },
  delivered: { badge: "bg-status-delivered-bg text-status-delivered-fg", dot: "bg-status-delivered-dot" },
  cancelled: { badge: "bg-status-cancelled-bg text-status-cancelled-fg", dot: "bg-status-cancelled-dot" },
};

export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={cn("inline-flex h-6 items-center gap-1.5 whitespace-nowrap rounded-sm px-2 text-[12px] font-semibold leading-4", STYLE[status].badge)}>
      <span aria-hidden="true" className={cn("size-2 flex-none rounded-pill", STYLE[status].dot)} />
      {STATUS_LABEL[status]}
    </span>
  );
}
