import { describe, expect, it } from "vitest";
import { addBlockReason, cartCount, cartReducer, cartTotalCents, loadCart, saveCart, type Cart } from "../src/features/public/cart";

const apply = (cart: Cart, ...actions: Parameters<typeof cartReducer>[1][]) => actions.reduce(cartReducer, cart);
const times = <T,>(n: number, value: T): T[] => Array.from({ length: n }, () => value);

describe("cart reducer", () => {
  it("adds, increments and decrements", () => {
    const cart = apply([], { type: "increment", itemId: 1 }, { type: "increment", itemId: 1 }, { type: "increment", itemId: 2 });
    expect(cart).toEqual([{ itemId: 1, qty: 2 }, { itemId: 2, qty: 1 }]);
    expect(cartCount(cart)).toBe(3);
    expect(apply(cart, { type: "decrement", itemId: 1 })).toEqual([{ itemId: 1, qty: 1 }, { itemId: 2, qty: 1 }]);
  });

  it("removes an item when its quantity reaches zero", () => {
    expect(apply([{ itemId: 1, qty: 1 }], { type: "decrement", itemId: 1 })).toEqual([]);
  });

  it("stops at 50 units of the same item", () => {
    const cart = apply([], ...times(55, { type: "increment" as const, itemId: 7 }));
    expect(cart).toEqual([{ itemId: 7, qty: 50 }]);
  });

  it("stops at 30 different items", () => {
    const cart = apply([], ...Array.from({ length: 31 }, (_, i) => ({ type: "increment" as const, itemId: i + 1 })));
    expect(cart).toHaveLength(30);
    expect(cart.some((line) => line.itemId === 31)).toBe(false);
    // An item already in the cart can still grow
    expect(apply(cart, { type: "increment", itemId: 1 })[0]).toEqual({ itemId: 1, qty: 2 });
  });

  it("removes one item, keeps only valid ones and clears", () => {
    const cart: Cart = [{ itemId: 1, qty: 2 }, { itemId: 2, qty: 1 }, { itemId: 3, qty: 4 }];
    expect(apply(cart, { type: "remove", itemId: 2 })).toEqual([{ itemId: 1, qty: 2 }, { itemId: 3, qty: 4 }]);
    expect(apply(cart, { type: "keepOnly", itemIds: [3] })).toEqual([{ itemId: 3, qty: 4 }]);
    expect(apply(cart, { type: "clear" })).toEqual([]);
  });
});

describe("cart totals and limits", () => {
  const prices = new Map([[1, 850000], [2, 350050], [3, 20000000]]); // $ 8.500, $ 3.500,50, $ 200.000

  it("computes the display total in exact cents", () => {
    expect(cartTotalCents([{ itemId: 1, qty: 1 }, { itemId: 2, qty: 2 }], prices)).toBe(1550100);
  });

  it("says why one more unit cannot be added", () => {
    expect(addBlockReason([{ itemId: 1, qty: 50 }], 1, prices)).toBe("qtyLimit");
    const full: Cart = Array.from({ length: 30 }, (_, i) => ({ itemId: 100 + i, qty: 1 }));
    expect(addBlockReason(full, 1, prices)).toBe("itemsLimit");
    // 50 x $ 200.000 = $ 10.000.000 exactly: allowed; one more unit of anything goes over
    expect(addBlockReason([{ itemId: 3, qty: 49 }], 3, prices)).toBeNull();
    expect(addBlockReason([{ itemId: 3, qty: 50 }], 1, prices)).toBe("totalLimit");
  });
});

describe("cart storage", () => {
  it("is saved per slug and ignores broken data", () => {
    saveCart("pizzeria", [{ itemId: 1, qty: 3 }]);
    expect(loadCart("pizzeria")).toEqual([{ itemId: 1, qty: 3 }]);
    expect(loadCart("otro-local")).toEqual([]);

    sessionStorage.setItem("comanda.cart.roto", '[{"itemId":1,"qty":99},{"itemId":"x","qty":1},{"itemId":2,"qty":2}]');
    expect(loadCart("roto")).toEqual([{ itemId: 2, qty: 2 }]);
    sessionStorage.setItem("comanda.cart.basura", "no es json");
    expect(loadCart("basura")).toEqual([]);
  });
});
