// Every failed request becomes an ApiError, so screens never parse HTTP responses themselves.

export type ApiErrorKind = "network" | "unauthorized" | "not_found" | "conflict" | "validation" | "http";

type ValidationItem = { loc?: (string | number)[]; msg?: string };

export class ApiError extends Error {
  readonly status: number; // 0 = no response (network error)
  readonly kind: ApiErrorKind;
  readonly detail: string | null; // the backend's own text, when it sent one
  readonly fieldErrors: Record<string, string>; // 422: "customer_phone" -> backend message

  constructor(status: number, kind: ApiErrorKind, detail: string | null, fieldErrors: Record<string, string> = {}) {
    super(detail ?? `Request failed (${status || "network"})`);
    this.name = "ApiError";
    this.status = status;
    this.kind = kind;
    this.detail = detail;
    this.fieldErrors = fieldErrors;
  }

  static network(): ApiError {
    return new ApiError(0, "network", null);
  }

  static fromResponse(status: number, body: unknown): ApiError {
    const kind: ApiErrorKind =
      status === 401 ? "unauthorized"
      : status === 404 ? "not_found"
      : status === 409 ? "conflict"
      : status === 422 ? "validation"
      : "http";
    const rawDetail = typeof body === "object" && body !== null ? (body as { detail?: unknown }).detail : undefined;

    // FastAPI sends a 422 either as a list (one entry per field) or, for business rules, as plain text
    if (Array.isArray(rawDetail)) {
      const fieldErrors: Record<string, string> = {};
      for (const item of rawDetail as ValidationItem[]) {
        // loc = ["body", "customer_phone"] or ["body", "items", 0, "quantity"] -> "customer_phone" / "items.0.quantity"
        const key = (item.loc ?? []).slice(1).join(".") || "_";
        if (!(key in fieldErrors)) fieldErrors[key] = item.msg ?? "";
      }
      return new ApiError(status, kind, null, fieldErrors);
    }
    return new ApiError(status, kind, typeof rawDetail === "string" ? rawDetail : null);
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}
