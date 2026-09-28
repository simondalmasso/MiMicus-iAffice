import test from 'node:test';
import assert from 'node:assert/strict';
import {
  scoreOpportunity,
  chooseOffer,
  requiresHumanGate,
  buildAgentSquad,
  buildPersuasionCase,
  applyLearningFeedback,
  buildDashboardSnapshot
} from '../dist/packages/sniper/src/engine.js';
import { recommendVerticalPack, SERVICE_PACKS } from '../dist/packages/sniper/src/servicePacks.js';

const signal = {
  businessId: 'biz-1',
  name: 'Comercio Demo',
  category: 'retail',
  locality: 'Santa Fe',
  observedAt: '2026-09-28T08:00:00.000Z',
  demand: { rating: 4.7, reviewCount: 620 },
  digital: {
    websiteUrl: null,
    websiteQuality: null,
    ecommerce: false,
    crm: false,
    whatsappAutomation: false,
    socialActive: true,
    booking: false,
    paymentsOnline: false,
    analytics: false
  },
  contacts: [
    { kind: 'EMAIL', value: 'ventas@example.test', provenance: 'PUBLIC_BUSINESS_LISTING' },
    { kind: 'WHATSAPP', value: '+543420000000', provenance: 'PUBLIC_BUSINESS_LISTING' }
  ],
  evidenceRefs: ['maps:biz-1', 'site-audit:biz-1']
};

test('opportunity score rewards visible demand plus concrete digital gaps', () => {
  const scored = scoreOpportunity(signal);
  assert.ok(scored.score >= 75);
  assert.ok(scored.reasons.some(x => x.includes('NO_WEBSITE')));
  assert.ok(scored.reasons.some(x => x.includes('NO_CRM')));
  assert.ok(scored.reasons.some(x => x.includes('NO_WHATSAPP_AUTOMATION')));
});

test('offer selection is evidence-backed and does not sell everything', () => {
  const offer = chooseOffer(signal);
  assert.deepEqual(offer.primary.slice(0, 3), ['WEBSITE', 'ECOMMERCE', 'WHATSAPP_AUTOMATION']);
  assert.ok(!offer.primary.includes('SOCIAL_MANAGEMENT'));
  assert.ok(offer.why.length >= 3);
});

test('persuasion case never invents revenue uplift without baseline evidence', () => {
  const p = buildPersuasionCase(signal, chooseOffer(signal));
  assert.equal(p.quantifiedClaim, null);
  assert.ok(p.observedFacts.length > 0);
  assert.ok(p.demoBrief.includes('before/after'));
  assert.ok(p.rules.includes('NO_FABRICATED_UPLIFT'));
});

test('persuasion case may calculate transparent scenario only from explicit baseline inputs', () => {
  const p = buildPersuasionCase(signal, chooseOffer(signal), {
    monthlyLeads: 200,
    conversionRate: 0.1,
    averageOrderValue: 25000,
    scenarioConversionRate: 0.13
  });
  assert.equal(p.quantifiedClaim?.baselineMonthlyRevenue, 500000);
  assert.equal(p.quantifiedClaim?.scenarioMonthlyRevenue, 650000);
  assert.equal(p.quantifiedClaim?.scenarioDelta, 150000);
  assert.equal(p.quantifiedClaim?.isForecast, true);
});

test('human gate is narrow but mandatory for large, requested or non-standard deals', () => {
  assert.equal(requiresHumanGate({ amountArs: 120000, meetingRequested: false, nonStandardTerms: false, legalCommitment: false }).required, false);
  assert.equal(requiresHumanGate({ amountArs: 1500000, meetingRequested: false, nonStandardTerms: false, legalCommitment: false }).required, true);
  assert.equal(requiresHumanGate({ amountArs: 120000, meetingRequested: true, nonStandardTerms: false, legalCommitment: false }).required, true);
  assert.equal(requiresHumanGate({ amountArs: 120000, meetingRequested: false, nonStandardTerms: true, legalCommitment: false }).required, true);
});

test('specialist squad is outcome-owned and keeps AUD and memory independent', () => {
  const squad = buildAgentSquad();
  const roles = new Set(squad.map(x => x.role));
  for (const role of ['ORCHESTRATOR','SCOUT','MARKET_RESEARCH','QUALIFIER','SALES','NEGOTIATOR','UX_AUDITOR','WEB','DESIGN','SOCIAL','CATALOG','CRM','AUTOMATION','PAYMENTS','PRODUCT','ANALYTICS','COPY','DEMO','DELIVERY','AUD','MEMORY']) {
    assert.ok(roles.has(role), role);
  }
  assert.equal(squad.every(x => x.owns.length > 0 && x.definitionOfDone.length > 0), true);
});

test('learning feedback changes tactic priors only from outcome-labelled observations', () => {
  const base = { tacticId: 'demo-first', attempts: 4, replies: 1, meetings: 0, wins: 0, losses: 1, score: 0.25 };
  const next = applyLearningFeedback(base, { outcome: 'WON', audited: true });
  assert.equal(next.attempts, 5);
  assert.equal(next.wins, 1);
  assert.ok(next.score > base.score);
  const ignored = applyLearningFeedback(base, { outcome: 'UNKNOWN', audited: true });
  assert.deepEqual(ignored, base);
});

test('dashboard snapshot exposes pipeline, negotiations, delivery, collections and learning', () => {
  const snapshot = buildDashboardSnapshot({
    opportunities: [{ status: 'QUALIFIED' }, { status: 'NEGOTIATING' }, { status: 'WON' }],
    negotiations: [{ state: 'ACTIVE', nextAction: 'counter-offer' }],
    deliveries: [{ state: 'IN_PROGRESS' }],
    payments: [{ state: 'PENDING', amountArs: 120000 }],
    learnings: [{ tacticId: 'demo-first', score: 0.6 }]
  });
  assert.equal(snapshot.pipeline.total, 3);
  assert.equal(snapshot.pipeline.negotiating, 1);
  assert.equal(snapshot.pipeline.won, 1);
  assert.equal(snapshot.money.pendingArs, 120000);
  assert.equal(snapshot.live.length >= 3, true);
});

test('openings retailer pack recommends visual configurator and quote commerce', () => {
  const pack = recommendVerticalPack({ category: 'aberturas', hasWebsite: true, websiteQuality: 31, hasEcommerce: false, has3d: false });
  assert.equal(pack.id, 'OPENINGS_COMMERCE');
  assert.ok(pack.deliverables.includes('VISUAL_CONFIGURATOR'));
  assert.ok(pack.deliverables.includes('QUOTE_TO_WHATSAPP'));
  assert.ok(pack.demoProof.includes('interactive room/material preview'));
});

test('real-estate pack can propose embeddable 3d tour without promising a measured twin', () => {
  const pack = recommendVerticalPack({ category: 'inmobiliaria', hasWebsite: true, websiteQuality: 70, hasEcommerce: false, has3d: false });
  assert.equal(pack.id, 'REAL_ESTATE_IMMERSIVE');
  assert.ok(pack.deliverables.includes('EMBEDDABLE_3D_TOUR'));
  assert.ok(pack.constraints.includes('NO_MEASURED_DIGITAL_TWIN_CLAIM_FROM_PHOTOS_ALONE'));
});

test('service packs are reusable patterns, not hardcoded prospect targets', () => {
  assert.equal(SERVICE_PACKS.every(x => !JSON.stringify(x).includes('rodriguezanton')), true);
  assert.equal(SERVICE_PACKS.every(x => x.verticalSignals.length > 0 && x.deliverables.length > 0), true);
});

import {
  chooseNextMove,
  promoteEpisode,
  rankDecisionCandidates
} from '../dist/packages/sniper/src/cognition.js';

test('cognitive policy escalates only when human gate is materially required', () => {
  const decision = chooseNextMove({
    opportunityId:'o1',
    stage:'NEGOTIATING',
    contactsAvailable:true,
    demoReady:true,
    replyState:'ENGAGED',
    objection:'needs-owner-call',
    attempts:2,
    daysSinceLastTouch:0,
    humanGate:{required:true,reasons:['BUYER_REQUESTED_HUMAN_MEETING']},
    tacticStats:[]
  });
  assert.equal(decision.move,'ESCALATE_HUMAN');
  assert.ok(decision.reasons.includes('BUYER_REQUESTED_HUMAN_MEETING'));
});

test('cognitive policy prefers proof/demo before outreach when demo is missing', () => {
  const decision = chooseNextMove({
    opportunityId:'o2',
    stage:'QUALIFIED',
    contactsAvailable:true,
    demoReady:false,
    replyState:'NONE',
    objection:null,
    attempts:0,
    daysSinceLastTouch:0,
    humanGate:{required:false,reasons:[]},
    tacticStats:[]
  });
  assert.equal(decision.move,'BUILD_DEMO');
});

test('ranker combines learned tactic score with context fit and contact fatigue', () => {
  const ranked = rankDecisionCandidates({
    opportunityId:'o3',
    stage:'CONTACTED',
    contactsAvailable:true,
    demoReady:true,
    replyState:'NO_REPLY',
    objection:null,
    attempts:1,
    daysSinceLastTouch:4,
    humanGate:{required:false,reasons:[]},
    tacticStats:[
      {tacticId:'demo-first',attempts:20,replies:9,meetings:4,wins:2,losses:3,score:.72},
      {tacticId:'generic-followup',attempts:30,replies:2,meetings:0,wins:0,losses:8,score:.08}
    ]
  });
  assert.equal(ranked[0].move,'FOLLOW_UP_WITH_VALUE');
  assert.ok(ranked[0].score>ranked.at(-1).score);
});

test('memory promotion requires audited outcome evidence', () => {
  assert.equal(promoteEpisode({
    episodeId:'e1',opportunityId:'o1',agentRole:'NEGOTIATOR',tacticId:'demo-first',
    observation:'prospect replied',outcome:'REPLIED',audited:false,evidenceRefs:['mail:1'],createdAt:'2026-09-28T00:00:00Z'
  }).promoted,false);
  assert.equal(promoteEpisode({
    episodeId:'e2',opportunityId:'o1',agentRole:'NEGOTIATOR',tacticId:'demo-first',
    observation:'prospect replied',outcome:'REPLIED',audited:true,evidenceRefs:['mail:2'],createdAt:'2026-09-28T00:00:00Z'
  }).promoted,true);
});