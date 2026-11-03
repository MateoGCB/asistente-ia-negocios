import { Link } from "react-router";
import { buttonClasses } from "../components/buttonStyles";
import { useDocumentTitle } from "./useDocumentTitle";

export function NotFoundPage() {
  useDocumentTitle("No encontramos eso");
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 px-4 py-12 text-center">
      <h1 className="text-display-md">No encontramos eso</h1>
      <p className="text-body text-ink-muted">Puede que el enlace esté mal escrito.</p>
      <Link to="/" className={buttonClasses("secondary")}>Ir al inicio</Link>
    </div>
  );
}
