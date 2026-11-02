// Asserts the built report is self-contained: the page cannot make a network request.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const file = fileURLToPath(new URL("../src/dataauditor/static/report.html", import.meta.url));
const html = readFileSync(file, "utf8");
const problems = [];

// React's bundled source contains inert strings that look like URLs. They are
// never fetched: W3C XML namespace identifiers (used with createElementNS) and
// the text of React's production error message. Allow-list exactly these.
const ALLOWED = [
  "https://react.dev/errors/",
  "http://www.w3.org/2000/svg",
  "http://www.w3.org/1999/xhtml",
  "http://www.w3.org/1998/Math/MathML",
  "http://www.w3.org/1999/xlink",
  "http://www.w3.org/XML/1998/namespace",
];
let rest = html;
for (const ok of ALLOWED) rest = rest.split(ok).join("");
for (const bad of ["http://", "https://"]) {
  if (rest.includes(bad)) problems.push(`forbidden substring outside allow-list: ${bad}`);
}

// framer-motion's bundled source tests animated values with a JS string literal
// (`!e.startsWith(`url(`)`). It is code, not CSS, and loads nothing. Allow exactly it.
const URL_ALLOWED = ["startsWith(`url(`)"];
let noUrl = html;
for (const ok of URL_ALLOWED) noUrl = noUrl.split(ok).join("");
if (noUrl.includes("url(")) problems.push("forbidden substring: url(");
for (const bad of ["@font-face", "<link", "@import"]) {
  if (html.includes(bad)) problems.push(`forbidden substring: ${bad}`);
}

// Markup outside script and style bodies must not reference any resource.
const markup = html.replace(/<(script|style)\b([^>]*)>[\s\S]*?<\/\1>/g, "<$1$2></$1>");
for (const attr of [/\ssrc\s*=/i, /\shref\s*=/i]) {
  if (attr.test(markup)) problems.push(`markup contains ${attr}`);
}

const placeholder = '<script id="audit-data" type="application/json">__AUDIT_DATA__</script>';
const idCount = html.split('id="audit-data"').length - 1;
if (idCount !== 1) problems.push(`expected exactly one id="audit-data" block, found ${idCount}`);
if (html.split(placeholder).length !== 2) problems.push("data block placeholder missing, altered or duplicated");
const phCount = html.split("__AUDIT_DATA__").length - 1;
if (phCount !== 1) problems.push(`__AUDIT_DATA__ must appear exactly once, found ${phCount}`);

const scriptTags = markup.match(/<script\b[^>]*>/g) ?? [];
if (scriptTags.length !== 2) problems.push(`expected exactly 2 script tags (data + bundle), found ${scriptTags.length}`);
const bundleAt = html.search(/<script\b(?![^>]*audit-data)[^>]*>/);
if (bundleAt === -1) problems.push("no inline bundle script");
if (html.indexOf('id="audit-data"') > bundleAt) problems.push("data block must come before the app script");
if (!html.includes('<meta charset="utf-8">')) problems.push("missing charset meta");
if (!html.includes("<title>Data audit</title>")) problems.push("missing static title");

if (problems.length) {
  console.error("check-build failed:\n  " + problems.join("\n  "));
  process.exit(1);
}
console.log(`check-build ok (${html.length} bytes)`);
