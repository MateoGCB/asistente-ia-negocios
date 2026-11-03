import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { vi } from "vitest";
import { Providers } from "../src/app/Providers";
import { createQueryClient } from "../src/app/queryClient";
import { routes } from "../src/app/routes";

type FakeResponse = { status: number; body?: unknown };
type Handler = (url: URL, init: RequestInit | undefined) => FakeResponse | undefined;

// Replaces fetch: each call goes to `handler`; an unhandled call answers 500 so it is noticed.
// Returns the mock to inspect the calls (URL, method, headers, body).
export function mockFetch(handler: Handler) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(input instanceof Request ? input.url : String(input));
    const answer = handler(url, init) ?? { status: 500, body: { detail: `unhandled ${init?.method ?? "GET"} ${url.pathname}` } };
    return new Response(answer.body === undefined ? null : JSON.stringify(answer.body), {
      status: answer.status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

// Renders the real app (same routes as production) starting at `path`
export function renderApp(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const queryClient = createQueryClient();
  queryClient.setDefaultOptions({ queries: { retry: false } });
  const utils = render(
    <Providers queryClient={queryClient}>
      <RouterProvider router={router} />
    </Providers>,
  );
  return { ...utils, router };
}
