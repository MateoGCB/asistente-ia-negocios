import { QueryClient } from "@tanstack/react-query";
import { isApiError } from "../api/errors";

// Retry once only on network errors: a 404, 409 or 422 will not change by asking again
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => isApiError(error) && error.kind === "network" && failureCount < 1,
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  });
}
