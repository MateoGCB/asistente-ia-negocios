import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

// The design tokens are the ONLY source of colors: no hex, rgb(), hsl() (or other color functions)
// may appear in src/ outside styles/tokens.css.
const SRC = join(__dirname, "..", "src");
const ALLOWED = new Set(["styles/tokens.css"]);
const HEX = /(?<![\w&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b/g;
const COLOR_FUNCTION = /\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(/gi;

export function findColorLiterals(text: string): string[] {
  return [...(text.match(HEX) ?? []), ...(text.match(COLOR_FUNCTION) ?? [])];
}

function filesIn(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? filesIn(path) : [path];
  });
}

describe("design guard", () => {
  it("the detector really finds color literals (so the guard is not empty)", () => {
    expect(findColorLiterals('className="bg-[#FF0000]"')).toEqual(["#FF0000"]);
    expect(findColorLiterals("color: rgb(1, 2, 3); background: hsl(0 0% 0%)")).toHaveLength(2);
    expect(findColorLiterals("box-shadow: 0 1px rgba(0,0,0,.5)")).toHaveLength(1);
    expect(findColorLiterals("Pedido #42 · #{order.number} · &#123;")).toEqual([]);
  });

  it("no file in src/ (except tokens.css) has a color literal", () => {
    const offenders = filesIn(SRC)
      .map((path) => ({ file: relative(SRC, path).replace(/\\/g, "/"), found: findColorLiterals(readFileSync(path, "utf8")) }))
      .filter(({ file, found }) => !ALLOWED.has(file) && !file.endsWith("schema.d.ts") && found.length > 0);
    expect(offenders).toEqual([]);
  });

  it("tokens.css does define the colors (light and dark)", () => {
    const tokens = readFileSync(join(SRC, "styles", "tokens.css"), "utf8");
    expect(tokens).toContain("--accent: #0E6B50;");
    expect(tokens).toContain('[data-theme="dark"]');
  });
});
