import { mkdirSync, mkdtempSync, readdirSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

// End-to-end smoke test: real backend + real frontend, driven by a real browser.
// The backend ALWAYS runs on a brand-new SQLite file in frontend/.e2e-tmp/ (ignored by Git),
// never on backend/businesses.db.
const here = fileURLToPath(new URL(".", import.meta.url));
const repo = resolve(here, "..");
const python = process.platform === "win32" ? join(repo, "venv", "Scripts", "python.exe") : join(repo, "venv", "bin", "python");
const tmpRoot = join(here, ".e2e-tmp");

if (!process.env.COMANDA_E2E_DIR) {
  // Main process (the workers inherit the variable and skip this block)
  mkdirSync(tmpRoot, { recursive: true });
  for (const old of readdirSync(tmpRoot)) {
    // Leftovers of previous runs (on Windows an open .db cannot be deleted while the backend runs)
    try { rmSync(join(tmpRoot, old), { recursive: true, force: true }); } catch { /* still in use: next time */ }
  }
  const dir = mkdtempSync(join(tmpRoot, "run-"));
  process.env.COMANDA_E2E_DIR = dir;
  // When Playwright exits, the servers are already stopped and the file can be removed
  process.once("exit", () => {
    try { rmSync(dir, { recursive: true, force: true }); } catch { /* removed on the next run */ }
  });
}
const databaseFile = join(process.env.COMANDA_E2E_DIR, "e2e.db").replace(/\\/g, "/");
if (!databaseFile.includes("/.e2e-tmp/")) throw new Error("The e2e test must only use a temporary database");

const API_PORT = 8011;
const WEB_PORT = 5174;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `"${python}" -m uvicorn main:app --port ${API_PORT}`,
      cwd: join(repo, "backend"),
      url: `http://127.0.0.1:${API_PORT}/openapi.json`,
      reuseExistingServer: false,
      env: {
        DATABASE_URL: `sqlite:///${databaseFile}`,
        SECRET_KEY: "e2e-only-secret-key-not-used-anywhere-else",
        CORS_ORIGINS: `http://localhost:${WEB_PORT}`,
      },
    },
    {
      command: `npx vite --port ${WEB_PORT} --strictPort`,
      cwd: here, // explicit: a config extending this one from another folder must still start Vite here
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: false,
      env: { VITE_API_URL: `http://127.0.0.1:${API_PORT}` },
    },
  ],
});
