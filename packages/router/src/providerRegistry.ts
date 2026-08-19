import type { ComputeModelRecord, ComputeProviderRecord, ProviderEvidenceRecord, RouteState } from "./computeTypes.js";
import { activatingEvidence, isEvidenceFresh } from "./providerEvidence.js";

function assertIso(value: string, field: string): void { if (!Number.isFinite(Date.parse(value))) throw new Error(`INVALID_ISO:${field}`); }
function assertId(value: string, field: string): void { if (!/^[a-z0-9][a-z0-9._:@/-]{1,127}$/i.test(value)) throw new Error(`INVALID_ID:${field}`); }

export class ProviderRegistry {
  private providers = new Map<string, ComputeProviderRecord>();
  private models = new Map<string, ComputeModelRecord>();
  private evidence: ProviderEvidenceRecord[] = [];

  constructor(providers: ComputeProviderRecord[] = [], models: ComputeModelRecord[] = [], evidence: ProviderEvidenceRecord[] = []) { for (const p of providers) this.upsertProvider(p); for (const m of models) this.upsertModel(m); this.replaceEvidence(evidence); }

  upsertProvider(provider: ComputeProviderRecord): void {
    assertId(provider.providerId,"provider_id"); assertIso(provider.createdAt,"created_at"); assertIso(provider.updatedAt,"updated_at"); assertIso(provider.lastVerifiedAt,"last_verified_at"); assertIso(provider.verificationExpiresAt,"verification_expires_at");
    if (provider.publicOnly && provider.privacyClass !== "PUBLIC_ONLY") throw new Error("PUBLIC_ONLY_PRIVACY_MISMATCH");
    if (provider.freeType === "PAID" && provider.productionEligible) throw new Error("PAID_PROVIDER_CANNOT_BE_PRODUCTION_ELIGIBLE");
    this.providers.set(provider.providerId, structuredClone(provider));
  }

  upsertModel(model: ComputeModelRecord): void {
    assertId(model.providerId,"provider_id"); assertId(model.modelId,"model_id"); assertIso(model.lastSeenAt,"last_seen_at"); assertIso(model.catalogExpiresAt,"catalog_expires_at");
    if (!this.providers.has(model.providerId)) throw new Error("MODEL_PROVIDER_UNKNOWN");
    if (model.contextWindow <= 0 || model.maxOutputTokens <= 0) throw new Error("MODEL_LIMIT_INVALID");
    this.models.set(`${model.providerId}:${model.modelId}`, structuredClone(model));
  }

  replaceEvidence(items: ProviderEvidenceRecord[]): void { this.evidence = items.map((x) => structuredClone(x)); }
  addEvidence(item: ProviderEvidenceRecord): void { this.evidence.push(structuredClone(item)); }
  listProviders(): ComputeProviderRecord[] { return [...this.providers.values()].map((x) => structuredClone(x)); }
  listModels(): ComputeModelRecord[] { return [...this.models.values()].map((x) => structuredClone(x)); }
  listEvidence(providerId?: string): ProviderEvidenceRecord[] { return this.evidence.filter((x) => !providerId || x.providerId === providerId).map((x) => structuredClone(x)); }
  getProvider(id: string): ComputeProviderRecord | undefined { const p=this.providers.get(id); return p?structuredClone(p):undefined; }
  getModel(providerId: string, modelId: string): ComputeModelRecord | undefined { const m=this.models.get(`${providerId}:${modelId}`); return m?structuredClone(m):undefined; }

  refreshStates(now: string): void {
    for (const [id, provider] of this.providers) {
      if (!provider.enabled || provider.routeState === "RETIRED") { provider.routeState = provider.routeState === "RETIRED" ? "RETIRED" : "DISABLED"; provider.productionEligible = false; continue; }
      const activation = activatingEvidence(provider,this.evidence,now);
      if (provider.verificationExpiresAt <= now || !activation.ok) { provider.routeState = provider.verificationExpiresAt <= now ? "STALE_EVIDENCE" : "NEEDS_POLICY_VERIFICATION"; provider.productionEligible = false; }
      else if (provider.freeType === "TRIAL") { provider.routeState = "NEEDS_POLICY_VERIFICATION"; provider.productionEligible = false; }
      else { provider.routeState = "ACTIVE"; provider.productionEligible = true; }
      this.providers.set(id,provider);
    }
    for (const [id,model] of this.models) {
      const provider=this.providers.get(model.providerId);
      if(!model.enabled||!provider||provider.routeState!=="ACTIVE") model.routeState="DISABLED";
      else if(model.catalogExpiresAt<=now || !this.evidence.some((e)=>e.providerId===model.providerId&&(e.modelId===model.modelId||!e.modelId)&&e.claimType==="CATALOG"&&e.result==="SUPPORTS"&&isEvidenceFresh(e,now))) model.routeState="STALE_EVIDENCE";
      else model.routeState="ACTIVE";
      this.models.set(id,model);
    }
  }

  disable(id: string, reason = "OPERATOR_DISABLED"): boolean {
    const provider=this.providers.get(id); if(provider){provider.enabled=false;provider.productionEligible=false;provider.routeState="DISABLED";provider.retiredReason=reason;return true;}
    const matches=[...this.models.entries()].filter(([key,m])=>key===id||m.modelId===id); if(matches.length){for(const [,m] of matches){m.enabled=false;m.routeState="DISABLED";}return true;} return false;
  }

  retireProvider(id:string,reason:string):void { const p=this.providers.get(id); if(!p)throw new Error("PROVIDER_NOT_FOUND");p.enabled=false;p.productionEligible=false;p.routeState="RETIRED";p.retiredReason=reason; }
  activeModels(): ComputeModelRecord[] { return this.listModels().filter((m)=>m.enabled&&m.routeState==="ACTIVE"&&this.providers.get(m.providerId)?.productionEligible===true); }
  routeState(providerId:string):RouteState { return this.providers.get(providerId)?.routeState??"DISABLED"; }
}
