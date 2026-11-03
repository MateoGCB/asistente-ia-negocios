import { expect, test } from "@playwright/test";

// The whole flow, once: register, log in, branch, menu with two items, assign it, order from the
// public page as a customer, then move the order to delivered from the panel. Fictitious data only.
test("from a new account to a delivered order", async ({ page, browser }) => {
  const email = `duena-${Date.now()}@example.com`;
  const password = "clave-segura-123";

  // 1. Register (it logs in automatically) and log out
  await page.goto("/registro");
  await page.getByLabel("Tu nombre").fill("Dueña Prueba");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Crear cuenta" }).click();
  await expect(page).toHaveURL(/\/negocios$/);
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page).toHaveURL(/\/login$/);

  // 2. Log in
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page).toHaveURL(/\/pedidos$/);

  // 3. Create a branch
  await page.getByRole("link", { name: "Sucursales" }).click();
  await page.getByRole("button", { name: "Crear la primera sucursal" }).click();
  await page.getByLabel("Nombre de la sucursal").fill("Pizzería de Prueba");
  await page.getByLabel("Rubro").fill("Gastronomía");
  await page.getByRole("button", { name: "Crear sucursal" }).click();
  await expect(page.getByRole("heading", { name: "Pizzería de Prueba" })).toBeVisible();
  const publicUrl = (await page.getByText("/pedir/").first().textContent())!.trim();
  expect(publicUrl).toMatch(/\/pedir\/pizzeria-de-prueba$/);

  // 4. Create a menu with two items
  await page.getByRole("link", { name: "Menús" }).click();
  await page.getByLabel("Nombre del menú nuevo").fill("Carta de Prueba");
  await page.getByRole("button", { name: "Crear menú" }).click();
  await expect(page.getByRole("heading", { name: "Carta de Prueba" })).toBeVisible();
  for (const [name, price, category] of [["Muzzarella", "8500", "Platos principales"], ["Café con leche", "3500,50", "Cafetería"]]) {
    await page.getByLabel("Nombre del plato").fill(name!);
    await page.getByLabel("Categoría").selectOption({ label: category! });
    await page.getByLabel("Descripción").fill("Descripción de prueba");
    await page.getByLabel("Precio").fill(price!);
    await page.getByRole("button", { name: "Agregar plato" }).click();
    await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  }

  // 5. Assign the menu to the branch
  await page.getByRole("link", { name: "Sucursales" }).click();
  await page.getByRole("link", { name: "Ver y editar" }).click();
  await page.getByLabel("Elegí un menú").selectOption({ label: "Carta de Prueba (2 platos)" });
  await page.getByRole("button", { name: "Asignar menú" }).click();
  await expect(page.getByText("Menú actual: Carta de Prueba")).toBeVisible();

  // 6. Order as a customer, in a separate browser context (no session at all)
  const customerContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const customer = await customerContext.newPage();
  await customer.goto(new URL(publicUrl).pathname);
  await expect(customer.getByRole("heading", { name: "Pizzería de Prueba" })).toBeVisible();
  await customer.getByRole("button", { name: "Agregar Muzzarella" }).click();
  await customer.getByRole("button", { name: "Agregar Café con leche" }).click();
  await customer.getByRole("button", { name: "Agregar uno más de Café con leche" }).click();
  await expect(customer.getByRole("link", { name: /Ver pedido/ })).toContainText("15.501");
  await customer.getByRole("link", { name: /Ver pedido/ }).click();
  await customer.getByLabel("Tu nombre").fill("Cliente Prueba");
  await customer.getByLabel("Teléfono").fill("351 555-0142");
  await customer.getByRole("button", { name: "Hacer pedido" }).click();
  await expect(customer.getByText("#1", { exact: true })).toBeVisible();
  await customerContext.close();

  // 7. The owner sees it and moves it to delivered
  await page.getByRole("link", { name: "Pedidos" }).click();
  const card = page.getByRole("article", { name: "Pedido #1" });
  await expect(card).toContainText("Pendiente");
  await expect(card).toContainText("Cliente Prueba");
  for (const [action, status] of [["Confirmar", "Confirmado"], ["Empezar a preparar", "En preparación"], ["Marcar listo", "Listo"]]) {
    await card.getByRole("button", { name: action }).click();
    await expect(card).toContainText(status!);
  }
  await card.getByRole("button", { name: "Marcar entregado" }).click();
  await expect(page.getByText("No hay pedidos en curso")).toBeVisible();
  await page.getByRole("tab", { name: "Historial" }).click();
  await expect(page.getByRole("article", { name: "Pedido #1" })).toContainText("Entregado");
});
