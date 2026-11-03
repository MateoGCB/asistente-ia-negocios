import { describe, expect, it, vi } from "vitest";
import { apiRequest } from "../src/api/client";
import { ApiError } from "../src/api/errors";
import { consumeSessionExpired, getToken, setToken } from "../src/api/session";
import { mockFetch } from "./utils";

const headersOf = (fetchMock: ReturnType<typeof mockFetch>, call = 0) =>
  (fetchMock.mock.calls[call]?.[1]?.headers ?? {}) as Record<string, string>;

async function catchError(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof ApiError) return error;
    throw error;
  }
  throw new Error("the request did not fail");
}

describe("apiRequest", () => {
  it("adds the token to authenticated requests", async () => {
    setToken("token-de-prueba");
    const fetchMock = mockFetch(() => ({ status: 200, body: [] }));

    await apiRequest("/businesses/");

    expect(headersOf(fetchMock).Authorization).toBe("Bearer token-de-prueba");
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("http://localhost:8000/businesses/");
  });

  it("never sends the token to public endpoints", async () => {
    setToken("token-de-prueba");
    const fetchMock = mockFetch(() => ({ status: 200, body: {} }));

    await apiRequest("/public/pizzeria/menu", { auth: false });

    expect(headersOf(fetchMock).Authorization).toBeUndefined();
  });

  it("sends JSON bodies and query parameters", async () => {
    const fetchMock = mockFetch(() => ({ status: 200, body: {} }));

    await apiRequest("/businesses/3/orders", { query: { view: "history", page: 2, status: undefined } });
    await apiRequest("/menus/", { method: "POST", body: { name: "Carta" } });

    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("http://localhost:8000/businesses/3/orders?view=history&page=2");
    expect(fetchMock.mock.calls[1]?.[1]?.body).toBe('{"name":"Carta"}');
    expect(headersOf(fetchMock, 1)["Content-Type"]).toBe("application/json");
  });

  it("a 401 clears the session and leaves the 'expired' notice", async () => {
    setToken("token-vencido");
    mockFetch(() => ({ status: 401, body: { detail: "Could not validate credentials" } }));

    const error = await catchError(apiRequest("/businesses/"));

    expect(error.kind).toBe("unauthorized");
    expect(getToken()).toBeNull();
    expect(consumeSessionExpired()).toBe(true);
    expect(consumeSessionExpired()).toBe(false); // read only once
  });

  it("a 401 from login (no token involved) does not touch the session", async () => {
    setToken("token-valido");
    mockFetch(() => ({ status: 401, body: { detail: "Invalid authentication" } }));

    const error = await catchError(apiRequest("/auth/login", { method: "POST", body: {}, auth: false }));

    expect(error.status).toBe(401);
    expect(getToken()).toBe("token-valido");
  });

  it("maps 404 and 409 keeping the backend detail", async () => {
    mockFetch((url) =>
      url.pathname === "/menus/7"
        ? { status: 409, body: { detail: "This menu is used by one or more active businesses." } }
        : { status: 404, body: { detail: "Menu not found" } });

    const notFound = await catchError(apiRequest("/public/no-existe/menu", { auth: false }));
    const conflict = await catchError(apiRequest("/menus/7", { method: "DELETE" }));

    expect([notFound.kind, notFound.status, notFound.detail]).toEqual(["not_found", 404, "Menu not found"]);
    expect([conflict.kind, conflict.status, conflict.detail]).toEqual(["conflict", 409, "This menu is used by one or more active businesses."]);
  });

  it("maps a 422 list to errors per field", async () => {
    mockFetch(() => ({
      status: 422,
      body: {
        detail: [
          { loc: ["body", "customer_phone"], msg: "Value error, Phone must contain at least 6 digits", type: "value_error" },
          { loc: ["body", "items", 0, "quantity"], msg: "Input should be less than or equal to 50", type: "less_than_equal" },
        ],
      },
    }));

    const error = await catchError(apiRequest("/public/x/orders", { method: "POST", body: {}, auth: false }));

    expect(error.kind).toBe("validation");
    expect(error.fieldErrors).toEqual({
      customer_phone: "Value error, Phone must contain at least 6 digits",
      "items.0.quantity": "Input should be less than or equal to 50",
    });
  });

  it("keeps a 422 sent as plain text (business rule) as its detail", async () => {
    mockFetch(() => ({ status: 422, body: { detail: "The order total exceeds the maximum allowed (10000000.00)" } }));

    const error = await catchError(apiRequest("/public/x/orders", { method: "POST", body: {}, auth: false }));

    expect(error.kind).toBe("validation");
    expect(error.detail).toBe("The order total exceeds the maximum allowed (10000000.00)");
    expect(error.fieldErrors).toEqual({});
  });

  it("turns a network failure into a 'network' error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));

    const error = await catchError(apiRequest("/businesses/"));

    expect([error.kind, error.status]).toEqual(["network", 0]);
  });
});
