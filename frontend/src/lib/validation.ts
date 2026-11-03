import {
  PASSWORD_MAX_BYTES, PASSWORD_MIN_CHARS, PHONE_MAX_DIGITS, PHONE_MAX_LENGTH, PHONE_MIN_DIGITS,
} from "./limits";

const encoder = new TextEncoder();

// Bytes in UTF-8 ("ñ" and "á" take 2 bytes, an emoji 4). bcrypt cuts at 72 BYTES.
export function utf8ByteLength(text: string): number {
  return encoder.encode(text).length;
}

// Characters as the backend counts them (Python len = code points; JS .length counts UTF-16 units)
export function charCount(text: string): number {
  return [...text].length;
}

export type PasswordRule = "minChars" | "maxBytes" | "letter" | "number";

export const PASSWORD_RULE_TEXT: Record<PasswordRule, string> = {
  minChars: `Al menos ${PASSWORD_MIN_CHARS} caracteres`,
  maxBytes: `Como máximo ${PASSWORD_MAX_BYTES} bytes (las letras con tilde y la ñ cuentan doble)`,
  letter: "Al menos una letra",
  number: "Al menos un número",
};

// Rules of POST /auth/register, in order. Returns the ones the password does NOT meet.
export function passwordProblems(password: string): PasswordRule[] {
  const problems: PasswordRule[] = [];
  if (charCount(password) < PASSWORD_MIN_CHARS) problems.push("minChars");
  if (utf8ByteLength(password) > PASSWORD_MAX_BYTES) problems.push("maxBytes");
  if (!/\p{L}/u.test(password)) problems.push("letter");
  if (!/\p{Nd}/u.test(password)) problems.push("number");
  return problems;
}

export function countDigits(text: string): number {
  return (text.match(/\d/g) ?? []).length;
}

// Same checks as the backend (OrderCreate.customer_phone), on the trimmed value.
// Returns a message in Spanish, or null when the phone is valid.
export function phoneProblem(rawPhone: string): string | null {
  const phone = rawPhone.trim();
  if (phone === "") return "Escribí un teléfono para que el local pueda avisarte";
  if (!/^\+?[0-9 -]+$/.test(phone)) return "Usá solo números, espacios, guiones y un + al comienzo";
  if (phone.includes("  ") || phone.includes("--")) return "No repitas espacios ni guiones seguidos";
  const digits = countDigits(phone);
  if (digits < PHONE_MIN_DIGITS) return `Necesita al menos ${PHONE_MIN_DIGITS} números`;
  if (digits > PHONE_MAX_DIGITS) return `Puede tener como máximo ${PHONE_MAX_DIGITS} números`;
  if (phone.length > PHONE_MAX_LENGTH) return `Puede tener como máximo ${PHONE_MAX_LENGTH} caracteres en total`;
  return null;
}
