import { useCallback, useMemo, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { X } from "lucide-react";
import { cn } from "../lib/cn";
import { ToastContext, type ToastTone } from "./toastContext";

type ToastItem = { id: number; tone: ToastTone; message: string };
const DISMISS_MS = 5000;

// Short notices ("Enlace copiado", "Este pedido cambió de estado"). Announced by screen readers
// through an aria-live region that is always in the page.
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => setToasts((all) => all.filter((t) => t.id !== id)), []);

  const notify = useCallback(
    (message: string, tone: ToastTone = "info") => {
      const id = nextId.current++;
      setToasts((all) => [...all.slice(-2), { id, tone, message }]);
      window.setTimeout(() => dismiss(id), DISMISS_MS);
    },
    [dismiss],
  );

  const api = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-4 top-4 z-50 flex flex-col items-center gap-2">
        <AnimatePresence initial={false}>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className={cn(
                "pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-md border px-4 py-3 text-body shadow-md",
                toast.tone === "error"
                  ? "border-transparent bg-danger-soft text-danger-soft-ink"
                  : "border-border bg-surface text-ink",
              )}
            >
              <p className="flex-1">{toast.message}</p>
              <button
                type="button"
                aria-label="Cerrar aviso"
                onClick={() => dismiss(toast.id)}
                className="-m-1 rounded-sm p-1 transition-tint hover:bg-surface-sunken focus-ring"
              >
                <X aria-hidden="true" size={20} strokeWidth={1.75} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

