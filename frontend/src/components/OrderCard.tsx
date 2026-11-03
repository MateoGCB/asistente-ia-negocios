import type { OrderStatus, OwnerOrder } from "../api/types";
import { formatTime } from "../lib/dates";
import { formatCents, toCents } from "../lib/money";
import { CANCEL_REASON_LABEL, canCancel, nextAction } from "../lib/orderStatus";
import { Button } from "./Button";
import { StatusBadge } from "./StatusBadge";

type OrderCardProps = {
  order: OwnerOrder;
  busy?: boolean;
  onAdvance: (order: OwnerOrder, to: OrderStatus) => void;
  onCancel: (order: OwnerOrder) => void;
};

// One order in the owner panel. Only the next valid action of the state machine is offered;
// final orders (delivered, cancelled) show no actions at all.
export function OrderCard({ order, busy = false, onAdvance, onCancel }: OrderCardProps) {
  const next = nextAction(order.status);
  const cancellable = canCancel(order.status);

  return (
    <article
      aria-label={`Pedido #${order.number}`}
      className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4 text-ink"
    >
      <header className="flex items-center justify-between gap-3">
        <span className="text-order-number">#{order.number}</span>
        <StatusBadge status={order.status} />
      </header>

      <p className="text-body-sm text-ink-muted">
        <strong className="font-semibold text-ink">{order.customer_name}</strong>
        {" · "}
        <a href={`tel:${order.customer_phone.replace(/[^\d+]/g, "")}`} className="text-data-sm text-ink-muted underline-offset-2 hover:underline focus-ring">
          {order.customer_phone}
        </a>
      </p>

      <ul className="flex flex-col gap-1 border-y border-border py-3 text-[14px] leading-5">
        {order.items.map((item, index) => (
          <li key={index} className="flex justify-between gap-3">
            <span>
              <span className="text-data-sm text-ink-muted">{item.quantity}×</span> {item.name}
            </span>
            <span className="text-price">{formatCents(toCents(item.unit_price) * item.quantity)}</span>
          </li>
        ))}
      </ul>

      {order.notes && (
        <p className="whitespace-pre-wrap break-words rounded-md bg-surface-sunken px-3 py-2 text-body-sm text-ink">
          {order.notes}
        </p>
      )}

      {order.status === "cancelled" && order.cancel_reason && (
        <p className="text-body-sm text-ink-muted">{CANCEL_REASON_LABEL[order.cancel_reason]}</p>
      )}

      <footer className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col">
          <span className="font-mono text-[16px] font-semibold leading-[22px] tabular-nums">{formatCents(toCents(order.total))}</span>
          <span className="text-caption text-ink-muted">
            Recibido {formatTime(order.created_at)}
            {order.ready_at ? ` · Listo ${formatTime(order.ready_at)}` : ""}
          </span>
        </div>
        {(next || cancellable) && (
          <div className="flex flex-wrap gap-2">
            {cancellable && (
              <Button variant="ghost" disabled={busy} onClick={() => onCancel(order)}>
                Cancelar
              </Button>
            )}
            {next && (
              <Button variant="primary" disabled={busy} onClick={() => onAdvance(order, next.to)}>
                {next.label}
              </Button>
            )}
          </div>
        )}
      </footer>
    </article>
  );
}
