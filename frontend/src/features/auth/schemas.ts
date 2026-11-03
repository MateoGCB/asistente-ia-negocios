import { z } from "zod";
import { USER_NAME_MAX } from "../../lib/limits";
import { PASSWORD_RULE_TEXT, passwordProblems } from "../../lib/validation";

const email = z
  .string()
  .trim()
  .min(1, "Escribí tu email")
  .pipe(z.email("Escribí un email válido, por ejemplo nombre@dominio.com"));

// Login: no password rules on purpose (a wrong password is just wrong: one generic message)
export const loginSchema = z.object({
  email,
  password: z.string().min(1, "Escribí tu contraseña"),
});

export const registerSchema = z.object({
  name: z.string().trim().min(1, "Escribí tu nombre").max(USER_NAME_MAX, `Usá como máximo ${USER_NAME_MAX} caracteres`),
  email,
  password: z.string().superRefine((password, ctx) => {
    const [first] = passwordProblems(password);
    if (first) ctx.addIssue({ code: "custom", message: `La contraseña necesita: ${PASSWORD_RULE_TEXT[first].toLowerCase()}` });
  }),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
