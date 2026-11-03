import { isApiError } from "../api/errors";

// Generic, user-facing text for an error that a screen does not handle in a specific way.
// Never shows technical codes; says what happened and what to do.
export function describeError(error: unknown): string {
  if (!isApiError(error)) return "Algo salió mal. Probá de nuevo.";
  switch (error.kind) {
    case "network":
      return "No pudimos conectarnos con el servidor. Revisá tu conexión y probá de nuevo.";
    case "unauthorized":
      return "Tu sesión venció. Ingresá de nuevo.";
    case "not_found":
      return "No encontramos eso. Puede que se haya borrado.";
    case "conflict":
      return "No se pudo completar porque los datos cambiaron. Actualizá y probá de nuevo.";
    case "validation":
      return "Revisá los datos marcados y probá de nuevo.";
    default:
      return "El servidor no pudo completar la acción. Probá de nuevo en unos minutos.";
  }
}
