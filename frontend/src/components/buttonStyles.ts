import { cn } from "../lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
// md: panel (40px). lg: main public action (48px). touch / icon: public touch targets of 44px
// (icon is a 44px square). Sizes are explicit so callers never override conflicting classes.
export type ButtonSize = "md" | "lg" | "touch" | "icon";

const SIZE: Record<ButtonSize, string> = {
  md: "min-h-10 px-4 text-[14px] leading-5",
  lg: "min-h-12 px-6 text-[16px] leading-6",
  touch: "min-h-11 px-4 text-[14px] leading-5",
  icon: "size-11 text-[14px] leading-5",
};

// Each variant sets its OWN border color. A shared "border-transparent" in the base classes would
// fight with "border-border-control": in Tailwind the winner is decided by the order of the generated
// CSS, not by the order in className, so secondary buttons lost their border.
const VARIANT: Record<ButtonVariant, string> = {
  primary: "border-transparent bg-accent text-on-accent hover:bg-accent-hover",
  secondary: "border-border-control bg-surface text-ink hover:bg-surface-sunken",
  ghost: "border-transparent bg-transparent text-ink hover:bg-surface-sunken",
  danger: "border-transparent bg-danger text-on-danger hover:brightness-[.92]",
};

// Panel: 40px high. Public page: lg (48px) and usually block, so the thumb reaches it.
export function buttonClasses(variant: ButtonVariant = "secondary", size: ButtonSize = "md", block = false): string {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-md border font-semibold no-underline",
    "cursor-pointer transition-tint focus-ring",
    SIZE[size],
    block && "flex w-full",
    VARIANT[variant],
    "disabled:cursor-not-allowed disabled:border-border disabled:bg-surface-sunken disabled:text-ink-subtle",
    "disabled:hover:bg-surface-sunken disabled:hover:brightness-100",
  );
}
