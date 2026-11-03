import type { PublicOrder } from "../../api/types";

// The order just placed, kept for the "Pedido enviado" screen (also survives a reload of that screen)
const key = (slug: string) => `comanda.lastOrder.${slug}`;

export function saveLastOrder(slug: string, order: PublicOrder): void {
  try {
    sessionStorage.setItem(key(slug), JSON.stringify(order));
  } catch {
    // storage blocked: the screen will send the customer back to the menu
  }
}

export function loadLastOrder(slug: string): PublicOrder | null {
  try {
    const raw = sessionStorage.getItem(key(slug));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PublicOrder;
    return typeof parsed.number === "number" ? parsed : null;
  } catch {
    return null;
  }
}

export function clearLastOrder(slug: string): void {
  try {
    sessionStorage.removeItem(key(slug));
  } catch {
    // nothing to clear
  }
}
