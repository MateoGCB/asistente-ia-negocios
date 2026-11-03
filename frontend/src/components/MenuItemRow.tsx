import type { ReactNode } from "react";
import { formatPrice } from "../lib/money";
import { cn } from "../lib/cn";

type MenuItemRowProps = {
  name: string;
  description: string;
  price: string;
  available?: boolean;
  // Right side: quantity control (public page) or Editar / Quitar (owner editor)
  children?: ReactNode;
};

// A sold-out item (owner editor) is struck through and says "Agotado". The public page never
// receives sold-out items: the public API filters them out (decision: they are hidden there).
export function MenuItemRow({ name, description, price, available = true, children }: MenuItemRowProps) {
  return (
    <li className="flex flex-col gap-3 border-b border-border bg-surface p-4 last:border-b-0 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <div className="min-w-0 flex-1">
        <h3 className={cn("text-heading-3 break-words", available ? "text-ink" : "text-ink-muted line-through")}>{name}</h3>
        <p className="mt-0.5 break-words text-body-sm text-ink-muted">{description}</p>
        {!available && <span className="mt-1 inline-block text-[12px] font-semibold leading-4 text-ink-muted">Agotado</span>}
      </div>
      <div className="flex flex-wrap items-center gap-3 sm:justify-end">
        <span className={cn("whitespace-nowrap text-price", available ? "text-ink" : "text-ink-muted line-through")}>
          {formatPrice(price)}
        </span>
        {children}
      </div>
    </li>
  );
}
