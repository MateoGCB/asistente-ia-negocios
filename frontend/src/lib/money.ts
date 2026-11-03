// Money is handled in integer CENTS. The backend sends decimals as text ("3500.50"); parsing that
// text directly (never through a float) keeps sums exact: 0.10 + 0.20 is 30 cents, not 0.30000000000000004.

const DECIMAL_TEXT = /^(\d+)(?:\.(\d{1,2}))?$/;

// "8500.00" -> 850000, "3500.5" -> 350050, "12" -> 1200
export function toCents(value: string): number {
  const match = DECIMAL_TEXT.exec(value.trim());
  if (!match) throw new Error(`Invalid money value: ${value}`);
  const units = Number(match[1]);
  const fraction = Number((match[2] ?? "").padEnd(2, "0"));
  return units * 100 + fraction;
}

// 850000 -> "8500.00" (what the backend expects when the owner sets a price)
export function centsToDecimalText(cents: number): string {
  const units = Math.trunc(cents / 100);
  const fraction = String(cents % 100).padStart(2, "0");
  return `${units}.${fraction}`;
}

export function sumCents(values: number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

const WHOLE = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", minimumFractionDigits: 0, maximumFractionDigits: 0 });
const WITH_CENTS = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", minimumFractionDigits: 2, maximumFractionDigits: 2 });

// 980000 -> "$ 9.800", 350050 -> "$ 3.500,50" (no decimals when they are zero)
export function formatCents(cents: number): string {
  const formatter = cents % 100 === 0 ? WHOLE : WITH_CENTS;
  return formatter.format(cents / 100); // the division is only for display, never for sums
}

export function formatPrice(decimalText: string): string {
  return formatCents(toCents(decimalText));
}

// What the owner types in the price field: "8500", "8.500", "3500,50", "3.500,50", "$ 3500.5".
// In es-AR the comma is the decimal separator and the dot groups thousands; a dot followed by
// exactly 1 or 2 digits at the end is also taken as decimals ("3500.5"). Returns null if invalid.
export function parsePriceInput(text: string): number | null {
  let cleaned = text.replace(/[$\s]/g, "");
  if (cleaned === "") return null;
  if (cleaned.includes(",")) {
    cleaned = cleaned.replace(/\./g, "").replace(",", ".");
  } else if (/\.\d{3}(\.|$)/.test(cleaned)) {
    cleaned = cleaned.replace(/\./g, ""); // "8.500" or "1.250.000": thousands
  }
  if (!DECIMAL_TEXT.test(cleaned)) return null;
  return toCents(cleaned);
}
