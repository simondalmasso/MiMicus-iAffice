# Mimicus iAffice

Monochrome autonomous-swarm cockpit for Cloudflare Workers.

- LAYA is the supervisor.
- The UI is deliberately slow/smooth rather than flashy.
- External side effects are disabled in the V1 cockpit simulation.
- The complete MiMicus Swarm source/history is preserved under `archive/MiMicus-swarm-source/`.
- Exact absorbed source HEAD: `565407eb1296eae617f5b14b512d2e0cf08c6c02`.

## Preview

```bash
npx wrangler dev
```

## Deploy

```bash
npx wrangler deploy
```

Expected Workers.dev hostname: `mimicus.simondalmasso44.workers.dev` when deployed in that Cloudflare account/subdomain.
