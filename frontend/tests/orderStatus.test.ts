import { describe, expect, it } from "vitest";
import type { OrderStatus } from "../src/api/types";
import { canCancel, nextAction } from "../src/lib/orderStatus";

// Written by hand ON PURPOSE (not built from the code's own table):
// status -> [next status, button label, can cancel]
const MACHINE: [OrderStatus, OrderStatus | null, string | null, boolean][] = [
  ["pending", "confirmed", "Confirmar", true],
  ["confirmed", "preparing", "Empezar a preparar", true],
  ["preparing", "ready", "Marcar listo", true],
  ["ready", "delivered", "Marcar entregado", true],
  ["delivered", null, null, false],
  ["cancelled", null, null, false],
];

describe("order state machine (frontend side)", () => {
  it.each(MACHINE)("%s -> %s (%s), cancel allowed: %s", (status, to, label, cancellable) => {
    const action = nextAction(status);
    expect(action?.to ?? null).toBe(to);
    expect(action?.label ?? null).toBe(label);
    expect(canCancel(status)).toBe(cancellable);
  });
});
