import { FlatCompat } from "@eslint/eslintrc";
import path from "node:path";
import { fileURLToPath } from "node:url";

const filename = fileURLToPath(import.meta.url);
const directory = path.dirname(filename);
const compat = new FlatCompat({ baseDirectory: directory });

const config = [
  { ignores: [".next/**", ".next-dev/**", "next-env.d.ts", "node_modules/**", "coverage/**"] },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    files: ["**/*.{ts,tsx}"],
    rules: {
      "no-debugger": "error",
      "no-constant-binary-expression": "error",
      "no-duplicate-imports": "error",
      "no-unreachable": "error",
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
];

export default config;
