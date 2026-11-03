import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { MenuCategory } from "../../api/types";
import { Button } from "../../components/Button";
import { Alert } from "../../components/States";
import { SelectField, TextAreaField, TextField } from "../../components/TextField";
import { CATEGORY_LABEL, CATEGORY_ORDER } from "../../lib/categories";
import { describeError } from "../../lib/errorMessages";
import { applyServerFieldErrors } from "../../lib/formErrors";
import { ITEM_DESCRIPTION_MAX, ITEM_NAME_MAX, ITEM_PRICE_MAX_CENTS } from "../../lib/limits";
import { centsToDecimalText, parsePriceInput } from "../../lib/money";

const itemSchema = z.object({
  name: z.string().trim().min(1, "Escribí el nombre del plato").max(ITEM_NAME_MAX, `Usá como máximo ${ITEM_NAME_MAX} caracteres`),
  description: z.string().trim().min(1, "Escribí una descripción corta").max(ITEM_DESCRIPTION_MAX, `Usá como máximo ${ITEM_DESCRIPTION_MAX} caracteres`),
  price: z.string().superRefine((text, ctx) => {
    const cents = parsePriceInput(text);
    if (cents === null) ctx.addIssue({ code: "custom", message: "Escribí el precio en pesos, por ejemplo 8500 o 3500,50" });
    else if (cents <= 0) ctx.addIssue({ code: "custom", message: "El precio tiene que ser mayor a cero" });
    else if (cents > ITEM_PRICE_MAX_CENTS) ctx.addIssue({ code: "custom", message: "El precio es demasiado alto" });
  }),
  category: z.enum(CATEGORY_ORDER as [MenuCategory, ...MenuCategory[]], "Elegí una categoría"),
});

export type ItemValues = z.infer<typeof itemSchema>;
export type ItemPayload = { name: string; description: string; price: string; category: MenuCategory };

type ItemFormProps = {
  defaultValues: ItemValues;
  submitLabel: string;
  onSubmit: (payload: ItemPayload) => Promise<unknown>;
  onCancel?: () => void;
};

// Create or edit a menu item. The price is typed as the owner writes it ("3.500,50") and is sent
// to the backend as exact decimal text ("3500.50"), never as a float.
export function ItemForm({ defaultValues, submitLabel, onSubmit, onCancel }: ItemFormProps) {
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } = useForm<ItemValues>({
    resolver: zodResolver(itemSchema),
    defaultValues,
  });

  const submit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await onSubmit({ ...values, price: centsToDecimalText(parsePriceInput(values.price) ?? 0) });
      if (!onCancel) reset(defaultValues); // the "new item" form starts empty again
    } catch (error) {
      const marked = applyServerFieldErrors(error, setError, {
        name: `El nombre necesita entre 1 y ${ITEM_NAME_MAX} caracteres`,
        description: `La descripción necesita entre 1 y ${ITEM_DESCRIPTION_MAX} caracteres`,
        price: "Revisá el precio: tiene que ser mayor a cero y con hasta 2 decimales",
        category: "Elegí una categoría de la lista",
      });
      if (!marked) setFormError(describeError(error));
    }
  });

  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-4">
      {formError && <Alert tone="danger">{formError}</Alert>}
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField label="Nombre del plato" maxLength={ITEM_NAME_MAX} error={errors.name?.message} {...register("name")} />
        <SelectField label="Categoría" error={errors.category?.message} {...register("category")}>
          {CATEGORY_ORDER.map((category) => (
            <option key={category} value={category}>{CATEGORY_LABEL[category]}</option>
          ))}
        </SelectField>
      </div>
      <TextAreaField label="Descripción" maxLength={ITEM_DESCRIPTION_MAX} error={errors.description?.message} {...register("description")} />
      <TextField
        label="Precio"
        inputMode="decimal"
        placeholder="8500"
        className="sm:max-w-[200px]"
        help="En pesos. Ejemplos: 8500 o 3500,50"
        error={errors.price?.message}
        {...register("price")}
      />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="primary" disabled={isSubmitting}>{isSubmitting ? "Guardando..." : submitLabel}</Button>
        {onCancel && <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>Cancelar</Button>}
      </div>
    </form>
  );
}
