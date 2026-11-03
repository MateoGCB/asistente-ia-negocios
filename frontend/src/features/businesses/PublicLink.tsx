import { Copy, ExternalLink } from "lucide-react";
import { Button } from "../../components/Button";
import { buttonClasses } from "../../components/buttonStyles";
import { useToast } from "../../components/toastContext";
import { publicUrl } from "./businessSchema";

// The branch's public ordering link, with "copy" and "open" actions
export function PublicLink({ slug }: { slug: string }) {
  const { notify } = useToast();
  const url = publicUrl(slug);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      notify("Enlace copiado. Pegalo donde quieras compartirlo.");
    } catch {
      notify("No pudimos copiar el enlace. Seleccionalo y copialo a mano.", "error");
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <span className="break-all text-data-sm text-ink-muted">{url}</span>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={copy}>
          <Copy aria-hidden="true" size={20} strokeWidth={1.75} />
          Copiar enlace
        </Button>
        <a href={url} target="_blank" rel="noreferrer" className={buttonClasses("ghost")}>
          <ExternalLink aria-hidden="true" size={20} strokeWidth={1.75} />
          Abrir página pública
        </a>
      </div>
    </div>
  );
}
