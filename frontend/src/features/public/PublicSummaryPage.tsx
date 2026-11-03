import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, useNavigate, useParams } from "react-router";
import { ArrowLeft } from "lucide-react";
import { createPublicOrder } from "../../api/endpoints";
import { isApiError } from "../../api/errors";
import { queryKeys } from "../../app/queryKeys";
import { useDocumentTitle } from "../../app/useDocumentTitle";
import { Button } from "../../components/Button";
import { buttonClasses } from "../../components/buttonStyles";
import { Alert, ErrorState, LoadingList } from "../../components/States";
import { TextAreaField, TextField } from "../../components/TextField";
import { useToast } from "../../components/toastContext";
import { describeError } from "../../lib/errorMessages";
import { applyServerFieldErrors } from "../../lib/formErrors";
import { CUSTOMER_NAME_MAX, NOTES_MAX, ORDER_TOTAL_MAX_CENTS, PHONE_MAX_LENGTH } from "../../lib/limits";
import { formatCents } from "../../lib/money";
import { cartTotalCents, saveCart } from "./cart";
import { saveLastOrder } from "./lastOrder";
import { ORDER_SERVER_MESSAGES, orderFormSchema, type OrderFormValues } from "./orderForm";
import { UnavailableScreen } from "./UnavailableScreen";
import { useCart } from "./useCart";
import { usePublicMenu } from "./usePublicMenu";

export function PublicSummaryPage() {
  useDocumentTitle("Confirmá tu pedido");
  const slug = useParams().slug ?? "";
  const menu = usePublicMenu(slug);
  const [cart] = useCart(slug);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const [formError, setFormError] = useState<string | null>(null);

  const { register, handleSubmit, setError, control, formState: { errors, isSubmitting } } = useForm<OrderFormValues>({
    resolver: zodResolver(orderFormSchema),
    defaultValues: { customer_name: "", customer_phone: "", notes: "" },
  });
  const notes = useWatch({ control, name: "notes" });

  if (menu.unavailable) return <UnavailableScreen />;
  if (menu.isPending) return <LoadingList rows={3} label="Cargando tu pedido" />;
  if (menu.isError) return <ErrorState message={describeError(menu.error)} onRetry={() => menu.refetch()} />;

  const itemsById = new Map(menu.data.items.map((item) => [item.id, item]));
  const lines = cart.filter((line) => itemsById.has(line.itemId));
  if (lines.length === 0) return <Navigate to={`/pedir/${slug}`} replace />;

  // Display only: the backend computes the real total with its current prices
  const totalCents = cartTotalCents(lines, menu.priceCents);
  const overLimit = totalCents > ORDER_TOTAL_MAX_CENTS;

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const order = await createPublicOrder(slug, {
        customer_name: values.customer_name,
        customer_phone: values.customer_phone.trim(),
        notes: values.notes || null,
        items: lines.map((line) => ({ menu_item_id: line.itemId, quantity: line.qty })),
      });
      saveLastOrder(slug, order);
      // Empty the SAVED cart and leave. Not dispatch({type:"clear"}): this screen would re-render with an
      // empty cart and its own <Navigate> back to the menu would win over the navigation to /listo.
      saveCart(slug, []);
      navigate(`/pedir/${slug}/listo`, { replace: true });
    } catch (error) {
      if (isApiError(error) && error.kind === "conflict") {
        // Some item stopped being available: reload the menu (the cart drops the missing items)
        notify("Alguno de los platos ya no está disponible. Revisá tu pedido y probá de nuevo.", "error");
        await queryClient.invalidateQueries({ queryKey: queryKeys.publicMenu(slug) });
        navigate(`/pedir/${slug}`);
        return;
      }
      if (isApiError(error) && error.kind === "not_found") {
        await queryClient.invalidateQueries({ queryKey: queryKeys.publicMenu(slug) });
        return; // the menu query now answers 404 -> "Este local no está disponible"
      }
      if (applyServerFieldErrors(error, setError, ORDER_SERVER_MESSAGES)) return;
      if (isApiError(error) && error.kind === "validation") {
        setFormError(`El pedido supera el máximo permitido (${formatCents(ORDER_TOTAL_MAX_CENTS)} o 30 platos distintos). Sacá algunos platos y probá de nuevo.`);
        return;
      }
      setFormError(describeError(error));
    }
  });

  return (
    <>
      <div>
        <Link to={`/pedir/${slug}`} className={buttonClasses("ghost")}>
          <ArrowLeft aria-hidden="true" size={24} strokeWidth={1.75} />
          Seguir eligiendo
        </Link>
      </div>
      <header className="flex flex-col gap-1">
        <h1 className="text-display-md">Tu pedido</h1>
        <p className="text-body text-ink-muted">{menu.data.business_name} · Retiro por el local</p>
      </header>

      <section aria-label="Platos del pedido" className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4">
        <ul className="flex flex-col gap-2">
          {lines.map((line) => {
            const item = itemsById.get(line.itemId)!;
            return (
              <li key={line.itemId} className="flex justify-between gap-3 text-body">
                <span><span className="text-data-sm text-ink-muted">{line.qty}×</span> {item.name}</span>
                <span className="text-price">{formatCents((menu.priceCents.get(line.itemId) ?? 0) * line.qty)}</span>
              </li>
            );
          })}
        </ul>
        <div className="flex justify-between gap-3 border-t border-border pt-3">
          <span className="text-heading-3">Total</span>
          <span className="font-mono text-[16px] font-semibold leading-6 tabular-nums">{formatCents(totalCents)}</span>
        </div>
      </section>

      {overLimit && <Alert tone="danger">El total supera {formatCents(ORDER_TOTAL_MAX_CENTS)}. Sacá algunos platos para poder hacer el pedido.</Alert>}
      {formError && <Alert tone="danger">{formError}</Alert>}

      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
        <TextField large label="Tu nombre" autoComplete="name" maxLength={CUSTOMER_NAME_MAX} error={errors.customer_name?.message} {...register("customer_name")} />
        <TextField
          large
          label="Teléfono"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          maxLength={PHONE_MAX_LENGTH}
          placeholder="351 555-0142"
          help="El local lo usa solo para avisarte sobre este pedido."
          error={errors.customer_phone?.message}
          {...register("customer_phone")}
        />
        <TextAreaField
          large
          label="Notas para el local (opcional)"
          maxLength={NOTES_MAX}
          help={`${notes.length} de ${NOTES_MAX} caracteres`}
          error={errors.notes?.message}
          {...register("notes")}
        />
        <Button type="submit" variant="primary" size="lg" block disabled={isSubmitting || overLimit}>
          {isSubmitting ? "Enviando pedido..." : "Hacer pedido"}
        </Button>
      </form>
    </>
  );
}
