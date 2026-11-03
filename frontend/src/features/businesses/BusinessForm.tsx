import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "../../components/Button";
import { Alert } from "../../components/States";
import { TextField } from "../../components/TextField";
import { describeError } from "../../lib/errorMessages";
import { applyServerFieldErrors } from "../../lib/formErrors";
import { BUSINESS_NAME_MAX, INDUSTRY_MAX, PICKUP_HOURS_MAX, PICKUP_HOURS_MIN } from "../../lib/limits";
import { BUSINESS_SERVER_MESSAGES, businessSchema, type BusinessValues } from "./businessSchema";

type BusinessFormProps = {
  defaultValues: BusinessValues;
  submitLabel: string;
  onSubmit: (values: BusinessValues) => Promise<unknown>;
  onCancel?: () => void;
};

// Used to create a branch and to edit one (name, industry, pickup time)
export function BusinessForm({ defaultValues, submitLabel, onSubmit, onCancel }: BusinessFormProps) {
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<BusinessValues>({
    resolver: zodResolver(businessSchema),
    defaultValues,
  });

  const submit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await onSubmit(values);
    } catch (error) {
      if (!applyServerFieldErrors(error, setError, BUSINESS_SERVER_MESSAGES)) setFormError(describeError(error));
    }
  });

  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-4">
      {formError && <Alert tone="danger">{formError}</Alert>}
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField label="Nombre de la sucursal" maxLength={BUSINESS_NAME_MAX} error={errors.name?.message} {...register("name")} />
        <TextField label="Rubro" placeholder="Gastronomía" maxLength={INDUSTRY_MAX} error={errors.industry?.message} {...register("industry")} />
      </div>
      <TextField
        label="Plazo de retiro (horas)"
        type="number"
        inputMode="numeric"
        min={PICKUP_HOURS_MIN}
        max={PICKUP_HOURS_MAX}
        className="sm:max-w-[200px]"
        help={`Si un pedido listo no se retira en este plazo, se cancela solo. De ${PICKUP_HOURS_MIN} a ${PICKUP_HOURS_MAX} horas.`}
        error={errors.pickup_timeout_hours?.message}
        {...register("pickup_timeout_hours", { valueAsNumber: true })}
      />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="primary" disabled={isSubmitting}>
          {isSubmitting ? "Guardando..." : submitLabel}
        </Button>
        {onCancel && (
          <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
            Cancelar
          </Button>
        )}
      </div>
    </form>
  );
}
