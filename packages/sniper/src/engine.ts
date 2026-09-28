export type ServiceKind =
  | 'WEBSITE'
  | 'ECOMMERCE'
  | 'WHATSAPP_AUTOMATION'
  | 'CRM'
  | 'SOCIAL_MANAGEMENT'
  | 'CATALOG'
  | 'PAYMENTS'
  | 'PRODUCT'
  | 'ANALYTICS'
  | 'CONTENT'
  | 'SEO_LOCAL';

export type ContactKind = 'EMAIL' | 'WHATSAPP' | 'PHONE' | 'INSTAGRAM' | 'WEB_FORM';

export interface ContactPoint {
  kind: ContactKind;
  value: string;
  provenance: 'PUBLIC_BUSINESS_LISTING' | 'BUSINESS_WEBSITE' | 'BUSINESS_SOCIAL' | 'OWNER_PROVIDED' | 'OTHER_PUBLIC';
}

export interface BusinessSignal {
  businessId: string;
  name: string;
  category: string;
  locality: string;
  observedAt: string;
  demand: { rating: number | null; reviewCount: number | null };
  digital: {
    websiteUrl: string | null;
    websiteQuality: number | null;
    ecommerce: boolean | null;
    crm: boolean | null;
    whatsappAutomation: boolean | null;
    socialActive: boolean | null;
    booking: boolean | null;
    paymentsOnline: boolean | null;
    analytics: boolean | null;
  };
  contacts: ContactPoint[];
  evidenceRefs: string[];
}

export interface OpportunityScore {
  score: number;
  reasons: string[];
  evidenceRefs: string[];
}

export interface OfferDecision {
  primary: ServiceKind[];
  secondary: ServiceKind[];
  why: string[];
}

export interface RevenueScenarioInput {
  monthlyLeads: number;
  conversionRate: number;
  averageOrderValue: number;
  scenarioConversionRate: number;
}

export interface PersuasionCase {
  observedFacts: string[];
  demoBrief: string;
  quantifiedClaim: null | {
    baselineMonthlyRevenue: number;
    scenarioMonthlyRevenue: number;
    scenarioDelta: number;
    isForecast: true;
    assumptions: RevenueScenarioInput;
  };
  rules: string[];
}

export type SniperRole =
  | 'ORCHESTRATOR'
  | 'SCOUT'
  | 'MARKET_RESEARCH'
  | 'QUALIFIER'
  | 'SALES'
  | 'NEGOTIATOR'
  | 'UX_AUDITOR'
  | 'WEB'
  | 'DESIGN'
  | 'SOCIAL'
  | 'CATALOG'
  | 'CRM'
  | 'AUTOMATION'
  | 'PAYMENTS'
  | 'PRODUCT'
  | 'ANALYTICS'
  | 'COPY'
  | 'DEMO'
  | 'DELIVERY'
  | 'AUD'
  | 'MEMORY';

export interface AgentCharter {
  role: SniperRole;
  owns: string;
  definitionOfDone: string;
  fences: string[];
}

export interface HumanGateInput {
  amountArs: number;
  meetingRequested: boolean;
  nonStandardTerms: boolean;
  legalCommitment: boolean;
}

export interface HumanGateDecision {
  required: boolean;
  reasons: string[];
}

export interface TacticStats {
  tacticId: string;
  attempts: number;
  replies: number;
  meetings: number;
  wins: number;
  losses: number;
  score: number;
}

export interface LearningObservation {
  outcome: 'REPLIED' | 'MEETING' | 'WON' | 'LOST' | 'UNKNOWN';
  audited: boolean;
}

export const DEFAULT_HUMAN_GATE_ARS = 1_000_000;

export function scoreOpportunity(signal: BusinessSignal): OpportunityScore {
  let score = 0;
  const reasons: string[] = [];
  const add = (points: number, reason: string): void => { score += points; reasons.push(reason); };

  if ((signal.demand.rating ?? 0) >= 4.5) add(8, 'STRONG_PUBLIC_RATING');
  if ((signal.demand.reviewCount ?? 0) >= 100) add(10, 'VISIBLE_DEMAND_REVIEW_VOLUME');

  if (!signal.digital.websiteUrl) add(24, 'NO_WEBSITE');
  else if (signal.digital.websiteQuality !== null && signal.digital.websiteQuality < 55) add(20, 'WEBSITE_QUALITY_GAP');

  if (signal.digital.ecommerce === false) add(15, 'NO_ECOMMERCE');
  if (signal.digital.crm === false) add(12, 'NO_CRM');
  if (signal.digital.whatsappAutomation === false) add(12, 'NO_WHATSAPP_AUTOMATION');
  if (signal.digital.paymentsOnline === false) add(7, 'NO_ONLINE_PAYMENTS');
  if (signal.digital.analytics === false) add(5, 'NO_ANALYTICS');
  if (signal.digital.socialActive === false) add(5, 'WEAK_SOCIAL_PRESENCE');
  if (signal.contacts.length > 0) add(4, 'PUBLIC_CONTACT_PATH_AVAILABLE');

  return { score: Math.min(100, score), reasons, evidenceRefs: [...signal.evidenceRefs] };
}

export function chooseOffer(signal: BusinessSignal): OfferDecision {
  const primary: ServiceKind[] = [];
  const secondary: ServiceKind[] = [];
  const why: string[] = [];
  const add = (service: ServiceKind, reason: string, tier: 'PRIMARY' | 'SECONDARY' = 'PRIMARY'): void => {
    const target = tier === 'PRIMARY' ? primary : secondary;
    if (!target.includes(service)) target.push(service);
    why.push(`${service}: ${reason}`);
  };

  if (!signal.digital.websiteUrl) add('WEBSITE', 'no public website detected');
  else if (signal.digital.websiteQuality !== null && signal.digital.websiteQuality < 55) add('WEBSITE', 'website quality is below opportunity threshold');

  if (signal.digital.ecommerce === false) add('ECOMMERCE', 'no ecommerce path detected');
  if (signal.digital.whatsappAutomation === false) add('WHATSAPP_AUTOMATION', 'customer messaging appears manual');
  if (signal.digital.crm === false) add('CRM', 'no CRM signal detected');
  if (signal.digital.paymentsOnline === false) add('PAYMENTS', 'no online payment path detected', 'SECONDARY');
  if (signal.digital.analytics === false) add('ANALYTICS', 'no analytics signal detected', 'SECONDARY');
  if (signal.digital.socialActive === false) add('SOCIAL_MANAGEMENT', 'social presence appears inactive', 'SECONDARY');
  if (primary.length === 0) add('PRODUCT', 'no obvious infrastructure gap; inspect conversion/product flow', 'SECONDARY');

  return { primary: primary.slice(0, 4), secondary: secondary.slice(0, 4), why };
}

export function buildPersuasionCase(
  signal: BusinessSignal,
  offer: OfferDecision,
  baseline?: RevenueScenarioInput
): PersuasionCase {
  const observedFacts: string[] = [];
  if (!signal.digital.websiteUrl) observedFacts.push('No public website was detected in the observed sources.');
  if (signal.digital.websiteQuality !== null) observedFacts.push(`Observed website quality score: ${signal.digital.websiteQuality}/100.`);
  if (signal.digital.ecommerce === false) observedFacts.push('No ecommerce path was detected.');
  if (signal.digital.crm === false) observedFacts.push('No CRM signal was detected.');
  if (signal.digital.whatsappAutomation === false) observedFacts.push('No WhatsApp automation signal was detected.');
  if ((signal.demand.reviewCount ?? 0) > 0) observedFacts.push(`Public demand signal: ${signal.demand.reviewCount} reviews at rating ${signal.demand.rating ?? 'unknown'}.`);

  let quantifiedClaim: PersuasionCase['quantifiedClaim'] = null;
  if (baseline) {
    const valid =
      baseline.monthlyLeads >= 0 &&
      baseline.conversionRate >= 0 &&
      baseline.conversionRate <= 1 &&
      baseline.averageOrderValue >= 0 &&
      baseline.scenarioConversionRate >= baseline.conversionRate &&
      baseline.scenarioConversionRate <= 1;
    if (!valid) throw new Error('INVALID_REVENUE_SCENARIO');
    const baselineMonthlyRevenue = baseline.monthlyLeads * baseline.conversionRate * baseline.averageOrderValue;
    const scenarioMonthlyRevenue = baseline.monthlyLeads * baseline.scenarioConversionRate * baseline.averageOrderValue;
    quantifiedClaim = {
      baselineMonthlyRevenue,
      scenarioMonthlyRevenue,
      scenarioDelta: scenarioMonthlyRevenue - baselineMonthlyRevenue,
      isForecast: true,
      assumptions: { ...baseline }
    };
  }

  return {
    observedFacts,
    demoBrief: `Build a high-fidelity before/after demo focused on ${offer.primary.join(', ') || offer.secondary.join(', ')}. Show the observed current-state friction beside a realistic improved flow. Do not impersonate the business or publish the demo.`,
    quantifiedClaim,
    rules: ['NO_FABRICATED_UPLIFT', 'OBSERVED_FACTS_SEPARATE_FROM_FORECASTS', 'NO_FAKE_TESTIMONIALS', 'NO_FAKE_HUMAN_IDENTITY']
  };
}

export function requiresHumanGate(input: HumanGateInput): HumanGateDecision {
  const reasons: string[] = [];
  if (input.amountArs >= DEFAULT_HUMAN_GATE_ARS) reasons.push('LARGE_DEAL');
  if (input.meetingRequested) reasons.push('BUYER_REQUESTED_HUMAN_MEETING');
  if (input.nonStandardTerms) reasons.push('NON_STANDARD_COMMERCIAL_TERMS');
  if (input.legalCommitment) reasons.push('LEGAL_COMMITMENT');
  return { required: reasons.length > 0, reasons };
}

export function buildAgentSquad(): AgentCharter[] {
  const row = (role: SniperRole, owns: string, definitionOfDone: string, fences: string[] = []): AgentCharter => ({ role, owns, definitionOfDone, fences });
  return [
    row('ORCHESTRATOR', 'goal decomposition, specialist routing and handoffs', 'every opportunity has one next owner, one expected artifact and no overlapping authority', ['NO_DIRECT_EXTERNAL_EFFECT']),
    row('SCOUT', 'public-market discovery', 'new businesses are captured with source evidence and deduplicated', ['NO_CONTACT']),
    row('MARKET_RESEARCH', 'local market and competitor evidence', 'market dossier contains sourced demand, category and competitive context', ['NO_UNSOURCED_FACT']),
    row('QUALIFIER', 'opportunity scoring and fit', 'every candidate is qualified, deferred or rejected with inspectable reasons', ['NO_CONTACT']),
    row('SALES', 'commercial offer and outreach strategy', 'offer matches diagnosed business gap and has a next action', ['NO_FALSE_CLAIM']),
    row('NEGOTIATOR', 'objection handling, concessions and deal state', 'negotiation has current position, acceptable bounds and next move', ['HUMAN_GATE_WHEN_REQUIRED']),
    row('UX_AUDITOR', 'conversion and usability diagnosis', 'audit has evidence, severity and demo-ready recommendations', ['NO_PUBLICATION']),
    row('WEB', 'web implementation', 'preview passes functional, responsive and accessibility checks', ['NO_PRODUCTION_DEPLOY_WITHOUT_POLICY']),
    row('DESIGN', 'visual systems and UI quality', 'demo has a coherent system, hierarchy and reusable assets', ['NO_COPYRIGHT_MISREPRESENTATION']),
    row('SOCIAL', 'social presence and content system', 'channel plan and review-ready assets exist', ['NO_PUBLISH_WITHOUT_POLICY']),
    row('CATALOG', 'product/service catalog structure', 'catalog data and presentation are complete and internally consistent'),
    row('CRM', 'pipeline and customer lifecycle design', 'CRM schema, stages and automations are testable'),
    row('AUTOMATION', 'workflow automation', 'automation has triggers, idempotency, failure path and audit trail'),
    row('PAYMENTS', 'payment-path integration design', 'payment proposal is technically scoped and never stores raw payment credentials', ['NO_MONEY_MUTATION']),
    row('PRODUCT', 'offer packaging and product decisions', 'service package has scope, acceptance criteria and delivery boundary'),
    row('ANALYTICS', 'measurement and experiment design', 'metrics have baseline, source, formula and uncertainty'),
    row('COPY', 'persuasive factual copy', 'copy is specific, evidence-backed and free of fabricated claims', ['NO_FAKE_HUMAN_IDENTITY']),
    row('DEMO', 'prospect-specific demo assembly', 'private demo demonstrates the diagnosed gap without impersonating the prospect', ['NO_PUBLICATION']),
    row('DELIVERY', 'post-sale fulfillment', 'contracted artifacts meet acceptance criteria and handoff is complete', ['NO_SCOPE_EXPANSION']),
    row('AUD', 'independent falsification and release gate', 'material claims and deliverables have an explicit PASS/FAIL/UNCERTAIN result', ['NO_SELF_APPROVAL']),
    row('MEMORY', 'audited organizational learning', 'outcome-labelled evidence is durable, attributable and reusable', ['NO_UNAUDITED_PROMOTION'])
  ];
}

export function applyLearningFeedback(base: TacticStats, observation: LearningObservation): TacticStats {
  if (!observation.audited || observation.outcome === 'UNKNOWN') return { ...base };
  const next = { ...base, attempts: base.attempts + 1 };
  if (observation.outcome === 'REPLIED') next.replies += 1;
  if (observation.outcome === 'MEETING') { next.replies += 1; next.meetings += 1; }
  if (observation.outcome === 'WON') { next.replies += 1; next.meetings += 1; next.wins += 1; }
  if (observation.outcome === 'LOST') next.losses += 1;
  const positive = next.replies + next.meetings * 2 + next.wins * 8;
  const negative = next.losses * 2;
  next.score = Math.max(0, Math.min(1, (positive - negative) / Math.max(1, next.attempts * 5)));
  return next;
}

export interface DashboardInput {
  opportunities: Array<{ status: string }>;
  negotiations: Array<{ state: string; nextAction: string }>;
  deliveries: Array<{ state: string }>;
  payments: Array<{ state: string; amountArs: number }>;
  learnings: Array<{ tacticId: string; score: number }>;
}

export function buildDashboardSnapshot(input: DashboardInput) {
  const count = (status: string): number => input.opportunities.filter(x => x.status === status).length;
  return {
    pipeline: {
      total: input.opportunities.length,
      qualified: count('QUALIFIED'),
      negotiating: count('NEGOTIATING'),
      won: count('WON'),
      lost: count('LOST')
    },
    money: {
      pendingArs: input.payments.filter(x => x.state === 'PENDING').reduce((sum, x) => sum + x.amountArs, 0),
      collectedArs: input.payments.filter(x => x.state === 'COLLECTED').reduce((sum, x) => sum + x.amountArs, 0)
    },
    live: [
      ...input.negotiations.map(x => ({ stream: 'NEGOTIATION', state: x.state, detail: x.nextAction })),
      ...input.deliveries.map(x => ({ stream: 'DELIVERY', state: x.state, detail: 'delivery state changed' })),
      ...input.payments.map(x => ({ stream: 'PAYMENT', state: x.state, detail: `ARS ${x.amountArs}` })),
      ...input.learnings.map(x => ({ stream: 'LEARNING', state: 'AUDITED', detail: `${x.tacticId} score=${x.score.toFixed(3)}` }))
    ]
  };
}
