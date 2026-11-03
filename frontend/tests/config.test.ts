import { afterEach, describe, expect, it, vi } from "vitest";

// config.ts reads VITE_API_URL when it is imported, so each case imports a fresh copy
async function loadConfig(apiUrl: string) {
  vi.stubEnv("VITE_API_URL", apiUrl);
  vi.resetModules();
  return import("../src/config");
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("config", () => {
  it("reads the provisional product name from one constant", async () => {
    expect((await loadConfig("")).APP_NAME).toBe("Comanda");
  });

  it("uses the local backend when VITE_API_URL is empty", async () => {
    expect((await loadConfig("")).API_URL).toBe("http://localhost:8000");
  });

  it("uses VITE_API_URL without trailing slashes", async () => {
    expect((await loadConfig("https://api.example.com//")).API_URL).toBe("https://api.example.com");
  });
});
