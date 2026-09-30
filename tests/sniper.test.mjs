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

import { buildCaseEvaluation } from '../dist/packages/sniper/src/case.js';

test('each business is projected as one inspectable case dossier', () => {
  const dossier = buildCaseEvaluation({
    opportunity: {
      id:'case-1',
      businessId:'biz-1',
      businessName:'Comercio Demo',
      category:'retail',
      locality:'Santa Fe',
      status:'NEGOTIATING',
      score:88,
      reasons:['WEBSITE_QUALITY_GAP','NO_CRM'],
      offer:{primary:['WEBSITE','CRM'],secondary:['ANALYTICS'],why:['WEBSITE: weak conversion path','CRM: no CRM signal detected']},
      persuasion:{observedFacts:['Observed website quality score: 31/100.'],demoBrief:'before/after',quantifiedClaim:null,rules:['NO_FABRICATED_UPLIFT']},
      contacts:[],
      evidenceRefs:['audit:1','maps:1'],
      nextOwner:'NEGOTIATOR',
      nextAction:'COUNTER_OFFER',
      createdAt:'2026-09-28T00:00:00Z',
      updatedAt:'2026-09-28T01:00:00Z'
    },
    negotiations:[{state:'ACTIVE',currentOfferArs:180000,floorPriceArs:140000,objections:['too expensive'],concessions:['split delivery'],nextAction:'counter offer',humanGate:false,humanGateReasons:[],lastContactAt:'2026-09-28T00:30:00Z',updatedAt:'2026-09-28T00:31:00Z'}],
    deliveries:[],
    payments:[],
    activity:[{stream:'NEGOTIATION',actor:'NEGOTIATOR',eventType:'NEGOTIATION_UPDATED',detail:{},createdAt:'2026-09-28T00:31:00Z'}],
    episodes:[{episodeId:'e1',agentRole:'NEGOTIATOR',tacticId:'demo-first',observation:'prospect objected to price',outcome:'REPLIED',audited:true,evidenceRefs:['mail:1'],createdAt:'2026-09-28T00:30:00Z'}],
    decisions:[{decisionId:'d1',selectedMove:'NEGOTIATE',selectedTacticId:'diagnostic-negotiation',selectedScore:.91,reasons:['ACTIVE_OBJECTION'],alternatives:[],createdAt:'2026-09-28T00:31:00Z'}]
  });
  assert.equal(dossier.caseId,'case-1');
  assert.equal(dossier.business.name,'Comercio Demo');
  assert.equal(dossier.evaluation.score,88);
  assert.equal(dossier.commercial.negotiations.length,1);
  assert.equal(dossier.cognition.decisions.length,1);
  assert.equal(dossier.memory.episodes.length,1);
  assert.deepEqual(dossier.evidence.refs,['audit:1','maps:1']);
});

test('case dossier keeps observed evidence separate from inferred commercial recommendation', () => {
  const dossier = buildCaseEvaluation({
    opportunity: {
      id:'case-2', businessId:'biz-2', businessName:'Demo 2', category:'services', locality:'Santa Fe',
      status:'QUALIFIED', score:70, reasons:['NO_CRM'],
      offer:{primary:['CRM'],secondary:[],why:['CRM: no CRM signal detected']},
      persuasion:{observedFacts:['No CRM signal was detected.'],demoBrief:'crm demo',quantifiedClaim:null,rules:['NO_FABRICATED_UPLIFT']},
      contacts:[], evidenceRefs:['source:1'], nextOwner:'DEMO', nextAction:'BUILD_DEMO',
      createdAt:'2026-09-28T00:00:00Z', updatedAt:'2026-09-28T00:00:00Z'
    },
    negotiations:[], deliveries:[], payments:[], activity:[], episodes:[], decisions:[]
  });
  assert.deepEqual(dossier.evidence.observedFacts,['No CRM signal was detected.']);
  assert.deepEqual(dossier.recommendation.primary,['CRM']);
  assert.equal(dossier.recommendation.isInference,true);
});

import {
  rankPortfolioCases,
  planGlobalFocus,
  buildGlobalTypedQuestions,
  interpretGlobalSystemOne
} from '../dist/packages/sniper/src/globalCore.js';

const globalCases = [
  {caseId:'a',status:'QUALIFIED',score:91,evidenceCount:7,contactable:true,demoReady:false,humanGate:false,daysIdle:1,strategicTags:['retail'],auditedWinRate:.55},
  {caseId:'b',status:'NEGOTIATING',score:78,evidenceCount:9,contactable:true,demoReady:true,humanGate:false,daysIdle:2,strategicTags:['services'],auditedWinRate:.72},
  {caseId:'c',status:'DEFERRED',score:96,evidenceCount:1,contactable:false,demoReady:false,humanGate:false,daysIdle:9,strategicTags:['retail'],auditedWinRate:.10}
];

test('global core ranks whole portfolio, not one case in isolation', () => {
  const ranked = rankPortfolioCases(globalCases, {preferredTags:['retail'],maxConcurrentCases:2,minEvidenceCount:2});
  assert.equal(ranked.length,3);
  assert.equal(ranked[0].caseId,'a');
  assert.ok(ranked[0].globalScore > ranked[2].globalScore);
  assert.ok(ranked[2].reasons.includes('INSUFFICIENT_EVIDENCE'));
});

test('global core allocates limited attention across cases deterministically', () => {
  const plan = planGlobalFocus(globalCases,{preferredTags:[],maxConcurrentCases:2,minEvidenceCount:2});
  assert.equal(plan.active.length,2);
  assert.equal(plan.deferred.length,1);
  assert.equal(new Set(plan.active.map(x=>x.caseId)).size,2);
  assert.ok(plan.active.every(x=>x.ownerRole && x.nextObjective));
});

test('global core emits typed System-1 questions suitable for Laya-like decision engines', () => {
  const questions=buildGlobalTypedQuestions(globalCases[0]);
  assert.equal(questions.priority.type,'score');
  assert.equal(questions.route.type,'choice');
  assert.equal(questions.human_attention.type,'noul');
  assert.ok(Object.keys(questions.route.criteria).includes('DEMO'));
});

test('global core respects calibrated abstention from System-1 layer', () => {
  const result=interpretGlobalSystemOne({
    answers:{
      route:{choice:'OUTREACH',probabilities:{OUTREACH:.31,DEMO:.30,RESEARCH:.22,NEGOTIATE:.17},answer_confidence:.31},
      priority:{score:2.2,answer_confidence:.88},
      human_attention:{noul:.12,answer_confidence:.91}
    }
  },.60);
  assert.equal(result.route,null);
  assert.equal(result.abstained,true);
  assert.ok(result.reasons.includes('LOW_CONFIDENCE_ROUTE'));
});

test('global planning never activates a case with material human gate for autonomous execution', () => {
  const cases=[...globalCases,{caseId:'d',status:'NEGOTIATING',score:99,evidenceCount:10,contactable:true,demoReady:true,humanGate:true,daysIdle:0,strategicTags:['retail'],auditedWinRate:.9}];
  const plan=planGlobalFocus(cases,{preferredTags:['retail'],maxConcurrentCases:3,minEvidenceCount:2});
  assert.equal(plan.active.some(x=>x.caseId==='d'),false);
  assert.equal(plan.humanAttention.some(x=>x.caseId==='d'),true);
});

import {
  ORCHESTRATION_REFERENCES,
  getAdoptedPatterns,
  assertSingleRuntimeAuthority
} from '../dist/packages/sniper/src/orchestrationRegistry.js';

test('orchestration registry corrects canonical Swarms repository', () => {
  const swarms=ORCHESTRATION_REFERENCES.find(x=>x.id==='SWARMS');
  assert.equal(swarms.source,'https://github.com/kyegomez/swarms');
  assert.equal(swarms.license,'Apache-2.0');
});

test('AutoGen is reference-only because upstream marks it maintenance mode', () => {
  const autogen=ORCHESTRATION_REFERENCES.find(x=>x.id==='AUTOGEN');
  assert.equal(autogen.adoption,'REFERENCE_ONLY');
  assert.ok(autogen.notes.some(x=>x.includes('maintenance mode')));
});

test('topic pages and tutorial repos cannot become runtime authority', () => {
  const topic=ORCHESTRATION_REFERENCES.find(x=>x.id==='AI_MARKETING_TOPIC');
  const tutorial=ORCHESTRATION_REFERENCES.find(x=>x.id==='AI_AGENTS_101');
  assert.equal(topic.adoption,'DISCOVERY_ONLY');
  assert.equal(tutorial.adoption,'REFERENCE_ONLY');
});

test('registry adopts patterns without creating competing orchestrators', () => {
  const patterns=getAdoptedPatterns();
  assert.ok(patterns.includes('HIERARCHICAL_AGENT_OWNERSHIP'));
  assert.ok(patterns.includes('DURABLE_STATE_GRAPH'));
  assert.ok(patterns.includes('EVENT_DRIVEN_FLOWS'));
  assert.doesNotThrow(()=>assertSingleRuntimeAuthority(ORCHESTRATION_REFERENCES));
});

test('global core remains the only runtime orchestration authority', () => {
  const runtime=ORCHESTRATION_REFERENCES.filter(x=>x.adoption==='RUNTIME_AUTHORITY');
  assert.deepEqual(runtime.map(x=>x.id),['ARIA_GLOBAL_CORE']);
});

import {
  OPERATING_STAGES,
  mapCaseToOperatingStage,
  buildAgencyOperationsSnapshot,
  requiredEffectClass
} from '../dist/packages/sniper/src/operatingModel.js';

test('agency operating model has exactly five canonical stages', () => {
  assert.deepEqual(OPERATING_STAGES.map(x=>x.id),['ANALYZE','PROSPECT','EXECUTE','DELIVER','COLLECT']);
});

test('case status maps deterministically into one operating stage', () => {
  assert.equal(mapCaseToOperatingStage('DISCOVERED'),'ANALYZE');
  assert.equal(mapCaseToOperatingStage('QUALIFIED'),'ANALYZE');
  assert.equal(mapCaseToOperatingStage('CONTACTED'),'PROSPECT');
  assert.equal(mapCaseToOperatingStage('NEGOTIATING'),'PROSPECT');
  assert.equal(mapCaseToOperatingStage('WON'),'EXECUTE');
  assert.equal(mapCaseToOperatingStage('DELIVERING'),'DELIVER');
  assert.equal(mapCaseToOperatingStage('DELIVERED'),'COLLECT');
});

test('external side effects are explicit and never owned directly by specialist agents', () => {
  assert.equal(requiredEffectClass('SEND_OUTREACH'),'SEND_EXTERNAL');
  assert.equal(requiredEffectClass('DEPLOY_CUSTOMER_WORK'),'DEPLOY');
  assert.equal(requiredEffectClass('CREATE_PAYMENT_REQUEST'),'MONEY_MUTATION');
  assert.equal(requiredEffectClass('ISSUE_INVOICE'),'MONEY_MUTATION');
});

test('agency operations snapshot groups cases by operational workstream', () => {
  const snapshot=buildAgencyOperationsSnapshot([
    {caseId:'a',businessName:'A',status:'QUALIFIED',owner:'MARKET_RESEARCH',nextAction:'BENCHMARK',score:90},
    {caseId:'b',businessName:'B',status:'NEGOTIATING',owner:'NEGOTIATOR',nextAction:'COUNTER',score:82},
    {caseId:'c',businessName:'C',status:'WON',owner:'WEB',nextAction:'BUILD',score:75},
    {caseId:'d',businessName:'D',status:'DELIVERING',owner:'DELIVERY',nextAction:'QA',score:71},
    {caseId:'e',businessName:'E',status:'DELIVERED',owner:'PAYMENTS',nextAction:'COLLECT',score:70}
  ]);
  assert.equal(snapshot.ANALYZE.length,1);
  assert.equal(snapshot.PROSPECT.length,1);
  assert.equal(snapshot.EXECUTE.length,1);
  assert.equal(snapshot.DELIVER.length,1);
  assert.equal(snapshot.COLLECT.length,1);
});

import {
  evaluateCommercialPolicy,
  DEFAULT_COMMERCIAL_CONTACT_LIMITS
} from '../dist/packages/sniper/src/commercialPolicy.js';

test('commercial policy permits evidence-backed targeted outreach', () => {
  const result=evaluateCommercialPolicy({
    action:'SEND_OUTREACH',
    explicitRefusal:false,
    optOut:false,
    autonomousContactsInWindow:0,
    hoursSinceLastContact:999,
    contactProvenance:'PUBLIC_BUSINESS_LISTING',
    claimsSupported:true,
    falseUrgency:false,
    humanImpersonation:false,
    bulkBlast:false,
    acceptedOffer:false,
    customerApproval:false,
    paymentVerified:false
  });
  assert.equal(result.decision,'ALLOW');
});

test('commercial policy permanently stops autonomous outreach after explicit refusal or opt-out', () => {
  for(const key of ['explicitRefusal','optOut']){
    const input={
      action:'SEND_OUTREACH',
      explicitRefusal:false,
      optOut:false,
      autonomousContactsInWindow:0,
      hoursSinceLastContact:999,
      contactProvenance:'PUBLIC_BUSINESS_LISTING',
      claimsSupported:true,
      falseUrgency:false,
      humanImpersonation:false,
      bulkBlast:false,
      acceptedOffer:false,
      customerApproval:false,
      paymentVerified:false
    };
    input[key]=true;
    const result=evaluateCommercialPolicy(input);
    assert.equal(result.decision,'DENY');
    assert.ok(result.reasons.includes('DO_NOT_CONTACT'));
  }
});

test('commercial policy rejects blast outreach and coercive or fabricated claims', () => {
  const unsafe=[
    {bulkBlast:true},
    {falseUrgency:true},
    {claimsSupported:false},
    {humanImpersonation:true}
  ];
  for(const patch of unsafe){
    const result=evaluateCommercialPolicy({
      action:'SEND_OUTREACH',
      explicitRefusal:false,
      optOut:false,
      autonomousContactsInWindow:0,
      hoursSinceLastContact:999,
      contactProvenance:'PUBLIC_BUSINESS_LISTING',
      claimsSupported:true,
      falseUrgency:false,
      humanImpersonation:false,
      bulkBlast:false,
      acceptedOffer:false,
      customerApproval:false,
      paymentVerified:false,
      ...patch
    });
    assert.equal(result.decision,'DENY');
  }
});

test('commercial policy enforces autonomous contact fatigue limits', () => {
  const result=evaluateCommercialPolicy({
    action:'SEND_OUTREACH',
    explicitRefusal:false,
    optOut:false,
    autonomousContactsInWindow:DEFAULT_COMMERCIAL_CONTACT_LIMITS.maxAutonomousContacts,
    hoursSinceLastContact:DEFAULT_COMMERCIAL_CONTACT_LIMITS.minHoursBetweenContacts,
    contactProvenance:'PUBLIC_BUSINESS_LISTING',
    claimsSupported:true,
    falseUrgency:false,
    humanImpersonation:false,
    bulkBlast:false,
    acceptedOffer:false,
    customerApproval:false,
    paymentVerified:false
  });
  assert.equal(result.decision,'DENY');
  assert.ok(result.reasons.includes('CONTACT_FATIGUE_LIMIT'));
});

test('commercial policy requires explicit commercial acceptance before payment request', () => {
  const denied=evaluateCommercialPolicy({
    action:'CREATE_PAYMENT_REQUEST',
    explicitRefusal:false,optOut:false,autonomousContactsInWindow:0,hoursSinceLastContact:999,
    contactProvenance:'OWNER_PROVIDED',claimsSupported:true,falseUrgency:false,humanImpersonation:false,bulkBlast:false,
    acceptedOffer:false,customerApproval:false,paymentVerified:false
  });
  assert.equal(denied.decision,'DENY');
  const allowed=evaluateCommercialPolicy({
    action:'CREATE_PAYMENT_REQUEST',
    explicitRefusal:false,optOut:false,autonomousContactsInWindow:0,hoursSinceLastContact:999,
    contactProvenance:'OWNER_PROVIDED',claimsSupported:true,falseUrgency:false,humanImpersonation:false,bulkBlast:false,
    acceptedOffer:true,customerApproval:false,paymentVerified:false
  });
  assert.equal(allowed.decision,'ALLOW');
});

test('commercial policy requires customer approval for deploy and verified payment for invoice', () => {
  assert.equal(evaluateCommercialPolicy({
    action:'DEPLOY_CUSTOMER_WORK',
    explicitRefusal:false,optOut:false,autonomousContactsInWindow:0,hoursSinceLastContact:999,
    contactProvenance:'OWNER_PROVIDED',claimsSupported:true,falseUrgency:false,humanImpersonation:false,bulkBlast:false,
    acceptedOffer:true,customerApproval:false,paymentVerified:false
  }).decision,'DENY');
  assert.equal(evaluateCommercialPolicy({
    action:'ISSUE_INVOICE',
    explicitRefusal:false,optOut:false,autonomousContactsInWindow:0,hoursSinceLastContact:999,
    contactProvenance:'OWNER_PROVIDED',claimsSupported:true,falseUrgency:false,humanImpersonation:false,bulkBlast:false,
    acceptedOffer:true,customerApproval:true,paymentVerified:false
  }).decision,'DENY');
});

import {
  OBSERVABILITY_REFERENCES,
  normalizeTelemetrySpan,
  buildTraceTree,
  summarizeTelemetry,
  assertSingleTelemetryAuthority
} from '../dist/packages/sniper/src/telemetry.js';

test('telemetry fabric is the single runtime authority', () => {
  const runtime=OBSERVABILITY_REFERENCES.filter(x=>x.adoption==='RUNTIME_AUTHORITY');
  assert.deepEqual(runtime.map(x=>x.id),['ARIA_TELEMETRY_FABRIC']);
  assert.doesNotThrow(()=>assertSingleTelemetryAuthority(OBSERVABILITY_REFERENCES));
});

test('observability registry rejects archived or license-conflicting runtime choices', () => {
  assert.equal(OBSERVABILITY_REFERENCES.find(x=>x.id==='FLOWISE')?.adoption,'REJECT');
  assert.equal(OBSERVABILITY_REFERENCES.find(x=>x.id==='DIFY')?.adoption,'REFERENCE_ONLY');
  assert.equal(OBSERVABILITY_REFERENCES.find(x=>x.id==='PHOENIX')?.adoption,'REFERENCE_ONLY');
  assert.equal(OBSERVABILITY_REFERENCES.find(x=>x.id==='AUTOGEN_STUDIO')?.adoption,'REJECT');
});

test('telemetry spans store metadata by default and reject paid execution', () => {
  const span=normalizeTelemetrySpan({
    traceId:'tr1',spanId:'sp1',parentSpanId:null,caseId:'case-1',agentRole:'NEGOTIATOR',
    stage:'PROSPECT',kind:'AGENT',operation:'HANDLE_OBJECTION',status:'OK',
    startedAt:'2026-09-28T12:00:00.000Z',endedAt:'2026-09-28T12:00:01.250Z',
    provider:'cloudflare',model:'free-model',inputTokens:100,outputTokens:40,actualCostUsd:0,
    errorCode:null,inputDigest:'sha256:a',outputDigest:'sha256:b',attributes:{tactic:'demo-first'}
  });
  assert.equal(span.latencyMs,1250);
  assert.equal(span.contentPolicy,'METADATA_ONLY');
  assert.equal('rawPrompt' in span,false);
  assert.throws(()=>normalizeTelemetrySpan({...span,actualCostUsd:.01}),/TELEMETRY_PAID_EXECUTION_FORBIDDEN/);
});

test('trace tree preserves parent-child agent and tool relationships', () => {
  const spans=[
    normalizeTelemetrySpan({traceId:'t',spanId:'root',parentSpanId:null,caseId:'c',agentRole:'ORCHESTRATOR',stage:'ANALYZE',kind:'AGENT',operation:'PLAN',status:'OK',startedAt:'2026-09-28T00:00:00Z',endedAt:'2026-09-28T00:00:01Z',provider:null,model:null,inputTokens:0,outputTokens:0,actualCostUsd:0,errorCode:null,inputDigest:null,outputDigest:null,attributes:{}}),
    normalizeTelemetrySpan({traceId:'t',spanId:'child',parentSpanId:'root',caseId:'c',agentRole:'SCOUT',stage:'ANALYZE',kind:'TOOL',operation:'CRAWL',status:'OK',startedAt:'2026-09-28T00:00:00.100Z',endedAt:'2026-09-28T00:00:00.700Z',provider:null,model:null,inputTokens:0,outputTokens:0,actualCostUsd:0,errorCode:null,inputDigest:null,outputDigest:null,attributes:{}})
  ];
  const tree=buildTraceTree(spans);
  assert.equal(tree.length,1);
  assert.equal(tree[0].children[0].span.spanId,'child');
});

test('telemetry summary exposes health, latency, tokens, errors and zero spend', () => {
  const spans=[
    normalizeTelemetrySpan({traceId:'t1',spanId:'a',parentSpanId:null,caseId:'c1',agentRole:'SALES',stage:'PROSPECT',kind:'LLM',operation:'DRAFT',status:'OK',startedAt:'2026-09-28T00:00:00Z',endedAt:'2026-09-28T00:00:01Z',provider:'cf',model:'m1',inputTokens:100,outputTokens:50,actualCostUsd:0,errorCode:null,inputDigest:null,outputDigest:null,attributes:{}}),
    normalizeTelemetrySpan({traceId:'t2',spanId:'b',parentSpanId:null,caseId:'c2',agentRole:'WEB',stage:'EXECUTE',kind:'TOOL',operation:'BUILD',status:'ERROR',startedAt:'2026-09-28T00:00:00Z',endedAt:'2026-09-28T00:00:02Z',provider:null,model:null,inputTokens:0,outputTokens:0,actualCostUsd:0,errorCode:'BUILD_FAILED',inputDigest:null,outputDigest:null,attributes:{}})
  ];
  const summary=summarizeTelemetry(spans);
  assert.equal(summary.spans,2);
  assert.equal(summary.errors,1);
  assert.equal(summary.inputTokens,100);
  assert.equal(summary.outputTokens,50);
  assert.equal(summary.actualCostUsd,0);
  assert.equal(summary.p95LatencyMs,2000);
});

import {
  SKILL_SOURCE_CANDIDATES,
  evaluateSkillAdmission,
  skillCanHandle
} from '../dist/packages/sniper/src/skillRegistry.js';

test('verified skill sources are catalogued but not auto-enabled without revision pin', () => {
  const source=SKILL_SOURCE_CANDIDATES.find(x=>x.id==='COREY_MARKETING_SKILLS');
  assert.equal(source?.license,'MIT');
  assert.equal(source?.sourceVerified,true);
  assert.equal(source?.revisionPin,null);
  const admission=evaluateSkillAdmission(source);
  assert.equal(admission.state,'QUARANTINED');
  assert.ok(admission.reasons.includes('REVISION_PIN_REQUIRED'));
});

test('skill admission rejects paid, unknown-license and direct-write capabilities', () => {
  const base={...SKILL_SOURCE_CANDIDATES[0],revisionPin:'deadbeef',license:'MIT',sourceVerified:true,costClass:'FREE_VERIFIED',networkPermission:'PUBLIC_READ',benchmarkScore:.9,health:'HEALTHY'};
  assert.equal(evaluateSkillAdmission({...base,costClass:'PAID'}).state,'REJECTED');
  assert.equal(evaluateSkillAdmission({...base,license:null}).state,'REJECTED');
  assert.equal(evaluateSkillAdmission({...base,networkPermission:'EXTERNAL_WRITE'}).state,'REJECTED');
});

test('skill admission enables only pinned, healthy, benchmarked zero-cost sources', () => {
  const candidate={...SKILL_SOURCE_CANDIDATES[0],revisionPin:'abc123',license:'MIT',sourceVerified:true,costClass:'FREE_VERIFIED',networkPermission:'PUBLIC_READ',benchmarkScore:.82,health:'HEALTHY'};
  const admission=evaluateSkillAdmission(candidate);
  assert.equal(admission.state,'ENABLED');
});

test('skill compatibility enforces role and data class', () => {
  const candidate={...SKILL_SOURCE_CANDIDATES[0],revisionPin:'abc123',license:'MIT',sourceVerified:true,costClass:'FREE_VERIFIED',networkPermission:'PUBLIC_READ',benchmarkScore:.82,health:'HEALTHY'};
  assert.equal(skillCanHandle(candidate,'COPY','PUBLIC'),true);
  assert.equal(skillCanHandle(candidate,'WEB','SECRET'),false);
});

import {
  evaluateDiscoveryJob,
  dedupeBusinessFindings,
  findingToBusinessSignal
} from '../dist/packages/sniper/src/discovery.js';

const publicSource={
  id:'PUBLIC_DIRECTORY',
  freeVerified:true,
  termsVerified:true,
  automatedAccessAllowed:true,
  publicBusinessDataOnly:true
};

test('discovery job requires zero-cost, terms-verified automated sources', () => {
  const ok=evaluateDiscoveryJob({
    jobId:'j1',locality:'Rafaela, Santa Fe',categories:['veterinaria'],maxCandidates:100,
    sources:[publicSource],createdAt:'2026-09-28T00:00:00Z'
  });
  assert.equal(ok.allowed,true);
  const denied=evaluateDiscoveryJob({
    jobId:'j2',locality:'Rafaela, Santa Fe',categories:['veterinaria'],maxCandidates:100,
    sources:[{...publicSource,freeVerified:false}],createdAt:'2026-09-28T00:00:00Z'
  });
  assert.equal(denied.allowed,false);
  assert.ok(denied.reasons.includes('SOURCE_ZERO_COST_NOT_VERIFIED'));
});

test('discovery dedupes the same business across public sources', () => {
  const findings=dedupeBusinessFindings([
    {sourceId:'A',sourceRef:'a:1',name:'Demo SRL',category:'retail',locality:'Rafaela',websiteUrl:'https://demo.example',businessContacts:[{kind:'EMAIL',value:'ventas@demo.example',provenance:'PUBLIC_BUSINESS_LISTING'}],rating:4.5,reviewCount:20,observedAt:'2026-09-28T00:00:00Z'},
    {sourceId:'B',sourceRef:'b:9',name:'DEMO S.R.L.',category:'retail',locality:'Rafaela',websiteUrl:'https://www.demo.example/',businessContacts:[{kind:'EMAIL',value:'ventas@demo.example',provenance:'BUSINESS_WEBSITE'}],rating:4.6,reviewCount:30,observedAt:'2026-09-28T00:01:00Z'}
  ]);
  assert.equal(findings.length,1);
  assert.equal(findings[0].evidenceRefs.length,2);
});

test('discovery creates evidence-grounded business signal without private personal enrichment', () => {
  const signal=findingToBusinessSignal({
    sourceId:'DIR',sourceRef:'dir:1',name:'Negocio Demo',category:'aberturas',locality:'Santo Tomé',
    websiteUrl:'https://negocio.example',
    businessContacts:[{kind:'WHATSAPP',value:'+543420000000',provenance:'PUBLIC_BUSINESS_LISTING'}],
    rating:4.7,reviewCount:100,observedAt:'2026-09-28T00:00:00Z'
  },{
    evidenceRef:'audit:1',httpOk:true,performanceScore:38,accessibilityScore:70,mobileReadabilityScore:42,
    ecommerce:false,crm:null,whatsappAutomation:false,socialActive:true,booking:false,paymentsOnline:false,analytics:false
  });
  assert.equal(signal.locality,'Santo Tomé');
  assert.equal(signal.digital.ecommerce,false);
  assert.equal(signal.contacts.length,1);
  assert.equal(signal.contacts[0].provenance,'PUBLIC_BUSINESS_LISTING');
  assert.ok(signal.digital.websiteQuality < 60);
  assert.equal('ownerPersonalPhone' in signal,false);
});

import {
  DISCOVERY_SOURCE_CANDIDATES,
  evaluateDiscoverySourceAdmission,
  selectDiscoverySources
} from '../dist/packages/sniper/src/discoverySources.js';

test('discovery source registry separates library license from target-site permission', () => {
  const crawl=DISCOVERY_SOURCE_CANDIDATES.find(x=>x.id==='CRAWL4AI_SELF_HOSTED');
  assert.equal(crawl?.license,'Apache-2.0');
  assert.equal(crawl?.runtimeCost,'FREE_SELF_HOSTED');
  assert.equal(crawl?.targetTermsVerified,false);
  assert.equal(evaluateDiscoverySourceAdmission(crawl).state,'QUARANTINED');
});

test('paid hosted browser path is rejected under zero-spend invariant', () => {
  const hosted=DISCOVERY_SOURCE_CANDIDATES.find(x=>x.id==='BROWSER_USE_CLOUD');
  const admission=evaluateDiscoverySourceAdmission(hosted);
  assert.equal(admission.state,'REJECTED');
  assert.ok(admission.reasons.includes('PAID_RUNTIME_FORBIDDEN'));
});

test('self-hosted crawlers remain quarantined until revision and target terms are pinned', () => {
  for(const id of ['CRAWL4AI_SELF_HOSTED','BROWSER_USE_SELF_HOSTED','SCRAPLING_SELF_HOSTED']){
    const src=DISCOVERY_SOURCE_CANDIDATES.find(x=>x.id===id);
    assert.equal(evaluateDiscoverySourceAdmission(src).state,'QUARANTINED');
  }
});

test('source selection returns only enabled sources matching capability and locality scope', () => {
  const synthetic=DISCOVERY_SOURCE_CANDIDATES.map(x=>x.id==='SCRAPLING_SELF_HOSTED'?{
    ...x,revisionPin:'abc1234',zeroCostVerified:true,targetTermsVerified:true,automationAllowed:true,health:'HEALTHY'
  }:x);
  const selected=selectDiscoverySources(synthetic,{capability:'PUBLIC_WEB_AUDIT',locality:'Santa Fe'});
  assert.deepEqual(selected.map(x=>x.id),['SCRAPLING_SELF_HOSTED']);
});

import {
  evaluateDemoJob,
  buildDemoArtifactManifest,
  chooseDemoExecutorClass
} from '../dist/packages/sniper/src/demoJobs.js';

test('demo job requires a case, evidence, service pack and private preview', () => {
  const decision=evaluateDemoJob({
    jobId:'demo-1',caseId:'case-1',servicePackId:'OPENINGS_COMMERCE',
    evidenceRefs:['audit:1'],requestedDeliverables:['VISUAL_CONFIGURATOR'],
    privatePreview:true,productionDeploy:false,executorId:'oracle-free-1',
    executorCostVerifiedZero:true,createdAt:'2026-09-28T00:00:00Z'
  });
  assert.equal(decision.allowed,true);
});

test('demo job denies production deployment and paid executor', () => {
  const base={
    jobId:'demo-2',caseId:'case-1',servicePackId:'LOCAL_COMMERCE_DIGITAL',
    evidenceRefs:['audit:1'],requestedDeliverables:['HIGH_CONVERSION_WEBSITE'],
    privatePreview:true,productionDeploy:false,executorId:'cloud-x',
    executorCostVerifiedZero:true,createdAt:'2026-09-28T00:00:00Z'
  };
  assert.equal(evaluateDemoJob({...base,productionDeploy:true}).allowed,false);
  assert.equal(evaluateDemoJob({...base,executorCostVerifiedZero:false}).allowed,false);
});

test('demo executor class routes 3d work away from normal worker execution', () => {
  assert.equal(chooseDemoExecutorClass(['HIGH_CONVERSION_WEBSITE']),'WEB_BUILD');
  assert.equal(chooseDemoExecutorClass(['EMBEDDABLE_3D_TOUR']),'HEAVY_3D');
  assert.equal(chooseDemoExecutorClass(['VISUAL_CONFIGURATOR']),'BROWSER_3D');
});

test('demo artifact manifest remains private and auditable', () => {
  const manifest=buildDemoArtifactManifest({
    jobId:'demo-3',caseId:'case-3',servicePackId:'REAL_ESTATE_IMMERSIVE',
    evidenceRefs:['photo:1','audit:2'],requestedDeliverables:['EMBEDDABLE_3D_TOUR'],
    privatePreview:true,productionDeploy:false,executorId:'oracle-free-1',
    executorCostVerifiedZero:true,createdAt:'2026-09-28T00:00:00Z'
  },[
    {kind:'WEB_PREVIEW',ref:'artifact:web:1',digest:'sha256:abc'}
  ]);
  assert.equal(manifest.visibility,'PRIVATE');
  assert.equal(manifest.production,false);
  assert.deepEqual(manifest.evidenceRefs,['photo:1','audit:2']);
  assert.equal(manifest.auditRequired,true);
});

import {
  EXECUTOR_CANDIDATES,
  evaluateExecutorAdmission,
  selectExecutor
} from '../dist/packages/sniper/src/executorRegistry.js';

test('cloudflare control plane is not treated as heavy build executor', () => {
  const cf=EXECUTOR_CANDIDATES.find(x=>x.id==='CLOUDFLARE_CONTROL');
  assert.equal(cf?.capabilities.includes('HEAVY_3D'),false);
  assert.equal(cf?.role,'CONTROL_PLANE');
});

test('oracle free executor remains quarantined until endpoint and health are verified', () => {
  const oracle=EXECUTOR_CANDIDATES.find(x=>x.id==='ORACLE_FREE_EXECUTOR');
  const admission=evaluateExecutorAdmission(oracle);
  assert.equal(admission.state,'QUARANTINED');
  assert.ok(admission.reasons.includes('ENDPOINT_REQUIRED'));
  assert.ok(admission.reasons.includes('HEALTH_NOT_VERIFIED'));
});

test('executor admission rejects billable runtime', () => {
  const oracle=EXECUTOR_CANDIDATES.find(x=>x.id==='ORACLE_FREE_EXECUTOR');
  const admission=evaluateExecutorAdmission({...oracle,costClass:'PAID',endpoint:'https://executor.example',health:'HEALTHY'});
  assert.equal(admission.state,'REJECTED');
});

test('verified oracle executor may handle web browser and heavy 3d classes', () => {
  const oracle={...EXECUTOR_CANDIDATES.find(x=>x.id==='ORACLE_FREE_EXECUTOR'),endpoint:'https://oracle.example',health:'HEALTHY',zeroCostVerified:true};
  assert.equal(evaluateExecutorAdmission(oracle).state,'ENABLED');
  assert.equal(selectExecutor([oracle],'WEB_BUILD')?.id,'ORACLE_FREE_EXECUTOR');
  assert.equal(selectExecutor([oracle],'BROWSER_3D')?.id,'ORACLE_FREE_EXECUTOR');
  assert.equal(selectExecutor([oracle],'HEAVY_3D')?.id,'ORACLE_FREE_EXECUTOR');
});

import {
  smoothedOutcomeRate,
  applySemanticObservation
} from '../dist/packages/sniper/src/learning.js';

test('contextual audited outcome rate is neutral with no evidence and resists one-shot overfitting', () => {
  assert.equal(smoothedOutcomeRate(0,0),0.5);
  assert.equal(smoothedOutcomeRate(1,0),2/3);
  assert.equal(smoothedOutcomeRate(0,1),1/3);
  assert.ok(smoothedOutcomeRate(8,2)>smoothedOutcomeRate(2,2));
});

test('semantic memory requires repeated audited support before verification', () => {
  let p={patternId:'p1',scopeKey:'category:retail',statement:'demo-first performs well',supportCount:0,contradictionCount:0,confidence:.5,status:'CANDIDATE'};
  p=applySemanticObservation(p,{supports:true,audited:true});
  assert.equal(p.status,'CANDIDATE');
  p=applySemanticObservation(p,{supports:true,audited:true});
  p=applySemanticObservation(p,{supports:true,audited:true});
  assert.equal(p.status,'VERIFIED');
  assert.ok(p.confidence>=.7);
});

test('unaudited semantic observation cannot alter durable pattern', () => {
  const p={patternId:'p1',scopeKey:'category:retail',statement:'demo-first performs well',supportCount:3,contradictionCount:0,confidence:.8,status:'VERIFIED'};
  assert.deepEqual(applySemanticObservation(p,{supports:false,audited:false}),p);
});

test('contradictions can demote a previously verified semantic pattern', () => {
  let p={patternId:'p1',scopeKey:'category:retail',statement:'demo-first performs well',supportCount:3,contradictionCount:0,confidence:.8,status:'VERIFIED'};
  p=applySemanticObservation(p,{supports:false,audited:true});
  p=applySemanticObservation(p,{supports:false,audited:true});
  p=applySemanticObservation(p,{supports:false,audited:true});
  assert.notEqual(p.status,'VERIFIED');
});

import {
  createExecutorEnvelope,
  verifyExecutorEnvelope,
  validateExecutorResult,
  executorRequestPath
} from '../dist/packages/sniper/src/executorProtocol.js';

test('executor protocol only exposes typed job kinds and a fixed request path', async () => {
  const env=await createExecutorEnvelope({
    runId:'run-1',executorId:'ORACLE_FREE_EXECUTOR',jobKind:'DEMO_WEB_BUILD',
    jobId:'demo-1',caseId:'case-1',payload:{businessName:'Demo Aberturas',category:'aberturas',locality:'Santa Fe',servicePackId:'OPENINGS_COMMERCE',requestedDeliverables:['VISUAL_CONFIGURATOR'],evidenceRefs:['evidence:audit:1'],observedFacts:['catalog is hard to scan on mobile'],demoBrief:'Show a private visual configurator proof.'},
    artifactInputRefs:['evidence:audit:1'],issuedAt:'2026-09-30T10:00:00.000Z',
    expiresAt:'2026-09-30T10:10:00.000Z',nonce:'nonce-12345678'
  },'test-secret');
  assert.equal(env.body.expectedCostUsd,0);
  assert.equal(executorRequestPath(env.body.jobKind),'/v1/jobs/demo-web-build');
  assert.equal('command' in env.body,false);
  assert.equal('shell' in env.body,false);
});

test('executor envelope validates HMAC and expiration', async () => {
  const signed=await createExecutorEnvelope({
    runId:'run-2',executorId:'ORACLE_FREE_EXECUTOR',jobKind:'DISCOVERY_WEB_AUDIT',
    jobId:'discovery-1',caseId:null,payload:{targetUrl:'https://example.test',auditProfile:'PUBLIC_BUSINESS_WEB'},
    artifactInputRefs:['url:https://example.test'],issuedAt:'2026-09-30T10:00:00.000Z',
    expiresAt:'2026-09-30T10:10:00.000Z',nonce:'nonce-abcdefgh'
  },'test-secret');
  assert.equal(await verifyExecutorEnvelope(signed,'test-secret','2026-09-30T10:05:00.000Z'),true);
  assert.equal(await verifyExecutorEnvelope(signed,'wrong-secret','2026-09-30T10:05:00.000Z'),false);
  assert.equal(await verifyExecutorEnvelope(signed,'test-secret','2026-09-30T10:11:00.000Z'),false);
});

test('executor result rejects monetary spend and untyped artifacts', () => {
  const base={
    protocolVersion:'iaffice-executor-v1',runId:'run-3',executorId:'ORACLE_FREE_EXECUTOR',
    jobKind:'DEMO_WEB_BUILD',jobId:'demo-3',caseId:'case-3',state:'SUCCEEDED',
    actualCostUsd:0,artifacts:[{kind:'WEB_PREVIEW',ref:'artifact:web:3',digest:'sha256:ok'}],
    telemetry:{startedAt:'2026-09-30T10:00:00.000Z',endedAt:'2026-09-30T10:01:00.000Z',cpuMs:1000,memoryPeakMb:512},
    resultDigest:'sha256:result',errorCode:null
  };
  assert.equal(validateExecutorResult(base).ok,true);
  assert.equal(validateExecutorResult({...base,actualCostUsd:.01}).ok,false);
  assert.equal(validateExecutorResult({...base,artifacts:[{kind:'SHELL_OUTPUT',ref:'x',digest:'sha256:x'}]}).ok,false);
});

test('executor protocol rejects arbitrary job kinds', async () => {
  await assert.rejects(()=>createExecutorEnvelope({
    runId:'run-x',executorId:'ORACLE_FREE_EXECUTOR',jobKind:'ARBITRARY_SHELL',
    jobId:'x',caseId:null,payload:{},artifactInputRefs:[],
    issuedAt:'2026-09-30T10:00:00.000Z',expiresAt:'2026-09-30T10:10:00.000Z',nonce:'nonce-12345678'
  },'test-secret'),/EXECUTOR_JOB_KIND_INVALID/);
});

import {
  validateExecutorEndpoint,
  signExecutorResult,
  verifySignedExecutorResult,
  signArtifactRequest,
  verifyArtifactRequest
} from '../dist/packages/sniper/src/executorProtocol.js';

test('executor endpoint must be public https and cannot target localhost/private literal IPs', () => {
  assert.equal(validateExecutorEndpoint('https://executor.example.com').ok,true);
  assert.equal(validateExecutorEndpoint('http://executor.example.com').ok,false);
  assert.equal(validateExecutorEndpoint('https://localhost:8080').ok,false);
  assert.equal(validateExecutorEndpoint('https://127.0.0.1').ok,false);
  assert.equal(validateExecutorEndpoint('https://10.0.0.10').ok,false);
  assert.equal(validateExecutorEndpoint('https://192.168.1.2').ok,false);
  assert.equal(validateExecutorEndpoint('https://172.16.4.2').ok,false);
});

test('executor results are signed and signature verification fails after tampering', async () => {
  const result={
    protocolVersion:'iaffice-executor-v1',runId:'run-4',executorId:'ORACLE_FREE_EXECUTOR',
    jobKind:'DEMO_WEB_BUILD',jobId:'demo-4',caseId:'case-4',state:'SUCCEEDED',
    actualCostUsd:0,artifacts:[{kind:'WEB_PREVIEW',ref:'artifact:web:4',digest:'sha256:ok'}],
    telemetry:{startedAt:'2026-09-30T10:00:00.000Z',endedAt:'2026-09-30T10:01:00.000Z',cpuMs:1000,memoryPeakMb:512},
    resultDigest:'sha256:result',errorCode:null
  };
  const signed=await signExecutorResult(result,'test-secret');
  assert.equal(await verifySignedExecutorResult(signed,'test-secret'),true);
  signed.result.resultDigest='sha256:tampered';
  assert.equal(await verifySignedExecutorResult(signed,'test-secret'),false);
});

test('executor payload rejects command-like or unknown fields', async () => {
  await assert.rejects(()=>createExecutorEnvelope({
    runId:'run-p',executorId:'ORACLE_FREE_EXECUTOR',jobKind:'DEMO_WEB_BUILD',
    jobId:'demo-p',caseId:'case-p',
    payload:{businessName:'Demo Comercio',category:'retail',locality:'Santa Fe',servicePackId:'LOCAL_COMMERCE_DIGITAL',requestedDeliverables:['HIGH_CONVERSION_WEBSITE'],evidenceRefs:['audit:1'],observedFacts:['mobile CTA is difficult to find'],demoBrief:'Show a private mobile conversion proof.',command:'rm -rf /'},
    artifactInputRefs:['audit:1'],issuedAt:'2026-09-30T10:00:00.000Z',
    expiresAt:'2026-09-30T10:10:00.000Z',nonce:'nonce-payload-1'
  },'test-secret'),/EXECUTOR_PAYLOAD_INVALID/);
});

test('successful executor result requires at least one artifact', () => {
  const result=validateExecutorResult({
    protocolVersion:'iaffice-executor-v1',runId:'run-empty',executorId:'ORACLE_FREE_EXECUTOR',
    jobKind:'DEMO_WEB_BUILD',jobId:'demo-empty',caseId:'case-empty',state:'SUCCEEDED',
    actualCostUsd:0,artifacts:[],
    telemetry:{startedAt:'2026-09-30T10:00:00.000Z',endedAt:'2026-09-30T10:00:01.000Z',cpuMs:1,memoryPeakMb:1},
    resultDigest:'sha256:result',errorCode:null
  });
  assert.equal(result.ok,false);
  assert.ok(result.reasons.includes('SUCCEEDED_ARTIFACT_REQUIRED'));
});

test('private artifact request signatures are path-bound and time-bound', async () => {
  const path='/v1/artifacts/executor-run_abc/index.html';
  const ts=1790762400;
  const sig=await signArtifactRequest(path,ts,'test-secret');
  assert.equal(await verifyArtifactRequest(path,ts,sig,'test-secret',ts+60),true);
  assert.equal(await verifyArtifactRequest('/v1/artifacts/executor-run_abc/other.html',ts,sig,'test-secret',ts+60),false);
  assert.equal(await verifyArtifactRequest(path,ts,sig,'test-secret',ts+301),false);
});

import {
  contactProvenanceForTarget,
  acceptedCommercialState,
  approvedDeliveryState,
  verifiedPaymentState,
  commercialActionDigest,
  isExternalOperation
} from '../dist/packages/sniper/src/commercialGuard.js';

test('commercial guard resolves only exact public business contact provenance', () => {
  const contacts=[
    {kind:'EMAIL',value:'ventas@example.test',provenance:'BUSINESS_WEBSITE'},
    {kind:'WHATSAPP',value:'+54 342 555-0101',provenance:'PUBLIC_BUSINESS_LISTING'}
  ];
  assert.equal(contactProvenanceForTarget(contacts,'ventas@example.test'),'BUSINESS_WEBSITE');
  assert.equal(contactProvenanceForTarget(contacts,'+543425550101'),'PUBLIC_BUSINESS_LISTING');
  assert.equal(contactProvenanceForTarget(contacts,'private@example.test'),'UNKNOWN');
});

test('commercial guard derives acceptance approval and payment conservatively', () => {
  assert.equal(acceptedCommercialState('WON',null),true);
  assert.equal(acceptedCommercialState('NEGOTIATING','AGREED'),true);
  assert.equal(acceptedCommercialState('NEGOTIATING','ACTIVE'),false);
  assert.equal(approvedDeliveryState('IN_PROGRESS',{customerApproved:true}),true);
  assert.equal(approvedDeliveryState('IN_PROGRESS',{}),false);
  assert.equal(verifiedPaymentState('COLLECTED'),true);
  assert.equal(verifiedPaymentState('PENDING'),false);
});

test('commercial action digest is bound to case operation target and exact payload', async () => {
  const base={caseId:'case-1',operation:'SEND_OUTREACH',target:'ventas@example.test',payload:{subject:'A',body:'B'}};
  const a=await commercialActionDigest(base);
  const b=await commercialActionDigest({...base,payload:{subject:'A',body:'C'}});
  const d=await commercialActionDigest({...base,target:'otro@example.test'});
  assert.match(a,/^[a-f0-9]{64}$/);
  assert.notEqual(a,b);
  assert.notEqual(a,d);
});

test('commercial operation allowlist rejects arbitrary effect operation strings', () => {
  assert.equal(isExternalOperation('SEND_OUTREACH'),true);
  assert.equal(isExternalOperation('CREATE_PAYMENT_REQUEST'),true);
  assert.equal(isExternalOperation('ARBITRARY_SEND'),false);
});

test('marketing opt-out does not suppress a verified transactional receipt', () => {
  const result=evaluateCommercialPolicy({
    action:'SEND_RECEIPT',
    explicitRefusal:true,
    optOut:true,
    autonomousContactsInWindow:99,
    hoursSinceLastContact:0,
    contactProvenance:'OWNER_PROVIDED',
    claimsSupported:false,
    falseUrgency:true,
    humanImpersonation:true,
    bulkBlast:true,
    acceptedOffer:true,
    customerApproval:true,
    paymentVerified:true
  });
  assert.equal(result.decision,'ALLOW');
});

test('transactional receipt still requires verified payment', () => {
  const result=evaluateCommercialPolicy({
    action:'SEND_RECEIPT',
    explicitRefusal:false,optOut:false,autonomousContactsInWindow:0,hoursSinceLastContact:999,
    contactProvenance:'OWNER_PROVIDED',claimsSupported:true,falseUrgency:false,humanImpersonation:false,bulkBlast:false,
    acceptedOffer:true,customerApproval:true,paymentVerified:false
  });
  assert.equal(result.decision,'DENY');
  assert.ok(result.reasons.includes('PAYMENT_VERIFICATION_REQUIRED'));
});

import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { CommercialGuard } from '../dist/packages/sniper/src/commercialGuard.js';

class SqlitePreparedAdapter {
  constructor(db,sql){this.db=db;this.sql=sql;this.values=[]}
  bind(...values){this.values=values;return this}
  async first(){return this.db.prepare(this.sql).get(...this.values)??null}
  async all(){return {results:this.db.prepare(this.sql).all(...this.values)}}
  async run(){return this.db.prepare(this.sql).run(...this.values)}
}
class SqliteD1Adapter {
  constructor(db){this.db=db}
  prepare(sql){return new SqlitePreparedAdapter(this.db,sql)}
  async batch(statements){const out=[];for(const stmt of statements)out.push(await stmt.run());return out}
}
function commercialTestDb(){
  const raw=new DatabaseSync(':memory:');
  for(const file of fs.readdirSync('migrations').filter(x=>/^\d{4}_.+\.sql$/.test(x)).sort()){
    raw.exec(fs.readFileSync(path.join('migrations',file),'utf8'));
  }
  const db=new SqliteD1Adapter(raw);
  return {raw,db,guard:new CommercialGuard(db)};
}
function seedCommercialCase(raw,{id='case-commercial',status='DEMO_READY'}={}){
  const now='2026-09-30T12:00:00.000Z';
  const contacts=[
    {kind:'EMAIL',value:'ventas@example.test',provenance:'BUSINESS_WEBSITE'},
    {kind:'WHATSAPP',value:'+543425550101',provenance:'PUBLIC_BUSINESS_LISTING'}
  ];
  raw.prepare("INSERT INTO sniper_opportunities (id,business_id,business_name,category,locality,status,score,signal_json,reasons_json,offer_json,persuasion_json,contacts_json,evidence_refs_json,next_owner,next_action,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
    .run(id,'biz-'+id,'Comercio Test','retail','Santa Fe',status,80,'{}','[]','{"primary":["WEBSITE"],"secondary":[],"why":[]}','{"observedFacts":["CTA difficult to find"],"demoBrief":"private demo","quantifiedClaim":null,"rules":[]}',JSON.stringify(contacts),'["evidence:site"]','SALES','OUTREACH',now,now);
}

test('durable commercial guard allows only exact AUD-passed outreach then stops on opt-out', async () => {
  const {raw,guard}=commercialTestDb();
  seedCommercialCase(raw);
  const payload={subject:'Diagnóstico privado',body:'Adjunto una mejora basada en el sitio observado.'};
  const audit=await guard.recordCommercialAudit({
    caseId:'case-commercial',operation:'SEND_OUTREACH',target:'ventas@example.test',payload,
    verdict:'PASS',reason:'claims grounded; no false urgency; no human impersonation',evidenceRefs:['evidence:site']
  },'2026-09-30T12:05:00.000Z');
  const allowed=await guard.evaluate({
    caseId:'case-commercial',operation:'SEND_OUTREACH',target:'ventas@example.test',payload,auditId:audit.auditId
  },'2026-09-30T12:06:00.000Z');
  assert.equal(allowed.decision,'ALLOW');
  await guard.setContactControl({
    caseId:'case-commercial',doNotContact:true,explicitRefusal:false,reason:'recipient opted out',evidenceRefs:['reply:optout']
  },'2026-09-30T12:07:00.000Z');
  const denied=await guard.evaluate({
    caseId:'case-commercial',operation:'SEND_OUTREACH',target:'ventas@example.test',payload,auditId:audit.auditId
  },'2026-09-30T12:08:00.000Z');
  assert.equal(denied.decision,'DENY');
  assert.ok(denied.reasons.includes('DO_NOT_CONTACT'));
  raw.close();
});

test('durable commercial guard enforces cooldown from executed effects', async () => {
  const {raw,guard}=commercialTestDb();
  seedCommercialCase(raw,{id:'case-cooldown'});
  const payload={subject:'A',body:'B'};
  const audit=await guard.recordCommercialAudit({
    caseId:'case-cooldown',operation:'SEND_OUTREACH',target:'ventas@example.test',payload,
    verdict:'PASS',reason:'audited',evidenceRefs:['evidence:site']
  },'2026-09-30T10:00:00.000Z');
  await guard.recordExecuted({
    caseId:'case-cooldown',operation:'SEND_OUTREACH',target:'ventas@example.test',intentId:'intent-1',receiptId:'receipt-1'
  },'2026-09-30T10:30:00.000Z');
  const result=await guard.evaluate({
    caseId:'case-cooldown',operation:'SEND_OUTREACH',target:'ventas@example.test',payload,auditId:audit.auditId
  },'2026-09-30T11:00:00.000Z');
  assert.equal(result.decision,'DENY');
  assert.ok(result.reasons.includes('CONTACT_COOLDOWN'));
  raw.close();
});

test('durable commercial guard escalates proposal when current negotiation has HUMAN_GATE', async () => {
  const {raw,guard}=commercialTestDb();
  seedCommercialCase(raw,{id:'case-human'});
  raw.prepare("INSERT INTO sniper_negotiations (id,opportunity_id,state,current_offer_ars,floor_price_ars,objections_json,concessions_json,next_action,human_gate,human_gate_reasons_json,last_contact_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)")
    .run('neg-1','case-human','ACTIVE',1500000,900000,'[]','[]','SIMON_MEETING',1,'["LARGE_DEAL"]',null,'2026-09-30T12:00:00.000Z');
  const payload={subject:'Propuesta',body:'Propuesta basada en el alcance conversado.'};
  const audit=await guard.recordCommercialAudit({
    caseId:'case-human',operation:'SEND_PROPOSAL',target:'ventas@example.test',payload,
    verdict:'PASS',reason:'audited',evidenceRefs:['evidence:proposal']
  },'2026-09-30T12:01:00.000Z');
  const result=await guard.evaluate({
    caseId:'case-human',operation:'SEND_PROPOSAL',target:'ventas@example.test',payload,auditId:audit.auditId
  },'2026-09-30T12:02:00.000Z');
  assert.equal(result.decision,'HUMAN_GATE');
  assert.ok(result.reasons.includes('HUMAN_GATE_REQUIRED'));
  raw.close();
});
