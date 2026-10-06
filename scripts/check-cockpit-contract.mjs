import { readFileSync } from "node:fs";

const html = readFileSync("public/index.html", "utf8");
const app = readFileSync("public/app.js", "utf8");
const worker = readFileSync("worker.js", "utf8");

const ids = [...app.matchAll(/getElementById\(["']([^"']+)["']\)/g)].map((match) => match[1]);
const missing = [...new Set(ids)].filter((id) => !html.includes(`id="${id}"`) && !html.includes(`id='${id}'`));

if (missing.length) {
  throw new Error(`cockpit DOM contract missing ids: ${missing.sort().join(", ")}`);
}

if (/\bsourceHead\s*:|\bcoreSourceHead\s*:/.test(worker)) {
  throw new Error("ambiguous current-source fields are forbidden in simulation Worker metadata");
}

if (!worker.includes("historicalCoreCheckpoint")) {
  throw new Error("Worker must label the archived core SHA as historicalCoreCheckpoint");
}

console.log(`cockpit contract ok: ${new Set(ids).size} referenced DOM ids resolved`);
