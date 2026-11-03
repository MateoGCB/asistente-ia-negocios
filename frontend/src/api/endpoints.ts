import { apiRequest } from "./client";
import type {
  Business, BusinessUpdate, CreateBusiness, LoginResponse, Menu, MenuItem, MenuItemCreate, MenuItemUpdate,
  MenuSummary, Message, OrderCreate, OrderPage, OrderStatus, OwnerOrder, PublicMenu, PublicOrder,
  User, UserCreate, UserLogin,
} from "./types";

// ---- Auth (no token)
export const login = (body: UserLogin) => apiRequest<LoginResponse>("/auth/login", { method: "POST", body, auth: false });
export const register = (body: UserCreate) => apiRequest<User>("/auth/register", { method: "POST", body, auth: false });

// ---- Businesses
export const listBusinesses = () => apiRequest<Business[]>("/businesses/");
export const getBusiness = (id: number) => apiRequest<Business>(`/businesses/${id}`);
export const createBusiness = (body: CreateBusiness) => apiRequest<Business>("/businesses/", { method: "POST", body });
export const updateBusiness = (id: number, body: BusinessUpdate) =>
  apiRequest<Business>(`/businesses/${id}`, { method: "PATCH", body });
export const archiveBusiness = (id: number) => apiRequest<Message>(`/businesses/${id}`, { method: "DELETE" });
export const removeBusinessMenu = (id: number) => apiRequest<Message>(`/businesses/${id}/menu`, { method: "DELETE" });

// ---- Menus and items
export const listMenus = () => apiRequest<MenuSummary[]>("/menus/");
export const createMenu = (name: string) => apiRequest<Menu>("/menus/", { method: "POST", body: { name } });
export const deleteMenu = (id: number) => apiRequest<Message>(`/menus/${id}`, { method: "DELETE" });
export const listMenuItems = (menuId: number) => apiRequest<MenuItem[]>(`/menus/${menuId}/items`);
export const createMenuItem = (menuId: number, body: MenuItemCreate) =>
  apiRequest<MenuItem>(`/menus/${menuId}/items`, { method: "POST", body });
export const updateMenuItem = (menuId: number, itemId: number, body: MenuItemUpdate) =>
  apiRequest<MenuItem>(`/menus/${menuId}/items/${itemId}`, { method: "PATCH", body });
export const deleteMenuItem = (menuId: number, itemId: number) =>
  apiRequest<Message>(`/menus/${menuId}/items/${itemId}`, { method: "DELETE" });

// ---- Owner orders ("view" and "status" cannot go together: the backend answers 422)
export type OrdersQuery = { view?: "active" | "history"; status?: OrderStatus; page?: number; page_size?: number };
export const listOrders = (businessId: number, query: OrdersQuery) =>
  apiRequest<OrderPage>(`/businesses/${businessId}/orders`, { query });
export const changeOrderStatus = (businessId: number, orderId: number, status: OrderStatus) =>
  apiRequest<OwnerOrder>(`/businesses/${businessId}/orders/${orderId}/status`, { method: "PATCH", body: { status } });

// ---- Public (no token)
export const getPublicMenu = (slug: string) =>
  apiRequest<PublicMenu>(`/public/${encodeURIComponent(slug)}/menu`, { auth: false });
export const createPublicOrder = (slug: string, body: OrderCreate) =>
  apiRequest<PublicOrder>(`/public/${encodeURIComponent(slug)}/orders`, { method: "POST", body, auth: false });
