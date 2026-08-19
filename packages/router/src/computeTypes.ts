import type { AgentRole, ModelTier } from "../../core/src/types.js";

export type ProviderType = "FIRST_PARTY" | "AGGREGATOR" | "RELAY" | "LOCAL";
export type TrustClass = "FIRST_PARTY_DIRECT" | "AUTHORIZED_AGGREGATOR" | "UNVERIFIED_RELAY" | "LOCAL_TRUSTED";
export type FreeType = "RECURRING_FREE" | "PROMOTIONAL_FREE" | "SIGNUP_GRANT" | "TRIAL" | "LOCAL_ZERO_COST" | "UNKNOWN" | "PAID";
export type BillingSafety = "NO_BILLING_PATH" | "HARD_ZERO_SPEND_CAP" | "FREE_TIER_FAILS_CLOSED" | "GRANT_WITH_NO_OVERAGE" | "UNKNOWN" | "BILLABLE";
export type IdentityAssurance = "FIRST_PARTY_DECLARED" | "AGGREGATOR_DECLARED" | "FINGERPRINT_ONLY" | "UNKNOWN";
export type TrainingUseClass = "NO_TRAINING" | "OPT_OUT_VERIFIED" | "TRAINING_ALLOWED" | "UNKNOWN";
export type RetentionClass = "ZERO_RETENTION" | "BOUNDED_KNOWN" | "PROVIDER_DEFAULT_KNOWN" | "UNKNOWN";
export type EvidenceClass = "FIRST_PARTY_OFFICIAL_DOC" | "FIRST_PARTY_API" | "FIRST_PARTY_DASHBOARD_OBSERVED" | "FIRST_PARTY_TERMS" | "SOURCE_CODE_OFFICIAL" | "LIVE_ACCOUNT_PROBE" | "THIRD_PARTY_CATALOG" | "SOCIAL_POST" | "UNKNOWN";
export type ModelDataClass = "PUBLIC" | "INTERNAL_BUSINESS" | "CONFIDENTIAL" | "SECRET";
export type QuotaDimension = "TOKENS_PER_DAY" | "TOKENS_PER_MINUTE" | "REQUESTS_PER_DAY" | "REQUESTS_PER_MINUTE" | "REQUESTS_PER_SECOND" | "CREDITS" | "NEURONS" | "CONCURRENT_REQUESTS" | "MODEL_SPECIFIC_POOL" | "SHARED_PROVIDER_POOL" | "UNKNOWN";
export type ProviderHealthState = "UNKNOWN" | "HEALTHY" | "DEGRADED" | "RATE_LIMITED" | "QUOTA_EXHAUSTED" | "AUTH_FAILED" | "BILLING_RISK" | "MODEL_MISSING" | "POLICY_STALE" | "OUTAGE" | "DISABLED";
export type RouteState = "ACTIVE" | "DISCOVERED" | "NEEDS_POLICY_VERIFICATION" | "STALE_EVIDENCE" | "DISABLED" | "RETIRED";
export type ReservationStatus = "RESERVED" | "COMMITTED" | "RELEASED" | "EXPIRED" | "FAILED";
export type ComputeErrorClass = "NO_SAFE_MODEL_ROUTE" | "FREE_QUOTA_EXHAUSTED" | "RATE_LIMITED" | "PROVIDER_OUTAGE" | "AUTH_INVALID" | "BILLING_REQUIRED" | "PRICE_DRIFT" | "POLICY_EVIDENCE_STALE" | "MODEL_REMOVED" | "MODEL_RESPONSE_INVALID" | "RESERVATION_FAILED" | "CONFIDENTIAL_ROUTE_UNAVAILABLE" | "SECRET_DATA_MODEL_DENIED";
export type RouteReasonCode = "PRICE_NONZERO" | "PRICE_UNKNOWN" | "BILLING_UNSAFE" | "FREE_EVIDENCE_STALE" | "PRIVACY_DENIED" | "TRAINING_POLICY_DENIED" | "RETENTION_POLICY_DENIED" | "TRUST_CLASS_DENIED" | "IDENTITY_ASSURANCE_DENIED" | "CAPABILITY_MISMATCH" | "CONTEXT_TOO_SMALL" | "QUOTA_UNAVAILABLE" | "QUOTA_RESERVATION_FAILED" | "HEALTH_CIRCUIT_OPEN" | "PROVIDER_DISABLED" | "MODEL_DISABLED" | "MODEL_MISSING" | "AUTH_FAILED" | "BILLING_RISK" | "PROMO_EXPIRED" | "GRANT_EXHAUSTED" | "TOS_UNVERIFIED" | "LIVE_PROBE_REQUIRED" | "QUALITY_THRESHOLD_FAILED" | "SECRET_DATA_MODEL_DENIED";
export type BillingGateOutcome = "ALLOW_ZERO_COST" | "DENY_PRICE_NONZERO" | "DENY_PRICE_UNKNOWN" | "DENY_BILLING_UNKNOWN" | "DENY_OVERAGE_POSSIBLE" | "DENY_GRANT_EXHAUSTED" | "DENY_EVIDENCE_STALE";
export type TaskClass = "EXTRACTION" | "CLASSIFICATION" | "STRUCTURED_JSON" | "BUSINESS_REASONING" | "AUD_CHALLENGE" | "CODING" | "SUMMARIZATION";

export interface ComputeProviderRecord {
  providerId: string; providerName: string; providerType: ProviderType; apiProtocol: "WORKERS_AI_BINDING" | "OPENAI_COMPATIBLE" | "LOCAL_FAKE";
  trustClass: TrustClass; baseUrlId: string; credentialBindingName: string | null; accountMode: string; freeType: FreeType; billingSafety: BillingSafety;
  privacyClass: "PUBLIC_ONLY" | "PRIVATE_ALLOWED" | "CONFIDENTIAL_ALLOWED" | "LOCAL_ONLY"; retentionClass: RetentionClass; trainingUseClass: TrainingUseClass;
  tosStatus: "VERIFIED" | "NEEDS_POLICY_VERIFICATION" | "UNKNOWN"; sourcePolicyHash: string; pricingPolicyHash: string; enabled: boolean; productionEligible: boolean;
  publicOnly: boolean; createdAt: string; updatedAt: string; lastVerifiedAt: string; verificationExpiresAt: string; routeState: RouteState;
  grantRemainingUnits?: number; overagePossible?: boolean; retiredReason?: string;
}

export interface ComputeModelRecord {
  providerId: string; modelId: string; providerModelName: string; modelAlias: string; identityAssurance: IdentityAssurance; modelFamily: string;
  capabilities: string[]; contextWindow: number; maxOutputTokens: number; supportsTools: boolean; supportsStructuredOutput: boolean; supportsVision: boolean;
  supportsReasoning: boolean; supportsCoding: boolean; pricingMode: "ZERO" | "NONZERO" | "GRANT" | "UNKNOWN"; publishedInputPriceUsd: number | null;
  publishedOutputPriceUsd: number | null; freePoolId: string; quotaDimensions: QuotaDimension[]; benchmarkProfileId: string; enabled: boolean; lastSeenAt: string;
  catalogExpiresAt: string; routeState: RouteState;
}

export interface ProviderEvidenceRecord {
  evidenceId: string; providerId: string; modelId?: string; evidenceClass: EvidenceClass; claimType: "PRICE" | "BILLING" | "PRIVACY" | "TOS" | "CATALOG" | "HEALTH" | "QUOTA" | "IDENTITY";
  sourceIdentifier: string; retrievedAt: string; expiresAt: string; contentHash: string; result: "SUPPORTS" | "REFUTES" | "CANDIDATE_ONLY" | "UNKNOWN"; detail: string;
}

export interface QuotaPool {
  quotaPoolId: string; providerId: string; modelId?: string; dimension: QuotaDimension; verifiedFreeCeiling: number | null; localHardFraction: number;
  consumed: number; reserved: number; upstreamRemaining?: number; resetsAt?: string; evidenceId: string; updatedAt: string;
}

export interface ComputeReservation {
  reservationId: string; idempotencyKey: string; routeDecisionId: string; providerId: string; modelId: string; quotaPoolId: string;
  estimatedInput: number; reservedOutput: number; reservedUsageUnits: number; createdAt: string; expiresAt: string; status: ReservationStatus; actualUsage?: number;
  uncertainty?: "NONE" | "UNKNOWN_COMPLETION";
}

export interface ProviderHealthRecord {
  providerId: string; modelId?: string; state: ProviderHealthState; consecutiveFailures: number; openedAt?: string; retryAfter?: string; lastSuccessAt?: string; lastFailureAt?: string; detail: string;
}

export interface ComputeBenchmarkProfile {
  profileId: string; providerId: string; modelId: string; taskClass: TaskClass; score: number; schemaSuccessRate: number; successRate: number; latencyP50Ms: number; latencyP95Ms: number;
  qualified: boolean; measuredAt: string; evidenceClass: EvidenceClass;
}

export interface ComputeRequest {
  taskId: string; role: AgentRole; tier: ModelTier; taskClass: TaskClass; dataClass: ModelDataClass; pii: boolean; prompt: string; requestedMaxOutputTokens: number;
  requiredCapabilities: string[]; reason: string; critical?: boolean; preferredDifferentProviderFrom?: string; preferredDifferentFamilyFrom?: string;
}

export interface CandidateEvaluation {
  providerId: string; modelId: string; eligible: boolean; reasons: RouteReasonCode[]; score: number | null; billingOutcome: BillingGateOutcome;
}

export interface ComputeRouteDecision {
  routeDecisionId: string; taskId: string; dataClass: ModelDataClass; promptHash: string; estimatedInputTokens: number; requiredContextWindow: number; requiredCapabilities: string[];
  candidates: CandidateEvaluation[]; selectedProviderId?: string; selectedModelId?: string; selectedScore?: number; reason: string; createdAt: string;
}

export interface InferenceExecution {
  executionId: string; reservationId: string; taskId: string; role: AgentRole; dataClass: ModelDataClass; providerId: string; modelId: string; adapterVersion: string;
  providerConfigHash: string; prompt: string; promptHash: string; maxOutputTokens: number; requiredCapabilities: string[]; policyVersion: string; routeDecisionId: string;
  requestedAt: string; expiresAt: string; executionDigest: string;
}

export interface InferenceReceipt {
  executionId: string; providerId: string; modelId: string; providerRequestId?: string; inputTokens: number; outputTokens: number; usageUnits: number; latencyMs: number;
  finishReason: string; responseHash: string; providerQuotaHeadersNormalized: Record<string, number | string>; status: "SUCCESS" | "FAILED" | "UNKNOWN_COMPLETION";
  errorClass?: ComputeErrorClass; adapterVersion: string; completedAt: string;
}

export interface ComputeCallResult { text: string; receipt: InferenceReceipt; route: ComputeRouteDecision; reservation: ComputeReservation; }
