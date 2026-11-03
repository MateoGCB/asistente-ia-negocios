import { useState } from "react";
import { motion } from "motion/react";
import { Navigate, useNavigate, useParams } from "react-router";
import { useDocumentTitle } from "../../app/useDocumentTitle";
import { Button } from "../../components/Button";
import { formatTime } from "../../lib/dates";
import { formatCents, toCents } from "../../lib/money";
import { clearLastOrder, loadLastOrder } from "./lastOrder";

export function PublicDonePage() {
  useDocumentTitle("Pedido enviado");
  const slug = useParams().slug ?? "";
  const navigate = useNavigate();
  const [order] = useState(() => loadLastOrder(slug));

  if (!order) return <Navigate to={`/pedir/${slug}`} replace />;

  const newOrder = () => {
    clearLastOrder(slug);
    navigate(`/pedir/${slug}`);
  };

  return (
    <div className="flex flex-col items-center gap-6 py-6 text-center">
      <h1 className="text-display-md">¡Pedido enviado!</h1>
      <div className="flex flex-col items-center gap-2 rounded-lg border border-border bg-surface px-6 py-6">
        <span className="text-label text-ink-muted">Tu número de pedido</span>
        <motion.span
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="text-order-number-hero"
        >
          #{order.number}
        </motion.span>
      </div>
      <p className="text-body text-ink-muted">
        El local lo va a confirmar en breve. Guardá este número: te lo van a pedir al retirarlo.
      </p>
      <section aria-label="Detalle del pedido" className="flex w-full flex-col gap-2 rounded-lg border border-border bg-surface p-4 text-left">
        <ul className="flex flex-col gap-2">
          {order.items.map((item, index) => (
            <li key={index} className="flex justify-between gap-3 text-body">
              <span><span className="text-data-sm text-ink-muted">{item.quantity}×</span> {item.name}</span>
              <span className="text-price">{formatCents(toCents(item.unit_price) * item.quantity)}</span>
            </li>
          ))}
        </ul>
        <div className="flex justify-between gap-3 border-t border-border pt-3">
          <span className="text-heading-3">Total</span>
          <span className="font-mono text-[16px] font-semibold leading-6 tabular-nums">{formatCents(toCents(order.total))}</span>
        </div>
        <span className="text-caption text-ink-muted">Enviado a las {formatTime(order.created_at)}</span>
      </section>
      <Button variant="secondary" size="lg" block onClick={newOrder}>Hacer otro pedido</Button>
    </div>
  );
}
