import type { components } from "./schema";

type Schemas = components["schemas"];

export type Business = Schemas["Business"];
export type BusinessUpdate = Schemas["BusinessUpdate"];
// The generated type marks pickup_timeout_hours as required because it has a default;
// in the backend it is optional (24 when missing or null).
export type CreateBusiness = Omit<Schemas["CreateBusiness"], "pickup_timeout_hours"> & { pickup_timeout_hours?: number };
export type MenuSummary = Schemas["MenuSummary"];
export type Menu = Schemas["Menu"];
export type MenuItem = Schemas["MenuItem"];
export type MenuItemCreate = Schemas["MenuItemCreate"];
export type MenuItemUpdate = Schemas["MenuItemUpdate"];
export type MenuCategory = Schemas["MenuCategory"];
export type OrderStatus = Schemas["OrderStatus"];
export type CancelReason = Schemas["CancelReason"];
export type OwnerOrder = Schemas["OwnerOrder"];
export type OrderPage = Schemas["OrderPage"];
export type PublicMenu = Schemas["PublicMenu"];
export type PublicMenuItem = Schemas["PublicMenuItem"];
export type PublicOrder = Schemas["PublicOrder"];
export type OrderCreate = Schemas["OrderCreate"];
export type User = Schemas["User"];
export type UserCreate = Schemas["UserCreate"];
export type UserLogin = Schemas["UserLogin"];
export type Message = Schemas["Message"];

// POST /auth/login has no response_model in the backend, so its body is not in the OpenAPI document
export type LoginResponse = { access_token: string; token_type: string };
