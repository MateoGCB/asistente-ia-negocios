import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { getToken, setToken } from "../src/api/session";
import { mockFetch, renderApp } from "./utils";

describe("protected routes", () => {
  it("without a token, the panel redirects to /login", async () => {
    mockFetch(() => undefined);
    const { router } = renderApp("/pedidos");

    expect(await screen.findByRole("heading", { name: "Ingresá a tu panel" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });

  it("with a session, /login and /registro go straight to the panel", async () => {
    setToken("token-de-prueba");
    mockFetch((url) => (url.pathname === "/businesses/" ? { status: 200, body: [] } : undefined));
    const { router } = renderApp("/registro");

    expect(await screen.findByText("Todavía no tenés sucursales")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/pedidos");
  });

  it("a 401 while using the panel ends the session and says it expired", async () => {
    setToken("token-vencido");
    mockFetch(() => ({ status: 401, body: { detail: "Could not validate credentials" } }));
    renderApp("/negocios");

    expect(await screen.findByText("Tu sesión venció. Ingresá de nuevo para seguir.")).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });
});

describe("login", () => {
  it("a wrong password shows one generic message (and no password rules)", async () => {
    mockFetch(() => ({ status: 401, body: { detail: "Invalid authentication" } }));
    renderApp("/login");

    await userEvent.type(await screen.findByLabelText("Email"), "persona@example.com");
    await userEvent.type(screen.getByLabelText("Contraseña"), "123");
    await userEvent.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByText("El email o la contraseña no son correctos. Revisalos y probá de nuevo.")).toBeInTheDocument();
  });
});

describe("register", () => {
  it("shows the password rules before the user fails", async () => {
    mockFetch(() => undefined);
    renderApp("/registro");

    const rules = await screen.findByRole("list", { name: "Requisitos de la contraseña" });
    expect(rules).toHaveTextContent("Al menos 8 caracteres");
    expect(rules).toHaveTextContent("Como máximo 72 bytes");
    expect(rules).toHaveTextContent("Al menos una letra");
    expect(rules).toHaveTextContent("Al menos un número");
  });
});

describe("public page", () => {
  it("an unknown slug shows 'Este local no está disponible'", async () => {
    mockFetch((url) => (url.pathname === "/public/no-existe/menu" ? { status: 404, body: { detail: "Menu not found" } } : undefined));
    renderApp("/pedir/no-existe");

    expect(await screen.findByRole("heading", { name: "Este local no está disponible" })).toBeInTheDocument();
  });

  it("shows the menu by category and adds to the cart with the bar", async () => {
    mockFetch((url) => url.pathname === "/public/pizzeria/menu" ? {
      status: 200,
      body: {
        business_name: "Pizzería de Prueba",
        menu_name: "Carta",
        items: [
          { id: 1, name: "Muzzarella", description: "Salsa y queso", price: "8500.00", category: "plato_principal" },
          { id: 2, name: "Café con leche", description: "Taza grande", price: "3500.50", category: "cafeteria" },
        ],
      },
    } : undefined);
    renderApp("/pedir/pizzeria");

    expect(await screen.findByRole("heading", { name: "Pizzería de Prueba" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Platos principales" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cafetería" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Agregar Muzzarella" }));
    await userEvent.click(screen.getByRole("button", { name: "Agregar Café con leche" }));
    await userEvent.click(screen.getByRole("button", { name: "Agregar uno más de Café con leche" }));

    const bar = await screen.findByRole("link", { name: /Ver pedido/ });
    expect(bar).toHaveTextContent("3");
    expect(bar).toHaveTextContent("$ 15.501"); // 8.500 + 2 x 3.500,50 (DOM text normalized: plain space)
    await waitFor(() => expect(sessionStorage.getItem("comanda.cart.pizzeria")).toBe('[{"itemId":1,"qty":1},{"itemId":2,"qty":2}]'));
  });
});
