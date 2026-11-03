import type { ButtonHTMLAttributes, Ref } from "react";
import { cn } from "../lib/cn";
import { buttonClasses, type ButtonSize, type ButtonVariant } from "./buttonStyles";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
  ref?: Ref<HTMLButtonElement>; // React 19: ref is a regular prop
};

export function Button({ variant = "secondary", size = "md", block = false, className, type = "button", ref, ...props }: ButtonProps) {
  return <button ref={ref} type={type} className={cn(buttonClasses(variant, size, block), className)} {...props} />;
}
