import { z } from "zod";
import { BUSINESS_NAME_MAX, INDUSTRY_MAX, PICKUP_HOURS_MAX, PICKUP_HOURS_MIN } from "../../lib/limits";

const hoursMessage = `Elegí un plazo entre ${PICKUP_HOURS_MIN} y ${PICKUP_HOURS_MAX} horas`;

export const businessSchema = z.object({
  name: z.string().trim().min(1, "Escribí el nombre de la sucursal").max(BUSINESS_NAME_MAX, `Usá como máximo ${BUSINESS_NAME_MAX} caracteres`),
  industry: z.string().trim().min(1, "Escribí el rubro, por ejemplo gastronomía").max(INDUSTRY_MAX, `Usá como máximo ${INDUSTRY_MAX} caracteres`),
  pickup_timeout_hours: z.number(hoursMessage).int(hoursMessage).min(PICKUP_HOURS_MIN, hoursMessage).max(PICKUP_HOURS_MAX, hoursMessage),
});

export type BusinessValues = z.infer<typeof businessSchema>;

export const BUSINESS_SERVER_MESSAGES = {
  name: `El nombre necesita entre 1 y ${BUSINESS_NAME_MAX} caracteres`,
  industry: `El rubro necesita entre 1 y ${INDUSTRY_MAX} caracteres`,
  pickup_timeout_hours: hoursMessage,
};

export function publicUrl(slug: string): string {
  return `${window.location.origin}/pedir/${slug}`;
}
