import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { OrderStatus, OwnerOrder } from "../src/api/types";
import { OrderCard } from "../src/components/OrderCard";
import { StatusBadge } from "../src/components/StatusBadge";

const WORD: Record<OrderStatus, string> = {
  pending: "Pendiente",
  confirmed: "Confirmado",
  preparing: "En preparación",
  ready: "Listo",
  delivered: "Entregado",
  cancelled: "Cancelado",
};

function order(status: OrderStatus, extra: Partial<OwnerOrder> = {}): OwnerOrder {
  return {
    id: 10,
    number: 42,
    customer_name: "Cliente Prueba",
    customer_phone: "351 555-0142",
    notes: null,
    items: [{ name: "Pizza Muzzarella", unit_price: "8500.00", quantity: 2 }],
    total: "17000.00",
    status,
    created_at: "2026-11-03T15:05:00Z",
    ready_at: null,
    cancel_reason: null,
    ...extra,
  };
}

describe("StatusBadge", () => {
  it.each(Object.entries(WORD))("always shows the word for %s", (status, word) => {
    render(<StatusBadge status={status as OrderStatus} />);
    expect(screen.getByText(word)).toBeInTheDocument();
  });
});

describe("OrderCard", () => {
  // Expected buttons per status, written by hand
  const EXPECTED: [OrderStatus, string[]][] = [
    ["pending", ["Cancelar", "Confirmar"]],
    ["confirmed", ["Cancelar", "Empezar a preparar"]],
    ["preparing", ["Cancelar", "Marcar listo"]],
    ["ready", ["Cancelar", "Marcar entregado"]],
    ["delivered", []],
    ["cancelled", []],
  ];

  it.each(EXPECTED)("in %s shows exactly the buttons %j", (status, buttons) => {
    render(<OrderCard order={order(status)} onAdvance={() => {}} onCancel={() => {}} />);
    const card = screen.getByRole("article", { name: "Pedido #42" });
    expect(within(card).queryAllByRole("button").map((b) => b.textContent)).toEqual(buttons);
    expect(within(card).getByText(WORD[status])).toBeInTheDocument();
  });

  it("the main button asks for the next status", async () => {
    const onAdvance = vi.fn();
    render(<OrderCard order={order("preparing")} onAdvance={onAdvance} onCancel={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: "Marcar listo" }));

    expect(onAdvance).toHaveBeenCalledWith(expect.objectContaining({ id: 10 }), "ready");
  });

  it("shows number, money in es-AR, local time, notes and the cancel reason", () => {
    render(
      <OrderCard
        order={order("cancelled", { notes: "Sin aceitunas", cancel_reason: "not_picked_up", ready_at: "2026-11-03T16:00:00Z" })}
        onAdvance={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(screen.getByText("#42")).toBeInTheDocument();
    expect(screen.getAllByText("$ 17.000")).toHaveLength(2); // the line (2 x 8.500) and the total; Testing Library normalizes the DOM text (non-breaking space -> space) but not the expected string
    expect(screen.getByText(/Recibido 12:05/)).toHaveTextContent("Recibido 12:05 · Listo 13:00"); // UTC-3
    expect(screen.getByText("Sin aceitunas")).toBeInTheDocument();
    expect(screen.getByText("No retirado a tiempo")).toBeInTheDocument();
  });
});
