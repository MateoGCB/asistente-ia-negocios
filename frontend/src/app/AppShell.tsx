import type { ReactNode } from "react";
import { NavLink, Outlet, useNavigate } from "react-router";
import { ClipboardList, LogOut, Store, UtensilsCrossed, type LucideIcon } from "lucide-react";
import { APP_NAME } from "../config";
import { cn } from "../lib/cn";

const LINKS: { to: string; label: string; icon: LucideIcon }[] = [
  { to: "/pedidos", label: "Pedidos", icon: ClipboardList },
  { to: "/negocios", label: "Sucursales", icon: Store },
  { to: "/menus", label: "Menús", icon: UtensilsCrossed },
];

const linkClasses = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex min-h-10 flex-none items-center gap-3 rounded-md px-3 text-[14px] font-semibold leading-5 no-underline transition-tint focus-ring",
    isActive ? "bg-accent-soft text-accent-soft-ink" : "text-ink-muted hover:bg-surface-sunken hover:text-ink",
  );

// Owner panel layout. Desktop (1024px+): 240px sidebar + content up to 1120px.
// Below 1024px the sidebar becomes a top row with horizontal scroll and the name is hidden.
export function AppShell() {
  const navigate = useNavigate();

  // Logging out goes through /salir (see Logout in guards.tsx). When the session EXPIRES instead,
  // RequireAuth remembers the page to come back to it after logging in again.
  const logout = () => navigate("/salir");

  return (
    // Below 1024px: two rows, the nav takes only its height (auto) and the content the rest (1fr).
    // Without it, a short page stretched the nav row to fill the screen.
    <div className="grid min-h-dvh grid-rows-[auto_1fr] bg-surface-page text-ink lg:grid-cols-[240px_1fr] lg:grid-rows-1">
      <nav
        aria-label="Panel"
        className="flex gap-1 overflow-x-auto border-b border-border bg-surface p-4 lg:flex-col lg:overflow-visible lg:border-r lg:border-b-0"
      >
        <span className="hidden px-3 pt-2 pb-4 text-[20px] font-bold leading-6 tracking-[-0.01em] lg:block">{APP_NAME}</span>
        {LINKS.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={linkClasses}>
            <Icon aria-hidden="true" size={20} strokeWidth={1.75} />
            {label}
          </NavLink>
        ))}
        <button
          type="button"
          onClick={logout}
          className="flex min-h-10 flex-none cursor-pointer items-center gap-3 rounded-md px-3 text-[14px] font-semibold leading-5 text-ink-muted transition-tint hover:bg-surface-sunken hover:text-ink focus-ring lg:mt-auto"
        >
          <LogOut aria-hidden="true" size={20} strokeWidth={1.75} />
          Cerrar sesión
        </button>
      </nav>
      <main className="flex w-full min-w-0 max-w-[1120px] flex-col gap-6 p-4 lg:p-8">
        <Outlet />
      </main>
    </div>
  );
}

// Screen title + optional actions on the right
export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-display-md">{title}</h1>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  );
}
