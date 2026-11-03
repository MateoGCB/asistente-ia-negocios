import { Outlet } from "react-router";

// Customer pages: one centered column of 480px max, mobile first. The bottom padding (88px)
// keeps the fixed CartBar from covering the last item.
export function PublicLayout() {
  return (
    <div className="min-h-dvh bg-surface-page text-ink">
      <main className="mx-auto flex w-full max-w-[480px] flex-col gap-6 px-4 pt-6 pb-[calc(88px+env(safe-area-inset-bottom))]">
        <Outlet />
      </main>
    </div>
  );
}
