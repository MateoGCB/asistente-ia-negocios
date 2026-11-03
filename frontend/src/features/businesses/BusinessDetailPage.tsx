import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router";
import { ArrowLeft } from "lucide-react";
import { archiveBusiness, getBusiness, listMenus, removeBusinessMenu, updateBusiness } from "../../api/endpoints";
import { isApiError } from "../../api/errors";
import type { Business } from "../../api/types";
import { PageHeader } from "../../app/AppShell";
import { queryKeys } from "../../app/queryKeys";
import { useDocumentTitle } from "../../app/useDocumentTitle";
import { Button } from "../../components/Button";
import { buttonClasses } from "../../components/buttonStyles";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Alert, EmptyState, ErrorState, LoadingList } from "../../components/States";
import { SelectField } from "../../components/TextField";
import { useToast } from "../../components/toastContext";
import { describeError } from "../../lib/errorMessages";
import { BusinessForm } from "./BusinessForm";
import type { BusinessValues } from "./businessSchema";
import { PublicLink } from "./PublicLink";

const backLink = (
  <Link to="/negocios" className={buttonClasses("ghost")}>
    <ArrowLeft aria-hidden="true" size={20} strokeWidth={1.75} />
    Volver a sucursales
  </Link>
);

export function BusinessDetailPage() {
  const businessId = Number(useParams().id);
  const valid = Number.isInteger(businessId) && businessId > 0;
  const business = useQuery({ queryKey: queryKeys.business(businessId), queryFn: () => getBusiness(businessId), enabled: valid });
  useDocumentTitle(business.data?.name ?? "Sucursal");

  if (!valid || (business.isError && isApiError(business.error) && business.error.kind === "not_found")) {
    return (
      <>
        {backLink}
        <EmptyState title="No encontramos esa sucursal" description="Puede que la hayas archivado o que el enlace esté mal escrito." />
      </>
    );
  }
  if (business.isPending) return <LoadingList rows={3} label="Cargando sucursal" />;
  if (business.isError) return <ErrorState message={describeError(business.error)} onRetry={() => business.refetch()} />;
  return <BusinessDetail business={business.data} />;
}

function BusinessDetail({ business }: { business: Business }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useToast();
  const menus = useQuery({ queryKey: queryKeys.menus, queryFn: listMenus });
  const [selectedMenu, setSelectedMenu] = useState<string>(business.menu_id ? String(business.menu_id) : "");
  const [menuBusy, setMenuBusy] = useState(false);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [archiving, setArchiving] = useState(false);

  const refresh = async (updated?: Business) => {
    if (updated) queryClient.setQueryData(queryKeys.business(business.id), updated);
    await queryClient.invalidateQueries({ queryKey: queryKeys.businesses });
  };

  const save = async (values: BusinessValues) => {
    await refresh(await updateBusiness(business.id, values));
    notify("Guardamos los cambios de la sucursal.");
  };

  const assignMenu = async () => {
    setMenuBusy(true);
    try {
      await refresh(await updateBusiness(business.id, { menu_id: Number(selectedMenu) }));
      notify("Asignamos el menú. La página pública ya muestra esos platos.");
    } catch (error) {
      notify(describeError(error), "error");
    } finally {
      setMenuBusy(false);
    }
  };

  const removeMenu = async () => {
    setMenuBusy(true);
    try {
      await removeBusinessMenu(business.id);
      await refresh({ ...business, menu_id: null });
      setSelectedMenu("");
      notify("Quitamos el menú. La página pública deja de recibir pedidos hasta que asignes otro.");
    } catch (error) {
      notify(describeError(error), "error");
    } finally {
      setMenuBusy(false);
    }
  };

  const archive = async () => {
    setArchiving(true);
    try {
      await archiveBusiness(business.id);
      queryClient.removeQueries({ queryKey: queryKeys.business(business.id) });
      await queryClient.invalidateQueries({ queryKey: queryKeys.businesses });
      notify(`Archivaste «${business.name}».`);
      navigate("/negocios", { replace: true });
    } catch (error) {
      setArchiving(false);
      setConfirmArchive(false);
      notify(describeError(error), "error");
    }
  };

  const currentMenu = menus.data?.find((menu) => menu.id === business.menu_id);
  const cardClasses = "flex flex-col gap-4 rounded-lg border border-border bg-surface p-4";

  return (
    <>
      <div>{backLink}</div>
      <PageHeader title={business.name} />

      <section aria-labelledby="data" className={cardClasses}>
        <h2 id="data" className="text-heading-2">Datos de la sucursal</h2>
        <BusinessForm
          key={`${business.name}|${business.industry}|${business.pickup_timeout_hours}`}
          defaultValues={{ name: business.name, industry: business.industry, pickup_timeout_hours: business.pickup_timeout_hours }}
          submitLabel="Guardar cambios"
          onSubmit={save}
        />
      </section>

      <section aria-labelledby="menu" className={cardClasses}>
        <h2 id="menu" className="text-heading-2">Menú</h2>
        {business.menu_id == null ? (
          <Alert>Esta sucursal no tiene menú, así que su página pública muestra «Este local no está disponible».</Alert>
        ) : (
          <p className="text-body">
            Menú actual: <span className="font-semibold">{currentMenu?.name ?? "cargando..."}</span>
          </p>
        )}
        {menus.isError ? (
          <ErrorState message={describeError(menus.error)} onRetry={() => menus.refetch()} />
        ) : menus.data && menus.data.length === 0 ? (
          <p className="text-body text-ink-muted">
            Todavía no tenés menús. <Link to="/menus" className="font-semibold text-accent underline-offset-2 hover:underline focus-ring">Creá uno</Link> y volvé para asignarlo.
          </p>
        ) : (
          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-[240px] flex-1">
              <SelectField label="Elegí un menú" value={selectedMenu} onChange={(e) => setSelectedMenu(e.target.value)} disabled={!menus.data}>
                <option value="" disabled>Seleccioná un menú</option>
                {menus.data?.map((menu) => (
                  <option key={menu.id} value={menu.id}>
                    {menu.name} ({menu.items_count} {menu.items_count === 1 ? "plato" : "platos"})
                  </option>
                ))}
              </SelectField>
            </div>
            <Button
              variant="secondary"
              onClick={assignMenu}
              disabled={menuBusy || selectedMenu === "" || Number(selectedMenu) === business.menu_id}
            >
              {business.menu_id == null ? "Asignar menú" : "Cambiar menú"}
            </Button>
            {business.menu_id != null && (
              <Button variant="ghost" onClick={removeMenu} disabled={menuBusy}>
                Quitar menú
              </Button>
            )}
          </div>
        )}
      </section>

      <section aria-labelledby="link" className={cardClasses}>
        <h2 id="link" className="text-heading-2">Enlace para tus clientes</h2>
        <PublicLink slug={business.slug} />
      </section>

      <section aria-labelledby="archive" className={cardClasses}>
        <h2 id="archive" className="text-heading-2">Archivar sucursal</h2>
        <p className="text-body text-ink-muted">
          La sucursal deja de recibir pedidos y su enlace público deja de funcionar. Sus pedidos se conservan.
        </p>
        <div>
          <Button variant="danger" onClick={() => setConfirmArchive(true)}>Archivar sucursal</Button>
        </div>
      </section>

      <ConfirmDialog
        open={confirmArchive}
        title={`¿Archivar «${business.name}»?`}
        confirmLabel="Archivar sucursal"
        busy={archiving}
        onConfirm={archive}
        onCancel={() => setConfirmArchive(false)}
      >
        Deja de recibir pedidos, desaparece de tu lista y su enlace público deja de funcionar. Los pedidos se
        conservan. Por ahora no se puede deshacer desde el panel.
      </ConfirmDialog>
    </>
  );
}
