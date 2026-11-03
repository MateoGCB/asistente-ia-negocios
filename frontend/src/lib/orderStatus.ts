import type { CancelReason, OrderStatus } from "../api/types";

export const STATUS_LABEL: Record<OrderStatus, string> = {
  pending: "Pendiente",
  confirmed: "Confirmado",
  preparing: "En preparación",
  ready: "Listo",
  delivered: "Entregado",
  cancelled: "Cancelado",
};

export const CANCEL_REASON_LABEL: Record<CancelReason, string> = {
  owner: "Cancelado por el local",
  not_picked_up: "No retirado a tiempo",
};

export const ACTIVE_STATUSES: OrderStatus[] = ["pending", "confirmed", "preparing", "ready"];
export const CLOSED_STATUSES: OrderStatus[] = ["delivered", "cancelled"];

export type NextAction = { to: OrderStatus; label: string };

// The forward step of the state machine: pending -> confirmed -> preparing -> ready -> delivered.
// Final statuses (delivered, cancelled) have no next action.
const NEXT: Record<OrderStatus, NextAction | null> = {
  pending: { to: "confirmed", label: "Confirmar" },
  confirmed: { to: "preparing", label: "Empezar a preparar" },
  preparing: { to: "ready", label: "Marcar listo" },
  ready: { to: "delivered", label: "Marcar entregado" },
  delivered: null,
  cancelled: null,
};

export function nextAction(status: OrderStatus): NextAction | null {
  return NEXT[status];
}

// Cancelling is allowed from every non-final status
export function canCancel(status: OrderStatus): boolean {
  return ACTIVE_STATUSES.includes(status);
}
