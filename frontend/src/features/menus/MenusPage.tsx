import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { z } from "zod";
import { createMenu, deleteMenu, listMenus } from "../../api/endpoints";
import { isApiError } from "../../api/errors";
import type { MenuSummary } from "../../api/types";
import { PageHeader } from "../../app/AppShell";
import { queryKeys } from "../../app/queryKeys";
import { useDocumentTitle } from "../../app/useDocumentTitle";
import { Button } from "../../components/Button";
import { buttonClasses } from "../../components/buttonStyles";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Alert, EmptyState, ErrorState, LoadingList } from "../../components/States";
import { TextField } from "../../components/TextField";
import { useToast } from "../../components/toastContext";
import { describeError } from "../../lib/errorMessages";
import { applyServerFieldErrors } from "../../lib/formErrors";
import { MENU_NAME_MAX } from "../../lib/limits";

const menuSchema = z.object({
  name: z.string().trim().min(1, "Escribí un nombre para el menú").max(MENU_NAME_MAX, `Usá como máximo ${MENU_NAME_MAX} caracteres`),
});
type MenuValues = z.infer<typeof menuSchema>;

function NewMenuForm({ onCreated }: { onCreated: (menuId: number) => void }) {
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } = useForm<MenuValues>({
    resolver: zodResolver(menuSchema),
    defaultValues: { name: "" },
  });

  const submit = handleSubmit(async ({ name }) => {
    setFormError(null);
    try {
      const menu = await createMenu(name);
      reset();
      onCreated(menu.id);
    } catch (error) {
      if (!applyServerFieldErrors(error, setError, { name: `El nombre necesita entre 1 y ${MENU_NAME_MAX} caracteres` })) {
        setFormError(describeError(error));
      }
    }
  });

  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4">
      {formError && <Alert tone="danger">{formError}</Alert>}
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[240px] flex-1">
          <TextField label="Nombre del menú nuevo" placeholder="Carta de mediodía" maxLength={MENU_NAME_MAX} error={errors.name?.message} {...register("name")} />
        </div>
        <Button type="submit" variant="primary" disabled={isSubmitting}>Crear menú</Button>
      </div>
    </form>
  );
}

export function MenusPage() {
  useDocumentTitle("Menús");
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useToast();
  const menus = useQuery({ queryKey: queryKeys.menus, queryFn: listMenus });
  const [toDelete, setToDelete] = useState<MenuSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [inUse, setInUse] = useState<string | null>(null);

  const onCreated = async (menuId: number) => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.menus });
    notify("Creaste el menú. Ahora agregale platos.");
    navigate(`/menus/${menuId}`);
  };

  const confirmDelete = async () => {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await deleteMenu(toDelete.id);
      notify(`Borraste «${toDelete.name}».`);
      setInUse(null);
    } catch (error) {
      if (isApiError(error) && error.kind === "conflict") {
        // 409: an active branch uses it. Explain why and how to solve it.
        setInUse(toDelete.name);
      } else {
        notify(describeError(error), "error");
      }
    } finally {
      setDeleting(false);
      setToDelete(null);
      await queryClient.invalidateQueries({ queryKey: queryKeys.menus });
    }
  };

  return (
    <>
      <PageHeader title="Menús" />
      {inUse && (
        <Alert tone="danger">
          <span>
            No pudimos borrar «{inUse}» porque lo usa al menos una sucursal activa. Quitáselo desde el detalle
            de cada sucursal (botón «Quitar menú») y probá de nuevo.
          </span>
          <Link to="/negocios" className="font-semibold underline underline-offset-2 focus-ring">Ir a sucursales</Link>
        </Alert>
      )}
      <NewMenuForm onCreated={onCreated} />

      {menus.isPending ? (
        <LoadingList label="Cargando menús" />
      ) : menus.isError ? (
        <ErrorState message={describeError(menus.error)} onRetry={() => menus.refetch()} />
      ) : menus.data.length === 0 ? (
        <EmptyState
          title="Todavía no tenés menús"
          description="Un menú agrupa los platos que ofrecés. Podés usar el mismo menú en varias sucursales. Escribí un nombre arriba para crear el primero."
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {menus.data.map((menu) => (
            <li key={menu.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-surface p-4">
              <div className="min-w-0">
                <h2 className="text-heading-3 break-words">{menu.name}</h2>
                <p className="text-body-sm text-ink-muted">
                  {menu.items_count === 0 ? "Sin platos" : `${menu.items_count} ${menu.items_count === 1 ? "plato" : "platos"}`}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link to={`/menus/${menu.id}`} className={buttonClasses("secondary")}>Editar platos</Link>
                <Button variant="ghost" onClick={() => setToDelete(menu)}>Borrar</Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={toDelete !== null}
        title={`¿Borrar «${toDelete?.name ?? ""}»?`}
        confirmLabel="Borrar menú"
        busy={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setToDelete(null)}
      >
        Se borran el menú y todos sus platos. Los pedidos que ya recibiste no cambian. Si alguna sucursal activa lo
        usa, no se va a poder borrar.
      </ConfirmDialog>
    </>
  );
}
