// Cache keys of TanStack Query in one place: after a change, invalidating the right key makes
// every screen that shows that data fetch it again.
export const queryKeys = {
  businesses: ["businesses"] as const,
  business: (id: number) => ["businesses", id] as const,
  menus: ["menus"] as const,
  menuItems: (menuId: number) => ["menus", menuId, "items"] as const,
  orders: (businessId: number) => ["orders", businessId] as const,
  publicMenu: (slug: string) => ["public-menu", slug] as const,
};
