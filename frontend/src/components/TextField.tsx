import { useId, type InputHTMLAttributes, type ReactNode, type Ref, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "../lib/cn";

type FieldFrameProps = {
  id: string;
  label: string;
  help?: ReactNode;
  error?: string;
  children: ReactNode;
};

// Label always visible and linked with htmlFor/id. The error (in words, saying how to fix it)
// is shown above the help text; both stay visible so rules are never hidden after a mistake.
function FieldFrame({ id, label, help, error, children }: FieldFrameProps) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-label text-ink">
        {label}
      </label>
      {children}
      {error && (
        <p id={`${id}-error`} className="text-body-sm text-danger">
          {error}
        </p>
      )}
      {help && (
        <div id={`${id}-help`} className="text-body-sm text-ink-muted">
          {help}
        </div>
      )}
    </div>
  );
}

function controlClasses(hasError: boolean, large: boolean): string {
  return cn(
    "w-full rounded-md border bg-surface px-3 text-body text-ink placeholder:text-ink-subtle transition-tint focus-ring",
    large ? "min-h-12" : "min-h-10",
    hasError ? "border-danger" : "border-border-control",
  );
}

function describedBy(id: string, help: ReactNode, error: string | undefined): string | undefined {
  const ids = [error ? `${id}-error` : null, help ? `${id}-help` : null].filter(Boolean);
  return ids.length > 0 ? ids.join(" ") : undefined;
}

type CommonProps = { label: string; help?: ReactNode; error?: string; large?: boolean };

type TextFieldProps = CommonProps & InputHTMLAttributes<HTMLInputElement> & { ref?: Ref<HTMLInputElement> };

export function TextField({ label, help, error, large = false, id, className, ref, ...props }: TextFieldProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <FieldFrame id={fieldId} label={label} help={help} error={error}>
      <input
        ref={ref}
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fieldId, help, error)}
        className={cn(controlClasses(Boolean(error), large), className)}
        {...props}
      />
    </FieldFrame>
  );
}

type TextAreaFieldProps = CommonProps & TextareaHTMLAttributes<HTMLTextAreaElement> & { ref?: Ref<HTMLTextAreaElement> };

export function TextAreaField({ label, help, error, large = false, id, className, ref, ...props }: TextAreaFieldProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <FieldFrame id={fieldId} label={label} help={help} error={error}>
      <textarea
        ref={ref}
        id={fieldId}
        rows={3}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fieldId, help, error)}
        className={cn(controlClasses(Boolean(error), large), "py-2", className)}
        {...props}
      />
    </FieldFrame>
  );
}

type SelectFieldProps = CommonProps & SelectHTMLAttributes<HTMLSelectElement> & { ref?: Ref<HTMLSelectElement> };

export function SelectField({ label, help, error, large = false, id, className, children, ref, ...props }: SelectFieldProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <FieldFrame id={fieldId} label={label} help={help} error={error}>
      <select
        ref={ref}
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fieldId, help, error)}
        className={cn(controlClasses(Boolean(error), large), className)}
        {...props}
      >
        {children}
      </select>
    </FieldFrame>
  );
}
