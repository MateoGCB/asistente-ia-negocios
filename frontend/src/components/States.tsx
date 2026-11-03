import type { ReactNode } from "react";
import { AlertCircle, Info } from "lucide-react";
import { Button } from "./Button";
import { cn } from "../lib/cn";

// Loading placeholder: plain surface-sunken blocks, no shimmer animation
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("rounded-md bg-surface-sunken", className)} />;
}

export function LoadingList({ rows = 3, label = "Cargando" }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-label={label} className="flex flex-col gap-6">
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-24 rounded-lg" />
      ))}
    </div>
  );
}

// Empty state: what will appear here, and the action to create the first one
export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-border bg-surface px-4 py-12 text-center">
      <h2 className="text-heading-2">{title}</h2>
      <p className="max-w-md text-body text-ink-muted">{description}</p>
      {action}
    </div>
  );
}

// Error with a retry button (network errors and failed loads)
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-lg border border-border bg-surface p-4">
      <p className="flex items-start gap-2 text-body text-ink">
        <AlertCircle aria-hidden="true" size={20} strokeWidth={1.75} className="mt-0.5 flex-none text-danger" />
        {message}
      </p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    </div>
  );
}

// Inline message box. tone "danger" for errors the user must read (danger-soft background)
export function Alert({ tone = "info", children }: { tone?: "info" | "danger"; children: ReactNode }) {
  const Icon = tone === "danger" ? AlertCircle : Info;
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn(
        "flex items-start gap-2 rounded-md px-3 py-2 text-body-sm",
        tone === "danger" ? "bg-danger-soft text-danger-soft-ink" : "bg-accent-soft text-accent-soft-ink",
      )}
    >
      <Icon aria-hidden="true" size={20} strokeWidth={1.75} className="flex-none" />
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}
