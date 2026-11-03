import { useDocumentTitle } from "../../app/useDocumentTitle";

// One single screen for an unknown slug, an archived branch and a branch without menu
export function UnavailableScreen() {
  useDocumentTitle("Local no disponible");
  return (
    <div className="flex flex-col gap-3 py-12 text-center">
      <h1 className="text-display-md">Este local no está disponible</h1>
      <p className="text-body text-ink-muted">
        Puede que el enlace esté mal escrito o que el local ya no reciba pedidos online. Pedile al local su enlace actualizado.
      </p>
    </div>
  );
}
