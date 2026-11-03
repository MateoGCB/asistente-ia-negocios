// Shown while the first screen is being downloaded (never a blank page)
export function RouteLoading() {
  return (
    <div role="status" aria-label="Cargando" className="mx-auto flex max-w-[480px] flex-col gap-4 px-4 py-12">
      <div className="h-8 w-1/2 rounded-md bg-surface-sunken" />
      <div className="h-24 rounded-lg bg-surface-sunken" />
    </div>
  );
}
