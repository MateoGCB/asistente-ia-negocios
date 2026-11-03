import { useEffect } from "react";
import { useParams } from "react-router";
import { useDocumentTitle } from "../../app/useDocumentTitle";
import { CartBar } from "../../components/CartBar";
import { MenuItemRow } from "../../components/MenuItemRow";
import { QuantityStepper } from "../../components/QuantityStepper";
import { Alert, ErrorState, LoadingList, Skeleton } from "../../components/States";
import { useToast } from "../../components/toastContext";
import { CATEGORY_LABEL, groupByCategory } from "../../lib/categories";
import { describeError } from "../../lib/errorMessages";
import { formatCents } from "../../lib/money";
import { ORDER_ITEMS_MAX, ORDER_QTY_MAX, ORDER_TOTAL_MAX_CENTS } from "../../lib/limits";
import { addBlockReason, cartCount, cartTotalCents, type AddBlock } from "./cart";
import { UnavailableScreen } from "./UnavailableScreen";
import { useCart } from "./useCart";
import { usePublicMenu } from "./usePublicMenu";

const BLOCK_TEXT = {
  qtyLimit: `Podés pedir hasta ${ORDER_QTY_MAX} unidades de cada plato.`,
  itemsLimit: `Un pedido puede tener hasta ${ORDER_ITEMS_MAX} platos distintos.`,
  totalLimit: `El total no puede superar ${formatCents(ORDER_TOTAL_MAX_CENTS)}.`,
} as const;

export function PublicMenuPage() {
  const slug = useParams().slug ?? "";
  const menu = usePublicMenu(slug);
  const [cart, dispatch] = useCart(slug);
  const { notify } = useToast();
  useDocumentTitle(menu.data?.business_name ?? null);

  // Items that left the menu (sold out or deleted) also leave the cart
  const menuData = menu.data;
  useEffect(() => {
    if (!menuData) return;
    const ids = menuData.items.map((item) => item.id);
    if (cart.some((line) => !ids.includes(line.itemId))) {
      dispatch({ type: "keepOnly", itemIds: ids });
      notify("Algunos platos ya no están disponibles y los sacamos de tu pedido.", "error");
    }
  }, [menuData, cart, dispatch, notify]);

  if (menu.unavailable) return <UnavailableScreen />;
  if (menu.isPending) {
    return (
      <>
        <Skeleton className="h-11 w-3/4" />
        <LoadingList rows={4} label="Cargando el menú" />
      </>
    );
  }
  if (menu.isError) return <ErrorState message={describeError(menu.error)} onRetry={() => menu.refetch()} />;

  const groups = groupByCategory(menu.data.items);
  // Limits currently reached (the "+" buttons are disabled; this says why)
  const blocked = new Set(
    menu.data.items
      .map((item) => addBlockReason(cart, item.id, menu.priceCents))
      .filter((reason): reason is NonNullable<AddBlock> => reason !== null),
  );

  return (
    <>
      <header className="flex flex-col gap-1">
        <h1 className="text-display-lg break-words">{menu.data.business_name}</h1>
        <p className="text-body text-ink-muted">{menu.data.menu_name} · Retiro por el local</p>
      </header>

      {[...blocked].map((reason) => (
        <Alert key={reason}>{BLOCK_TEXT[reason]}</Alert>
      ))}

      {groups.length === 0 ? (
        <p className="rounded-lg border border-border bg-surface p-4 text-body text-ink-muted">
          En este momento no hay platos disponibles. Probá más tarde.
        </p>
      ) : (
        groups.map((group) => (
          <section key={group.category} aria-labelledby={`cat-${group.category}`} className="flex flex-col gap-3">
            <h2 id={`cat-${group.category}`} className="text-heading-2">{CATEGORY_LABEL[group.category]}</h2>
            <ul className="overflow-hidden rounded-lg border border-border">
              {group.items.map((item) => (
                <MenuItemRow key={item.id} name={item.name} description={item.description} price={item.price}>
                  <QuantityStepper
                    itemName={item.name}
                    quantity={cart.find((l) => l.itemId === item.id)?.qty ?? 0}
                    canAdd={addBlockReason(cart, item.id, menu.priceCents) === null}
                    onAdd={() => dispatch({ type: "increment", itemId: item.id })}
                    onRemove={() => dispatch({ type: "decrement", itemId: item.id })}
                  />
                </MenuItemRow>
              ))}
            </ul>
          </section>
        ))
      )}

      <CartBar count={cartCount(cart)} totalCents={cartTotalCents(cart, menu.priceCents)} to={`/pedir/${slug}/resumen`} />
    </>
  );
}
