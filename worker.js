const runtime = {
  product: "MiMicus iAffice",
  supervisor: "LAYA",
  mode: "simulation-safe",
  release: "v0.3-prep",
  corePackage: "mimicus-swarm",
  coreVersion: "0.2.2",
  sourceHead: "565407eb1296eae617f5b14b512d2e0cf08c6c02",
  morphologies: ["solo","paired_verify","parallel_fanout","sparse_graph","hierarchical_fanout_fanin"]
};

const headers = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff"
};

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
        coreVersion: runtime.coreVersion,
        coreSourceHead: runtime.sourceHead
      }), { headers });
    }
    if (url.pathname === "/api/runtime") {
      return new Response(JSON.stringify(runtime), { headers });
    }
    return env.ASSETS.fetch(request);
  }
};
