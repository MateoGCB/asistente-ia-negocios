import { describe, expect, it } from "vitest";
import { registerSchema } from "../src/features/auth/schemas";
import { orderFormSchema } from "../src/features/public/orderForm";
import { charCount, passwordProblems, phoneProblem, utf8ByteLength } from "../src/lib/validation";

describe("password rules (register only), counted in BYTES", () => {
  it("knows that accents and ñ take 2 bytes", () => {
    expect(utf8ByteLength("a")).toBe(1);
    expect(utf8ByteLength("ñ")).toBe(2);
    expect(utf8ByteLength("á")).toBe(2);
    expect(charCount("ñandú")).toBe(5);
  });

  it.each([
    ["abcdefg1", []],                                  // exactly 8
    ["a1" + "x".repeat(70), []],                       // exactly 72 bytes
    ["ñ".repeat(35) + "a1", []],                       // 37 characters, exactly 72 bytes
    ["abcdef1", ["minChars"]],                         // 7 characters
    ["abcdefgh", ["number"]],                          // no number
    ["12345678", ["letter"]],                          // no letter
    ["a1" + "x".repeat(71), ["maxBytes"]],             // 73 bytes
    ["1" + "ñ".repeat(39), ["maxBytes"]],              // only 40 characters but 79 bytes
  ])("passwordProblems(%j) = %j", (password, problems) => {
    expect(passwordProblems(password)).toEqual(problems);
  });

  it("the register form rejects 73 bytes and the 40 accented characters", () => {
    const base = { name: "Persona", email: "persona@example.com" };
    expect(registerSchema.safeParse({ ...base, password: "a1" + "x".repeat(70) }).success).toBe(true);
    expect(registerSchema.safeParse({ ...base, password: "a1" + "x".repeat(71) }).success).toBe(false);
    expect(registerSchema.safeParse({ ...base, password: "1" + "ñ".repeat(39) }).success).toBe(false);
  });

  it("the register form trims the name and requires 1 to 100 characters", () => {
    const base = { email: "persona@example.com", password: "clave1234" };
    expect(registerSchema.safeParse({ ...base, name: "   " }).success).toBe(false);
    expect(registerSchema.safeParse({ ...base, name: "x".repeat(101) }).success).toBe(false);
    const parsed = registerSchema.parse({ ...base, name: "  Ana  " });
    expect(parsed.name).toBe("Ana");
  });
});

describe("phone (same rules as the backend)", () => {
  it.each(["123456", "123456789012345", "+54 9 351 123-4567", "351 - 1234567", "+549351123456789"])("accepts %j", (phone) => {
    expect(phoneProblem(phone)).toBeNull();
  });

  it.each([
    "",
    "12345",              // 5 digits
    "1234567890123456",   // 16 digits
    "11  0000-0000",      // double space
    "11 0000--0000",      // double hyphen
    "11+00000000",        // + in the middle
    "------",             // no digits
    "abc123456",          // letters
  ])("rejects %j", (phone) => {
    expect(phoneProblem(phone)).not.toBeNull();
  });
});

describe("order form limits", () => {
  const valid = { customer_name: "Cliente", customer_phone: "351 555-0142", notes: "" };

  it("accepts the edges: name of 2 and notes of 300", () => {
    expect(orderFormSchema.safeParse({ ...valid, customer_name: "Al", notes: "x".repeat(300) }).success).toBe(true);
  });

  it("rejects a 1-letter name, notes of 301 and a short phone", () => {
    expect(orderFormSchema.safeParse({ ...valid, customer_name: "A" }).success).toBe(false);
    expect(orderFormSchema.safeParse({ ...valid, notes: "x".repeat(301) }).success).toBe(false);
    expect(orderFormSchema.safeParse({ ...valid, customer_phone: "12345" }).success).toBe(false);
  });
});
