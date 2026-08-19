import fs from 'node:fs';
import { AriaOrchestrator } from '../dist/packages/core/src/orchestrator.js';
import { InMemoryStateStore } from '../dist/packages/memory/src/store.js';
import { referenceEvents } from '../dist/packages/fixtures/src/reference.js';
import { LocalEffectGateway } from '../dist/packages/effects/src/local.js';
const out=await new AriaOrchestrator(new InMemoryStateStore(), undefined, 'local-reference-signing-key', ()=>new Date('2026-08-19T15:00:00.000Z')).runReferenceE2E(await referenceEvents(), new LocalEffectGateway());
const evidence={taxonomy:'DETERMINISTIC_TEST',timestamp:new Date().toISOString(),head_sha:process.env.ARIA_HEAD_SHA||'LOCAL_PRECOMMIT',steps:out.steps,pre_restart_hash:out.preRestartHash,post_restart_hash:out.postRestartHash,ledger_verified:out.ledgerVerified,tamper_detected:out.tamperDetected,model_calls:out.modelCalls,estimated_neurons:out.totalNeurons,total_incremental_cost_usd:out.costUsd,hot_lead_id:out.hotLeadId,stale_lead_id:out.staleLeadId,approval_id:out.approvalId,outbound_id:out.outboundId};
fs.mkdirSync('evidence/ORDER-002',{recursive:true});fs.writeFileSync('evidence/ORDER-002/reference-e2e.json',JSON.stringify(evidence,null,2)+'\n');console.log(JSON.stringify(evidence,null,2));
