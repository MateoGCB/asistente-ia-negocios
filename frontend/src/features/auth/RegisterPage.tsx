import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Check, Circle } from "lucide-react";
import { Link, useNavigate } from "react-router";
import { login, register as registerUser } from "../../api/endpoints";
import { isApiError } from "../../api/errors";
import { setToken } from "../../api/session";
import { useDocumentTitle } from "../../app/useDocumentTitle";
import { Button } from "../../components/Button";
import { Alert } from "../../components/States";
import { TextField } from "../../components/TextField";
import { describeError } from "../../lib/errorMessages";
import { applyServerFieldErrors } from "../../lib/formErrors";
import { USER_NAME_MAX } from "../../lib/limits";
import { PASSWORD_RULE_TEXT, passwordProblems, utf8ByteLength, type PasswordRule } from "../../lib/validation";
import { AuthLayout, linkClasses } from "./AuthLayout";
import { registerSchema, type RegisterValues } from "./schemas";

const RULES: PasswordRule[] = ["minChars", "maxBytes", "letter", "number"];

// The rules are visible BEFORE the user fails, and each one is checked live while typing
function PasswordRules({ password }: { password: string }) {
  const problems = passwordProblems(password);
  return (
    <ul className="flex flex-col gap-1" aria-label="Requisitos de la contraseña">
      {RULES.map((rule) => {
        const met = password !== "" && !problems.includes(rule);
        const Icon = met ? Check : Circle;
        return (
          <li key={rule} className={met ? "flex items-start gap-1 text-ink" : "flex items-start gap-1 text-ink-muted"}>
            <Icon aria-hidden="true" size={16} strokeWidth={1.75} className="mt-px flex-none" />
            {PASSWORD_RULE_TEXT[rule]}
            <span className="sr-only">{met ? " (cumplido)" : " (pendiente)"}</span>
          </li>
        );
      })}
      <li className="text-caption text-ink-muted">{utf8ByteLength(password)} de 72 bytes</li>
    </ul>
  );
}

export function RegisterPage() {
  useDocumentTitle("Crear cuenta");
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);

  const { register, handleSubmit, control, setError, formState: { errors, isSubmitting } } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { name: "", email: "", password: "" },
  });
  const password = useWatch({ control, name: "password" });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await registerUser(values);
      // Log in right away so the new owner lands in the panel
      const { access_token } = await login({ email: values.email, password: values.password });
      setToken(access_token);
      navigate("/negocios", { replace: true });
    } catch (error) {
      if (isApiError(error) && error.kind === "conflict") {
        setError("email", { message: "Ya hay una cuenta con ese email. Ingresá con tu contraseña o usá otro email." });
        return;
      }
      const marked = applyServerFieldErrors(error, setError, {
        name: `El nombre necesita entre 1 y ${USER_NAME_MAX} caracteres`,
        email: "Escribí un email válido, por ejemplo nombre@dominio.com",
        password: "La contraseña no cumple los requisitos de abajo",
      });
      if (!marked) setFormError(describeError(error));
    }
  });

  return (
    <AuthLayout
      title="Creá tu cuenta"
      footer={<>¿Ya tenés cuenta? <Link to="/login" className={linkClasses}>Ingresá</Link></>}
    >
      {formError && <Alert tone="danger">{formError}</Alert>}
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
        <TextField label="Tu nombre" autoComplete="name" maxLength={USER_NAME_MAX} error={errors.name?.message} {...register("name")} />
        <TextField label="Email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
        <TextField
          label="Contraseña"
          type="password"
          autoComplete="new-password"
          error={errors.password?.message}
          help={<PasswordRules password={password} />}
          {...register("password")}
        />
        <Button type="submit" variant="primary" block disabled={isSubmitting}>
          {isSubmitting ? "Creando cuenta..." : "Crear cuenta"}
        </Button>
      </form>
    </AuthLayout>
  );
}
