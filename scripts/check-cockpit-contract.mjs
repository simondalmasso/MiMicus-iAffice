import { readFileSync } from "node:fs";

const html = readFileSync("public/index.html", "utf8");
const app = readFileSync("public/app.js", "utf8");
const worker = readFileSync("worker.js", "utf8");

const ids = [
  ...app.matchAll(/getElementById\(["']([^"']+)["']\)/g),
  ...app.matchAll(/\bget\(["']([^"']+)["']\)/g)
].map((match) => match[1]);
const missing = [...new Set(ids)].filter((id) => !html.includes(`id="${id}"`) && !html.includes(`id='${id}'`));

if (missing.length) {
  throw new Error(`cockpit DOM contract missing ids: ${missing.sort().join(", ")}`);
}

if (/\bsourceHead\s*:|\bcoreSourceHead\s*:/.test(worker)) {
  throw new Error("ambiguous current-source fields are forbidden in simulation Worker metadata");
}

// A public observability UI may only display real observations.
// It must not boot into synthetic timelines or fabricated business KPIs.
const banned = [
  "simulationLines", "startSimulation", "SIMULATED_FIXTURE",
  "14.578", "312.3M", "22.70M", "mPipeline2", "Autopilot SIM",
  "historicalCoreCheckpoint", "565407eb1296eae617f5b14b512d2e0cf08c6c02"
];
for (const term of banned) {
  if (html.includes(term) || app.includes(term) || worker.includes(term)) {
    throw new Error("non-live cockpit content forbidden: " + term);
  }
}
if (!worker.includes("coreConnected: false") || !worker.includes("agentActivityAvailable: false")) {
  throw new Error("public Worker must deny unverified LAYA connectivity");
}
if (!worker.includes("externalEffectsEnabled: false")) {
  throw new Error("public Worker must explicitly deny effect authority");
}
if (!worker.includes('"LIVE_OBSERVED"') || !worker.includes('"/api/status"')) {
  throw new Error("public Worker must expose a real status endpoint");
}
if (!app.includes("local-live-observer") || !app.includes("/api/activity?since=")) {
  throw new Error("actual Python observer integration was removed");
}


const staticAssetRules = readFileSync("public/_headers", "utf8");
const staticLines = staticAssetRules.split(/\r?\n/).filter((line) => line.trim() && !line.startsWith("#"));
if (staticLines[0] !== "/*") {
  throw new Error("static assets must have a global /* security-header rule");
}
const deployedAssetHeaders = new Map();
for (const line of staticLines.slice(1)) {
  const parsed = line.match(/^\s+([A-Za-z0-9-]+):\s+(.+)$/);
  if (!parsed) {
    throw new Error("unexpected static asset header rule: " + line);
  }
  const name = parsed[1].toLowerCase();
  if (deployedAssetHeaders.has(name)) {
    throw new Error("duplicate static asset header: " + name);
  }
  deployedAssetHeaders.set(name, parsed[2]);
}
const securityBlock = worker.match(/const securityHeaders = \{([\s\S]*?)\n\};/)?.[1];
if (!securityBlock) {
  throw new Error("Worker securityHeaders not found");
}
const canonicalSecurityHeaders = [...securityBlock.matchAll(/^\s*"([^"]+)":\s*"([^"]+)"[,]?$/gm)];
if (canonicalSecurityHeaders.length < 5) {
  throw new Error("Worker securityHeaders parsing failed");
}
for (const [, name, value] of canonicalSecurityHeaders) {
  if (deployedAssetHeaders.get(name) !== value) {
    throw new Error("static asset security header drift: " + name);
  }
}

console.log(`cockpit contract ok: ${new Set(ids).size} referenced DOM ids resolved`);
