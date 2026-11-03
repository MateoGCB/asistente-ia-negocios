import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { isApiError } from "../api/errors";

// Marks the form fields that the backend rejected (422). The backend messages are technical and in
// English, so each field shows its own Spanish message instead. Returns true if any field was marked.
export function applyServerFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  messages: Partial<Record<Path<T>, string>>,
): boolean {
  if (!isApiError(error) || error.kind !== "validation") return false;
  let applied = false;
  for (const key of Object.keys(error.fieldErrors)) {
    const field = key.split(".")[0] as Path<T>;
    const message = messages[field];
    if (message) {
      setError(field, { type: "server", message });
      applied = true;
    }
  }
  return applied;
}
