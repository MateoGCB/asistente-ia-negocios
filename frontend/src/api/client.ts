import { API_URL } from "../config";
import { ApiError } from "./errors";
import { clearSession, getToken } from "./session";

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  // auth=false for public endpoints and login/register: no token is sent and a 401 is not "session expired"
  auth?: boolean;
  query?: Record<string, string | number | undefined>;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true, query } = options;
  const token = auth ? getToken() : null;

  const url = new URL(API_URL + path);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined) url.searchParams.set(key, String(value));
  }

  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw ApiError.network();
  }

  const data: unknown = await response.json().catch(() => null);

  if (response.status === 401 && auth) {
    // Expired or invalid token: forget it. The protected routes react and go to /login.
    clearSession({ expired: token !== null });
  }
  if (!response.ok) {
    throw ApiError.fromResponse(response.status, data);
  }
  return data as T;
}
