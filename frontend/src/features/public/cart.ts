import { ORDER_ITEMS_MAX, ORDER_QTY_MAX, ORDER_TOTAL_MAX_CENTS } from "../../lib/limits";

// The cart only stores WHICH items and HOW MANY. Names and prices always come from the current
// public menu, so a stale cart can never show an old price. The backend recomputes the real total.
export type CartLine = { itemId: number; qty: number };
export type Cart = CartLine[];

export type CartAction =
  | { type: "increment"; itemId: number }
  | { type: "decrement"; itemId: number }
  | { type: "remove"; itemId: number }
  | { type: "keepOnly"; itemIds: number[] }
  | { type: "clear" };

export function cartReducer(cart: Cart, action: CartAction): Cart {
  switch (action.type) {
    case "increment": {
      const line = cart.find((l) => l.itemId === action.itemId);
      if (line) {
        if (line.qty >= ORDER_QTY_MAX) return cart; // 50 per item at most
        return cart.map((l) => (l.itemId === action.itemId ? { ...l, qty: l.qty + 1 } : l));
      }
      if (cart.length >= ORDER_ITEMS_MAX) return cart; // 30 different items at most
      return [...cart, { itemId: action.itemId, qty: 1 }];
    }
    case "decrement":
      return cart
        .map((l) => (l.itemId === action.itemId ? { ...l, qty: l.qty - 1 } : l))
        .filter((l) => l.qty > 0);
    case "remove":
      return cart.filter((l) => l.itemId !== action.itemId);
    case "keepOnly":
      return cart.filter((l) => action.itemIds.includes(l.itemId));
    case "clear":
      return [];
  }
}

export function cartCount(cart: Cart): number {
  return cart.reduce((count, line) => count + line.qty, 0);
}

// priceCents: current price of each item (from the public menu). Unknown items count as 0.
export function cartTotalCents(cart: Cart, priceCents: Map<number, number>): number {
  return cart.reduce((total, line) => total + (priceCents.get(line.itemId) ?? 0) * line.qty, 0);
}

export type AddBlock = "qtyLimit" | "itemsLimit" | "totalLimit" | null;

// Why one more unit of this item cannot be added (null = it can)
export function addBlockReason(cart: Cart, itemId: number, priceCents: Map<number, number>): AddBlock {
  const line = cart.find((l) => l.itemId === itemId);
  if (line && line.qty >= ORDER_QTY_MAX) return "qtyLimit";
  if (!line && cart.length >= ORDER_ITEMS_MAX) return "itemsLimit";
  if (cartTotalCents(cart, priceCents) + (priceCents.get(itemId) ?? 0) > ORDER_TOTAL_MAX_CENTS) return "totalLimit";
  return null;
}

// ---- Persistence: sessionStorage, one cart per slug (it disappears when the tab is closed)

const cartKey = (slug: string) => `comanda.cart.${slug}`;

export function loadCart(slug: string): Cart {
  try {
    const parsed: unknown = JSON.parse(sessionStorage.getItem(cartKey(slug)) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    // Never trust stored data blindly: keep only well-formed lines within the limits
    return parsed
      .filter((l): l is CartLine =>
        typeof l === "object" && l !== null && Number.isInteger(l.itemId) && Number.isInteger(l.qty)
        && l.qty >= 1 && l.qty <= ORDER_QTY_MAX)
      .slice(0, ORDER_ITEMS_MAX);
  } catch {
    return [];
  }
}

export function saveCart(slug: string, cart: Cart): void {
  try {
    if (cart.length === 0) sessionStorage.removeItem(cartKey(slug));
    else sessionStorage.setItem(cartKey(slug), JSON.stringify(cart));
  } catch {
    // storage blocked: the cart lives only in memory
  }
}
