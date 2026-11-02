/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { viteSingleFile } from "vite-plugin-singlefile";
import { fileURLToPath } from "node:url";
import { readFileSync, unlinkSync, writeFileSync } from "node:fs";
import path from "node:path";

const outDir = fileURLToPath(new URL("../src/dataauditor/static", import.meta.url));

const DATA_BLOCK = '<script id="audit-data" type="application/json">__AUDIT_DATA__</script>';

// The single-file build emits index.html with the bundle in <head>. Rename it
// to report.html and put the data block before the first script, so the
// document order is data first, app second. Only our own markup is touched.
const finishReport = () => ({
  name: "finish-report",
  closeBundle() {
    const from = path.join(outDir, "index.html");
    let html = readFileSync(from, "utf8");
    if (html.split(DATA_BLOCK).length !== 2) throw new Error("data block missing or duplicated");
    html = html.replace(DATA_BLOCK, "");
    // Tailwind's licence banner carries its home page URL. Keep the MIT notice, drop the link.
    html = html.replace(/(\/\*! tailwindcss v[\d.]+ \| MIT License) \| https:\/\/tailwindcss\.com( \*\/)/, "$1$2");
    const first = html.indexOf("<script");
    html = html.slice(0, first) + DATA_BLOCK + html.slice(first);
    writeFileSync(path.join(outDir, "report.html"), html);
    unlinkSync(from);
  },
});

export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile(), finishReport()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  build: {
    outDir,
    emptyOutDir: false,
    minify: true,
    modulePreload: false,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/setupTests.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
