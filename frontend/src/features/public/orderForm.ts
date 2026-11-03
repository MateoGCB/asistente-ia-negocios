import { z } from "zod";
import { CUSTOMER_NAME_MAX, CUSTOMER_NAME_MIN, NOTES_MAX } from "../../lib/limits";
import { phoneProblem } from "../../lib/validation";

// Same rules as the backend's OrderCreate (which stays the authority)
export const orderFormSchema = z.object({
  customer_name: z
    .string()
    .trim()
    .min(CUSTOMER_NAME_MIN, `Escribí tu nombre (al menos ${CUSTOMER_NAME_MIN} letras)`)
    .max(CUSTOMER_NAME_MAX, `Usá como máximo ${CUSTOMER_NAME_MAX} caracteres`),
  customer_phone: z.string().superRefine((phone, ctx) => {
    const problem = phoneProblem(phone);
    if (problem) ctx.addIssue({ code: "custom", message: problem });
  }),
  notes: z.string().trim().max(NOTES_MAX, `Las notas pueden tener hasta ${NOTES_MAX} caracteres`),
});

export type OrderFormValues = z.infer<typeof orderFormSchema>;

export const ORDER_SERVER_MESSAGES = {
  customer_name: `Escribí tu nombre (de ${CUSTOMER_NAME_MIN} a ${CUSTOMER_NAME_MAX} caracteres)`,
  customer_phone: "Revisá el teléfono: de 6 a 15 números, sin espacios ni guiones repetidos",
  notes: `Las notas pueden tener hasta ${NOTES_MAX} caracteres`,
};
