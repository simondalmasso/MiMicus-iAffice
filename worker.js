const runtime = {
  product: "MiMicus iAffice",
  supervisor: "LAYA",
  mode: "simulation-fixture",
  evidenceClass: "SIMULATED_FIXTURE",
  dataOrigin: "synthetic-ui-fixture",
  sideEffects: false,
  release: "v0.3-prep",
  corePackage: "mimicus-swarm",
  coreVersion: "0.2.2",
  sourceHead: "565407eb1296eae617f5b14b512d2e0cf08c6c02",
  morphologies: ["solo","paired_verify","parallel_fanout","sparse_graph","hierarchical_fanout_fanin"]
};

const securityHeaders = {
  "strict-transport-security": "max-age=31536000; includeSubDomains",
  "content-security-policy": "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY",
  "referrer-policy": "no-referrer",
  "permissions-policy": "camera=(), microphone=(), geolocation=()"
};

const jsonHeaders = {
  ...securityHeaders,
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store"
};

function secureResponse(response) {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries(securityHeaders)) headers.set(name, value);
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/health") {
      return new Response(JSON.stringify({
        ok: true,
        service: "mimicus",
        runtime: "cloudflare-workers",
        ui: "monochrome-v2",
        release: runtime.release,
        evidenceClass: runtime.evidenceClass,
        coreVersion: runtime.coreVersion,
        coreSourceHead: runtime.sourceHead
      }), { headers: jsonHeaders });
    }
    if (url.pathname === "/api/runtime") {
      return new Response(JSON.stringify(runtime), { headers: jsonHeaders });
    }
    return secureResponse(await env.ASSETS.fetch(request));
  }
};
