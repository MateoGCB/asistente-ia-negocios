import { useState, type KeyboardEvent } from "react";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { Link, useSearchParams } from "react-router";
import { RefreshCw } from "lucide-react";
import { changeOrderStatus, listBusinesses, listOrders, type OrdersQuery } from "../../api/endpoints";
import { isApiError } from "../../api/errors";
import type { OrderStatus, OwnerOrder } from "../../api/types";
import { PageHeader } from "../../app/AppShell";
import { queryKeys } from "../../app/queryKeys";
import { useDocumentTitle } from "../../app/useDocumentTitle";
import { Button } from "../../components/Button";
import { buttonClasses } from "../../components/buttonStyles";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { OrderCard } from "../../components/OrderCard";
import { EmptyState, ErrorState, LoadingList } from "../../components/States";
import { SelectField } from "../../components/TextField";
import { useToast } from "../../components/toastContext";
import { cn } from "../../lib/cn";
import { formatTime } from "../../lib/dates";
import { describeError } from "../../lib/errorMessages";
import { ACTIVE_REFRESH_MS, HISTORY_PAGE_SIZE } from "../../lib/limits";
import { ACTIVE_STATUSES, CLOSED_STATUSES, STATUS_LABEL } from "../../lib/orderStatus";

type Tab = "active" | "history";
const TABS: { id: Tab; label: string }[] = [
  { id: "active", label: "Activos" },
  { id: "history", label: "Historial" },
];

export function OrdersPage() {
  useDocumentTitle("Pedidos");
  const businesses = useQuery({ queryKey: queryKeys.businesses, queryFn: listBusinesses });

  if (businesses.isPending) return <><PageHeader title="Pedidos" /><LoadingList label="Cargando sucursales" /></>;
  if (businesses.isError) {
    return <><PageHeader title="Pedidos" /><ErrorState message={describeError(businesses.error)} onRetry={() => businesses.refetch()} /></>;
  }
  if (businesses.data.length === 0) {
    return (
      <>
        <PageHeader title="Pedidos" />
        <EmptyState
          title="Todavía no tenés sucursales"
          description="Los pedidos llegan a una sucursal. Creá la primera y asignale un menú para empezar a recibirlos."
          action={<Link to="/negocios" className={buttonClasses("primary")}>Crear una sucursal</Link>}
        />
      </>
    );
  }
  return <OrdersBoard businesses={businesses.data} />;
}

function OrdersBoard({ businesses }: { businesses: { id: number; name: string }[] }) {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  // Branch, tab, filter and page live in the URL: a reload (or a shared link) keeps them
  const [params, setParams] = useSearchParams();
  const requestedId = Number(params.get("sucursal"));
  const business = businesses.find((b) => b.id === requestedId) ?? businesses[0]!;
  const tab: Tab = params.get("vista") === "historial" ? "history" : "active";
  const groupStatuses = tab === "active" ? ACTIVE_STATUSES : CLOSED_STATUSES;
  const statusParam = params.get("estado") as OrderStatus | null;
  const status = statusParam && groupStatuses.includes(statusParam) ? statusParam : null;
  const page = Math.max(1, Number(params.get("pagina")) || 1);

  const update = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value === null) next.delete(key);
      else next.set(key, value);
    }
    setParams(next, { replace: true });
  };

  // The backend does not accept view and status together: with a status filter, only status is sent
  // (its group rules still apply: active ones oldest first, closed ones newest first and paginated)
  const query: OrdersQuery = status
    ? { status, ...(tab === "history" ? { page, page_size: HISTORY_PAGE_SIZE } : {}) }
    : tab === "active" ? { view: "active" } : { view: "history", page, page_size: HISTORY_PAGE_SIZE };

  const orders = useQuery({
    queryKey: [...queryKeys.orders(business.id), query],
    queryFn: () => listOrders(business.id, query),
    // Automatic refresh only for active orders, and only while the browser tab is visible
    refetchInterval: tab === "active" ? ACTIVE_REFRESH_MS : false,
    refetchIntervalInBackground: false,
    placeholderData: keepPreviousData,
  });

  const [busyOrderId, setBusyOrderId] = useState<number | null>(null);
  const [toCancel, setToCancel] = useState<OwnerOrder | null>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: queryKeys.orders(business.id) });

  const changeStatus = async (order: OwnerOrder, to: OrderStatus) => {
    setBusyOrderId(order.id);
    try {
      await changeOrderStatus(business.id, order.id, to);
      if (to === "cancelled") notify(`Cancelaste el pedido #${order.number}.`);
    } catch (error) {
      if (isApiError(error) && (error.kind === "conflict" || error.kind === "not_found")) {
        // Someone else changed it (or it expired). Show the real status.
        notify(`Este pedido cambió de estado (#${order.number}). Actualizamos la lista.`, "error");
      } else {
        notify(describeError(error), "error");
      }
    } finally {
      setBusyOrderId(null);
      setToCancel(null);
      await refresh();
    }
  };

  const onTabKey = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      event.preventDefault();
      const nextTab = tab === "active" ? "history" : "active";
      update({ vista: nextTab === "history" ? "historial" : null, estado: null, pagina: null });
      document.getElementById(`tab-${nextTab}`)?.focus();
    }
  };

  const data = orders.data;
  const totalPages = data?.page_size ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <>
      <PageHeader title="Pedidos">
        <Button variant="secondary" onClick={() => orders.refetch()} disabled={orders.isFetching}>
          <RefreshCw aria-hidden="true" size={20} strokeWidth={1.75} />
          Actualizar
        </Button>
      </PageHeader>

      <div className="flex flex-wrap items-end gap-4">
        <div className="min-w-[220px]">
          <SelectField
            label="Sucursal"
            value={String(business.id)}
            onChange={(e) => update({ sucursal: e.target.value, pagina: null })}
          >
            {businesses.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </SelectField>
        </div>
        <div className="min-w-[200px]">
          <SelectField
            label="Estado"
            value={status ?? ""}
            onChange={(e) => update({ estado: e.target.value || null, pagina: null })}
          >
            <option value="">Todos</option>
            {groupStatuses.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </SelectField>
        </div>
      </div>

      <div role="tablist" aria-label="Pedidos" className="flex w-fit gap-1 rounded-md bg-surface-sunken p-1">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            id={`tab-${id}`}
            type="button"
            role="tab"
            aria-selected={tab === id}
            aria-controls="orders-panel"
            tabIndex={tab === id ? 0 : -1}
            onKeyDown={onTabKey}
            onClick={() => update({ vista: id === "history" ? "historial" : null, estado: null, pagina: null })}
            className={cn(
              "min-h-10 cursor-pointer rounded-md px-4 text-[14px] font-semibold leading-5 transition-tint focus-ring",
              tab === id ? "bg-surface text-ink shadow-sm" : "text-ink-muted hover:text-ink",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <section id="orders-panel" role="tabpanel" aria-labelledby={`tab-${tab}`} className="flex flex-col gap-4">
        {data && (
          <p className="text-caption text-ink-muted" aria-live="polite">
            {data.total} {data.total === 1 ? "pedido" : "pedidos"}
            {tab === "active" && orders.dataUpdatedAt > 0 && ` · Actualizado ${formatTime(new Date(orders.dataUpdatedAt).toISOString())}`}
          </p>
        )}
        {orders.isPending ? (
          <LoadingList label="Cargando pedidos" />
        ) : orders.isError ? (
          <ErrorState message={describeError(orders.error)} onRetry={() => orders.refetch()} />
        ) : orders.data.items.length === 0 ? (
          <EmptyState
            title={tab === "active" ? "No hay pedidos en curso" : "Todavía no hay pedidos cerrados"}
            description={tab === "active"
              ? "Los pedidos nuevos aparecen acá solos. Compartí el enlace público de la sucursal para recibirlos."
              : "Los pedidos entregados y cancelados aparecen acá, del más nuevo al más viejo."}
            action={tab === "active" ? <Link to="/negocios" className={buttonClasses("secondary")}>Ver enlaces de las sucursales</Link> : undefined}
          />
        ) : (
          <ul className="grid gap-6 xl:grid-cols-2">
            <AnimatePresence initial={false}>
              {orders.data.items.map((order) => (
                <motion.li
                  key={order.id}
                  layout="position"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.18, ease: "easeOut" }}
                >
                  <OrderCard
                    order={order}
                    busy={busyOrderId === order.id}
                    onAdvance={changeStatus}
                    onCancel={setToCancel}
                  />
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}

        {data && data.page !== null && data.page !== undefined && totalPages > 1 && (
          <nav aria-label="Páginas del historial" className="flex items-center gap-3">
            <Button variant="secondary" disabled={page <= 1} onClick={() => update({ pagina: String(page - 1) })}>Anterior</Button>
            <span className="text-body-sm text-ink-muted">Página {page} de {totalPages}</span>
            <Button variant="secondary" disabled={page >= totalPages} onClick={() => update({ pagina: String(page + 1) })}>Siguiente</Button>
          </nav>
        )}
      </section>

      <ConfirmDialog
        open={toCancel !== null}
        title={`¿Cancelar el pedido #${toCancel?.number ?? ""}?`}
        confirmLabel="Cancelar pedido"
        busy={busyOrderId !== null}
        onConfirm={() => toCancel && changeStatus(toCancel, "cancelled")}
        onCancel={() => setToCancel(null)}
      >
        El pedido de {toCancel?.customer_name} pasa a Cancelado y no se puede deshacer.
      </ConfirmDialog>
    </>
  );
}
