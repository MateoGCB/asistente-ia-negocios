import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useLocation, useNavigate } from "react-router";
import { login } from "../../api/endpoints";
import { isApiError } from "../../api/errors";
import { consumeSessionExpired, setToken } from "../../api/session";
import { HOME_PATH } from "../../app/guards";
import { useDocumentTitle } from "../../app/useDocumentTitle";
import { Button } from "../../components/Button";
import { Alert } from "../../components/States";
import { TextField } from "../../components/TextField";
import { describeError } from "../../lib/errorMessages";
import { AuthLayout, linkClasses } from "./AuthLayout";
import { loginSchema, type LoginValues } from "./schemas";

export function LoginPage() {
  useDocumentTitle("Ingresar");
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? HOME_PATH;
  // Read once on mount: true when we arrived here because the token expired
  const [expired] = useState(consumeSessionExpired);
  const [formError, setFormError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const { access_token } = await login(values);
      setToken(access_token);
      navigate(from, { replace: true });
    } catch (error) {
      // A wrong email or password always gets the same message: we do not reveal which one failed
      setFormError(isApiError(error) && error.kind === "unauthorized"
        ? "El email o la contraseña no son correctos. Revisalos y probá de nuevo."
        : describeError(error));
    }
  });

  return (
    <AuthLayout
      title="Ingresá a tu panel"
      footer={<>¿Todavía no tenés cuenta? <Link to="/registro" className={linkClasses}>Creá una</Link></>}
    >
      {expired && <Alert>Tu sesión venció. Ingresá de nuevo para seguir.</Alert>}
      {formError && <Alert tone="danger">{formError}</Alert>}
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
        <TextField label="Email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
        <TextField label="Contraseña" type="password" autoComplete="current-password" error={errors.password?.message} {...register("password")} />
        <Button type="submit" variant="primary" block disabled={isSubmitting}>
          {isSubmitting ? "Ingresando..." : "Ingresar"}
        </Button>
      </form>
    </AuthLayout>
  );
}
