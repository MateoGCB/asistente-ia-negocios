import { useEffect, useReducer } from "react";
import { cartReducer, loadCart, saveCart } from "./cart";

// The cart of one public page, saved in sessionStorage under its slug
export function useCart(slug: string) {
  const [cart, dispatch] = useReducer(cartReducer, slug, loadCart);

  useEffect(() => {
    saveCart(slug, cart);
  }, [slug, cart]);

  return [cart, dispatch] as const;
}
