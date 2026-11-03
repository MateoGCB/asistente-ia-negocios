import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { ArrowLeft } from "lucide-react";
import { createMenuItem, deleteMenuItem, listMenuItems, listMenus, updateMenuItem } from "../../api/endpoints";
import { isApiError } from "../../api/errors";
import type { MenuItem } from "../../api/types";
import { PageHeader } from "../../app/AppShell";
import { queryKeys } from "../../app/queryKeys";
import { useDocumentTitle } from "../../app/useDocumentTitle";
import { Button } from "../../components/Button";
import { buttonClasses } from "../../components/buttonStyles";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { MenuItemRow } from "../../components/MenuItemRow";
import { Alert, EmptyState, ErrorState, LoadingList } from "../../components/States";
import { useToast } from "../../components/toastContext";
import { CATEGORY_LABEL, groupByCategory } from "../../lib/categories";
import { describeError } from "../../lib/errorMessages";
import { formatPrice } from "../../lib/money";
import { ItemForm, type ItemPayload } from "./ItemForm";

const backLink = (
  <Link to="/menus" className={buttonClasses("ghost")}>
    <ArrowLeft aria-hidden="true" size={20} strokeWidth={1.75} />
    Volver a menús
  </Link>
);

// "3500.50" -> "3500,50": how the owner edits an existing price
const priceForInput = (price: string) => price.replace(/\.00$/, "").replace(".", ",");

export function MenuEditorPage() {
  const menuId = Number(useParams().id);
  const valid = Number.isInteger(menuId) && menuId > 0;
  const queryClient = useQueryClient();
  const { notify } = useToast();

  // There is no GET /menus/{id}: the name comes from the list of my menus
  const menus = useQuery({ queryKey: queryKeys.menus, queryFn: listMenus });
  const items = useQuery({ queryKey: queryKeys.menuItems(menuId), queryFn: () => listMenuItems(menuId), enabled: valid });
  const menu = menus.data?.find((m) => m.id === menuId);
  useDocumentTitle(menu?.name ?? "Menú");

  const [editing, setEditing] = useState<MenuItem | null>(null);
  const [toDelete, setToDelete] = useState<MenuItem | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [deleteBlocked, setDeleteBlocked] = useState<string | null>(null);

  const refresh = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: queryKeys.menuItems(menuId) }),
    queryClient.invalidateQueries({ queryKey: queryKeys.menus }), // items_count changes
  ]);

  const notFound = !valid
    || (items.isError && isApiError(items.error) && items.error.kind === "not_found")
    || (menus.isSuccess && !menu);
  if (notFound) {
    return (
      <>
        <div>{backLink}</div>
        <EmptyState title="No encontramos ese menú" description="Puede que lo hayas borrado o que el enlace esté mal escrito." />
      </>
    );
  }
  if (items.isPending || menus.isPending) return <LoadingList rows={4} label="Cargando menú" />;
  if (items.isError) return <ErrorState message={describeError(items.error)} onRetry={() => items.refetch()} />;
  if (menus.isError) return <ErrorState message={describeError(menus.error)} onRetry={() => menus.refetch()} />;

  const add = async (payload: ItemPayload) => {
    await createMenuItem(menuId, payload);
    await refresh();
    notify(`Agregaste «${payload.name}».`);
  };

  const saveEdit = async (payload: ItemPayload) => {
    if (!editing) return;
    await updateMenuItem(menuId, editing.id, payload);
    setEditing(null);
    await refresh();
    notify("Guardamos el plato.");
  };

  const toggleAvailable = async (item: MenuItem) => {
    setBusyId(item.id);
    try {
      await updateMenuItem(menuId, item.id, { available: !item.available });
      await refresh();
      notify(item.available ? `«${item.name}» quedó agotado: no se puede pedir.` : `«${item.name}» se puede pedir de nuevo.`);
    } catch (error) {
      notify(describeError(error), "error");
    } finally {
      setBusyId(null);
    }
  };

  const confirmDelete = async () => {
    if (!toDelete) return;
    const item = toDelete;
    setBusyId(item.id);
    try {
      await deleteMenuItem(menuId, item.id);
      setDeleteBlocked(null);
      notify(`Quitaste «${item.name}».`);
    } catch (error) {
      if (isApiError(error) && error.kind === "conflict") setDeleteBlocked(item.name); // it appears in orders
      else notify(describeError(error), "error");
    } finally {
      setBusyId(null);
      setToDelete(null);
      await refresh();
    }
  };

  const groups = groupByCategory(items.data);
  const card = "flex flex-col gap-4 rounded-lg border border-border bg-surface p-4";

  return (
    <>
      <div>{backLink}</div>
      <PageHeader title={menu?.name ?? "Menú"} />

      {deleteBlocked && (
        <Alert tone="danger">
          «{deleteBlocked}» figura en pedidos que ya recibiste, así que no se puede borrar. Marcalo como agotado para
          que nadie lo pueda pedir.
        </Alert>
      )}

      <section aria-labelledby="new-item" className={card}>
        <h2 id="new-item" className="text-heading-2">Agregar un plato</h2>
        <ItemForm
          defaultValues={{ name: "", description: "", price: "", category: "plato_principal" }}
          submitLabel="Agregar plato"
          onSubmit={add}
        />
      </section>

      {editing && (
        <section aria-labelledby="edit-item" className={card}>
          <h2 id="edit-item" className="text-heading-2">Editar «{editing.name}»</h2>
          <ItemForm
            key={editing.id}
            defaultValues={{ name: editing.name, description: editing.description, price: priceForInput(editing.price), category: editing.category }}
            submitLabel="Guardar plato"
            onSubmit={saveEdit}
            onCancel={() => setEditing(null)}
          />
        </section>
      )}

      {groups.length === 0 ? (
        <EmptyState title="Este menú todavía no tiene platos" description="Los platos que agregues arriba aparecen acá, agrupados por categoría." />
      ) : (
        groups.map((group) => (
          <section key={group.category} aria-labelledby={`cat-${group.category}`} className="flex flex-col gap-3">
            <h2 id={`cat-${group.category}`} className="text-heading-2">{CATEGORY_LABEL[group.category]}</h2>
            <ul className="overflow-hidden rounded-lg border border-border">
              {group.items.map((item) => (
                <MenuItemRow key={item.id} name={item.name} description={item.description} price={item.price} available={item.available}>
                  <div className="flex flex-wrap gap-1">
                    <Button variant="ghost" onClick={() => setEditing(item)} aria-label={`Editar ${item.name}`}>Editar</Button>
                    <Button variant="ghost" onClick={() => toggleAvailable(item)} disabled={busyId === item.id}>
                      {item.available ? "Marcar agotado" : "Marcar disponible"}
                    </Button>
                    <Button variant="ghost" onClick={() => setToDelete(item)} disabled={busyId === item.id} aria-label={`Quitar ${item.name}`}>Quitar</Button>
                  </div>
                </MenuItemRow>
              ))}
            </ul>
          </section>
        ))
      )}

      <ConfirmDialog
        open={toDelete !== null}
        title={`¿Quitar «${toDelete?.name ?? ""}»?`}
        confirmLabel="Quitar plato"
        busy={busyId !== null}
        onConfirm={confirmDelete}
        onCancel={() => setToDelete(null)}
      >
        El plato se borra del menú ({toDelete ? formatPrice(toDelete.price) : ""}). Si ya figura en pedidos no se
        puede borrar: en ese caso marcalo como agotado.
      </ConfirmDialog>
    </>
  );
}
