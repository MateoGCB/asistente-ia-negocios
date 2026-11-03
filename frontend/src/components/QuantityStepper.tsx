import { Minus, Plus } from "lucide-react";
import { Button } from "./Button";

type QuantityStepperProps = {
  itemName: string;
  quantity: number;
  canAdd: boolean;
  onAdd: () => void;
  onRemove: () => void;
};

// Public page control: "Agregar" while the item is not in the cart, then − quantity +.
// Every touch target is at least 44px.
export function QuantityStepper({ itemName, quantity, canAdd, onAdd, onRemove }: QuantityStepperProps) {
  if (quantity === 0) {
    return (
      <Button variant="secondary" size="touch" onClick={onAdd} disabled={!canAdd} aria-label={`Agregar ${itemName}`}>
        <Plus aria-hidden="true" size={24} strokeWidth={1.75} />
        Agregar
      </Button>
    );
  }
  return (
    <div className="flex items-center gap-2" role="group" aria-label={`Cantidad de ${itemName}`}>
      <Button variant="secondary" size="icon" onClick={onRemove} aria-label={`Quitar uno de ${itemName}`}>
        <Minus aria-hidden="true" size={24} strokeWidth={1.75} />
      </Button>
      <span aria-live="polite" className="min-w-8 text-center font-mono text-[16px] font-semibold tabular-nums">
        {quantity}
      </span>
      <Button variant="secondary" size="icon" onClick={onAdd} disabled={!canAdd} aria-label={`Agregar uno más de ${itemName}`}>
        <Plus aria-hidden="true" size={24} strokeWidth={1.75} />
      </Button>
    </div>
  );
}
