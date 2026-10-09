// Public edge telemetry only. Python LAYA is NOT hosted inside this Worker.
// Never expose internal agent messages, synthetic metrics, or effect authority here.
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

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: jsonHeaders });
}

function operationalStatus() {
  return {
    service: "mimicus",
    surface: "cloudflare-edge",
    observedAt: new Date().toISOString(),
    evidenceClass: "LIVE_OBSERVED",
    edgeReachable: true,
    decisionAuthority: "MiMicusEngine",
    coreConnected: false,
    agentActivityAvailable: false,
    activeAgentCount: null,
    businessMetricsAvailable: false,
    externalEffectsEnabled: false,
    coreConnectionReason: "Python LAYA control plane is not connected to this public Worker",
    message: "Cloud edge operational; Python LAYA requires a separately authenticated runtime"
  };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const api = url.pathname === "/health" || url.pathname.startsWith("/api/");
    if (api && request.method !== "GET" && request.method !== "HEAD") {
      return jsonResponse({ ok: false, error: "method_not_allowed" }, 405);
    }
    if (url.pathname === "/api/health" || url.pathname === "/health") {
      return jsonResponse({
        ok: true,
        service: "mimicus",
        runtime: "cloudflare-workers",
        ...operationalStatus()
      });
    }
    if (url.pathname === "/api/status" || url.pathname === "/api/runtime") {
      return jsonResponse({ mode: "cloud-edge", ...operationalStatus() });
    }
    if (url.pathname.startsWith("/api/")) {
      return jsonResponse({ ok: false, error: "not_found" }, 404);
    }
    return secureResponse(await env.ASSETS.fetch(request));
  }
};
