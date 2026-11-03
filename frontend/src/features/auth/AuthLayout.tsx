import type { ReactNode } from "react";
import { APP_NAME } from "../../config";

// Centered card for /login and /registro, with generous air around it
export function AuthLayout({ title, children, footer }: { title: string; children: ReactNode; footer: ReactNode }) {
  return (
    <div className="min-h-dvh bg-surface-page px-4 py-12 text-ink">
      <main className="mx-auto flex w-full max-w-[420px] flex-col gap-6">
        <p className="text-display-md">{APP_NAME}</p>
        <div className="flex flex-col gap-6 rounded-lg border border-border bg-surface p-6">
          <h1 className="text-heading-1">{title}</h1>
          {children}
        </div>
        <p className="text-center text-body text-ink-muted">{footer}</p>
      </main>
    </div>
  );
}

export const linkClasses = "font-semibold text-accent underline-offset-2 hover:underline focus-ring rounded-sm";
