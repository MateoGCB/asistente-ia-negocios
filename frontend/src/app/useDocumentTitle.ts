import { useEffect } from "react";
import { APP_NAME } from "../config";

export function useDocumentTitle(title: string | null): void {
  useEffect(() => {
    document.title = title ? `${title} · ${APP_NAME}` : APP_NAME;
  }, [title]);
}
