import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { Plus } from "lucide-react";
import { createBusiness, listBusinesses, listMenus } from "../../api/endpoints";
import { PageHeader } from "../../app/AppShell";
import { queryKeys } from "../../app/queryKeys";
import { useDocumentTitle } from "../../app/useDocumentTitle";
import { Button } from "../../components/Button";
import { buttonClasses } from "../../components/buttonStyles";
import { EmptyState, ErrorState, LoadingList } from "../../components/States";
import { useToast } from "../../components/toastContext";
import { describeError } from "../../lib/errorMessages";
import { PICKUP_HOURS_DEFAULT } from "../../lib/limits";
import { BusinessForm } from "./BusinessForm";
import { PublicLink } from "./PublicLink";

export function BusinessesPage() {
  useDocumentTitle("Sucursales");
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const [creating, setCreating] = useState(false);

  const businesses = useQuery({ queryKey: queryKeys.businesses, queryFn: listBusinesses });
  // Only to show the menu name of each branch (the business only has menu_id)
  const menus = useQuery({ queryKey: queryKeys.menus, queryFn: listMenus });
  const menuName = (menuId: number | null | undefined) =>
    menuId == null ? null : menus.data?.find((menu) => menu.id === menuId)?.name ?? "Menú asignado";

  const create = async (values: Parameters<typeof createBusiness>[0]) => {
    const business = await createBusiness(values);
    await queryClient.invalidateQueries({ queryKey: queryKeys.businesses });
    setCreating(false);
    notify(`Creaste «${business.name}». Asignale un menú para que pueda recibir pedidos.`);
  };

  return (
    <>
      <PageHeader title="Sucursales">
        {!creating && (businesses.data?.length ?? 0) > 0 && (
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus aria-hidden="true" size={20} strokeWidth={1.75} />
            Nueva sucursal
          </Button>
        )}
      </PageHeader>

      {creating && (
        <section aria-labelledby="new-business" className="flex flex-col gap-4 rounded-lg border border-border bg-surface p-4">
          <h2 id="new-business" className="text-heading-2">Nueva sucursal</h2>
          <BusinessForm
            defaultValues={{ name: "", industry: "", pickup_timeout_hours: PICKUP_HOURS_DEFAULT }}
            submitLabel="Crear sucursal"
            onSubmit={create}
            onCancel={() => setCreating(false)}
          />
        </section>
      )}

      {businesses.isPending ? (
        <LoadingList label="Cargando sucursales" />
      ) : businesses.isError ? (
        <ErrorState message={describeError(businesses.error)} onRetry={() => businesses.refetch()} />
      ) : businesses.data.length === 0 ? (
        !creating && (
          <EmptyState
            title="Todavía no tenés sucursales"
            description="Cada sucursal tiene su propio enlace para que tus clientes hagan pedidos. Creá la primera para empezar."
            action={<Button variant="primary" onClick={() => setCreating(true)}>Crear la primera sucursal</Button>}
          />
        )
      ) : (
        <ul className="grid gap-6 lg:grid-cols-2">
          {businesses.data.map((business) => {
            const menu = menuName(business.menu_id);
            return (
              <li key={business.id} className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4">
                <div className="flex flex-col gap-1">
                  <h2 className="text-heading-2 break-words">{business.name}</h2>
                  <p className="text-body-sm text-ink-muted">
                    {business.industry} · Retiro en {business.pickup_timeout_hours} h
                  </p>
                  <p className="text-body-sm">
                    {menu ? (
                      <>Menú: <span className="font-semibold">{menu}</span></>
                    ) : (
                      <span className="text-ink-muted">Sin menú: su página pública todavía no recibe pedidos</span>
                    )}
                  </p>
                </div>
                <PublicLink slug={business.slug} />
                <Link to={`/negocios/${business.id}`} className={buttonClasses("secondary")}>
                  Ver y editar
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
