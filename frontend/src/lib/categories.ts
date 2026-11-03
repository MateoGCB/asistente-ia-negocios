import type { MenuCategory } from "../api/types";

// Order in which categories are shown, with their visible names
export const CATEGORY_ORDER: MenuCategory[] = ["entrada", "plato_principal", "postre", "bebida", "cafeteria"];

export const CATEGORY_LABEL: Record<MenuCategory, string> = {
  entrada: "Entradas",
  plato_principal: "Platos principales",
  postre: "Postres",
  bebida: "Bebidas",
  cafeteria: "Cafetería",
};

// Groups items by category in the fixed order, skipping empty categories
export function groupByCategory<T extends { category: MenuCategory }>(items: T[]): { category: MenuCategory; items: T[] }[] {
  return CATEGORY_ORDER
    .map((category) => ({ category, items: items.filter((item) => item.category === category) }))
    .filter((group) => group.items.length > 0);
}
