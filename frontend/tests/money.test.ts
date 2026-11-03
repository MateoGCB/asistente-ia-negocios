import { describe, expect, it } from "vitest";
import { centsToDecimalText, formatCents, formatPrice, parsePriceInput, sumCents, toCents } from "../src/lib/money";

const NBSP = "\u00a0"; // Intl puts a non-breaking space between "$" and the number

describe("money in integer cents", () => {
  it.each([
    ["8500.00", 850000],
    ["3500.50", 350050],
    ["3500.5", 350050],
    ["12", 1200],
    ["0.05", 5],
    ["10000000.00", 1000000000],
  ])("toCents(%s) = %i", (text, cents) => {
    expect(toCents(text)).toBe(cents);
  });

  it("adds 0,10 + 0,20 exactly (floats would give 0.30000000000000004)", () => {
    expect(0.1 + 0.2).not.toBe(0.3); // the problem we avoid
    expect(sumCents([toCents("0.10"), toCents("0.20")])).toBe(30);
    expect(formatCents(sumCents([toCents("0.10"), toCents("0.20")]))).toBe(`$${NBSP}0,30`);
  });

  it("converts values where float math fails (0.29 * 100 = 28.999999999999996 in floats)", () => {
    expect(0.29 * 100).not.toBe(29); // the trap
    expect(toCents("0.29")).toBe(29);
    expect(toCents("1.15")).toBe(115);
    expect(toCents("4.35")).toBe(435);
    expect(sumCents([toCents("0.29"), toCents("1.15"), toCents("4.35")])).toBe(579);
    expect(formatCents(sumCents([toCents("0.29"), toCents("1.15")]))).toBe(`$${NBSP}1,44`);
  });

  it("adds a realistic order exactly: 8500 + 2 x 3500,50 = 15501", () => {
    expect(sumCents([toCents("8500.00"), 2 * toCents("3500.50")])).toBe(1550100);
  });

  it.each(["", "abc", "-5", "1.234", "1,5"])("rejects %j as a backend decimal", (text) => {
    expect(() => toCents(text)).toThrow();
  });

  it("formats in es-AR, without decimals when they are zero", () => {
    expect(formatCents(980000)).toBe(`$${NBSP}9.800`);
    expect(formatCents(350050)).toBe(`$${NBSP}3.500,50`);
    expect(formatCents(1000000000)).toBe(`$${NBSP}10.000.000`);
    expect(formatCents(0)).toBe(`$${NBSP}0`);
    expect(formatPrice("24600.00")).toBe(`$${NBSP}24.600`);
  });

  it("writes cents back as the decimal text the backend expects", () => {
    expect(centsToDecimalText(350050)).toBe("3500.50");
    expect(centsToDecimalText(850000)).toBe("8500.00");
    expect(centsToDecimalText(5)).toBe("0.05");
  });

  it.each([
    ["8500", 850000],
    ["8.500", 850000],
    ["1.250.000", 125000000],
    ["3500,50", 350050],
    ["3.500,5", 350050],
    ["3500.5", 350050],
    ["$ 9.800", 980000],
    ["abc", null],
    ["", null],
    ["12,345", null],
  ])("parsePriceInput(%j) = %s", (text, cents) => {
    expect(parsePriceInput(text)).toBe(cents);
  });
});
