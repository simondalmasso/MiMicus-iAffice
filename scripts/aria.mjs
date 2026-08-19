#!/usr/bin/env node
import fs from 'node:fs';
import { spawnSync } from 'node:child_process';
import { emptyState } from '../dist/packages/memory/src/store.js';
import { EventMemory, Ledger, rebuildProjection, stateHash } from '../dist/packages/memory/src/ledger.js';
import { referenceEvents } from '../dist/packages/fixtures/src/reference.js';
import { LocalEffectGateway } from '../dist/packages/effects/src/local.js';
import { AriaOrchestrator } from '../dist/packages/core/src/orchestrator.js';
import { Scheduler } from '../dist/packages/core/src/scheduler.js';
const dir='.aria'; const file=`${dir}/local-state.json`; const ledgerFile=`${dir}/local-ledger.json`;
class FileStore {
  async load(){return fs.existsSync(file)?JSON.parse(fs.readFileSync(file,'utf8')):emptyState();}
  async save(state){fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(file,JSON.stringify(state,null,2)+'\n');}
  async reset(){fs.rmSync(dir,{recursive:true,force:true});}
  async loadLedger(){return fs.existsSync(ledgerFile)?JSON.parse(fs.readFileSync(ledgerFile,'utf8')):[];}
  async saveLedger(records){fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(ledgerFile,JSON.stringify(records,null,2)+'\n');}
}
const command=process.argv[2]??'help'; const store=new FileStore();
const run=(args)=>{const r=spawnSync('npm',args,{stdio:'inherit'});process.exitCode=r.status??1;};
if(command==='doctor') run(['run','doctor']);
else if(command==='benchmark') run(['run','benchmark']);
else if(command==='export-evidence') run(['run','evidence']);
else if(command==='ingest'){
  if((process.argv[3]??'reference')!=='reference') throw new Error('ONLY_REFERENCE_FIXTURE_SUPPORTED_LOCALLY');
  const state=await store.load(); const ledger=new Ledger(); ledger.replaceForTest(await store.loadLedger()); const memory=new EventMemory(state,ledger); let duplicates=0;
  for(const event of await referenceEvents()){const r=await memory.ingest(event);if(r.duplicate)duplicates++;}
  const projection=await rebuildProjection(state.events);state.leads=projection.leads;state.metrics=projection.metrics;await store.save(state);await store.saveLedger(ledger.list());console.log(JSON.stringify({events:state.events.length,duplicates,fixture:'REFERENCE_BUSINESS_FIXTURE'}));
}else if(command==='run'){
  const task=process.argv[3]??'reference-e2e'; if(task!=='reference-e2e') throw new Error('UNKNOWN_RUN_TASK');
  const o=new AriaOrchestrator(store,undefined,'local-reference-signing-key',()=>new Date('2026-08-19T15:00:00.000Z'));await o.load();const result=await o.runReferenceE2E(await referenceEvents(), new LocalEffectGateway());console.log(JSON.stringify({pass:result.steps.every(s=>s.pass),steps:result.steps.length,modelCalls:result.modelCalls,costUsd:result.costUsd},null,2));
}else if(command==='tick'){
  const state=await store.load();const scheduler=new Scheduler(state);const slot=new Date().toISOString();const result=await scheduler.enqueue('business_tick',slot.slice(0,16)+':00.000Z');await store.save(state);console.log(JSON.stringify({taskId:result.task.id,duplicate:result.duplicate,status:result.task.status}));
}else if(command==='verify-ledger'){
  const ledger=new Ledger();ledger.replaceForTest(await store.loadLedger());console.log(JSON.stringify(await ledger.verify(),null,2));
}else if(command==='replay'){
  const state=await store.load();const before=await stateHash(state);const rebuilt=await rebuildProjection(state.events);state.leads=rebuilt.leads;state.metrics=rebuilt.metrics;const after=await stateHash(state);console.log(JSON.stringify({scope:process.argv[3]??'all',before,after,projectionEvents:state.events.length,deterministic:before===after},null,2));
}else if(command==='compact-memory'){
  const state=await store.load();const ledger=new Ledger();ledger.replaceForTest(await store.loadLedger());const memory=new EventMemory(state,ledger);const expired=memory.expire(new Date().toISOString());await store.save(state);console.log(JSON.stringify({expired,remaining:state.knowledge.filter(k=>k.status==='VERIFIED_KNOWLEDGE').length}));
}else{console.log('aria doctor | ingest reference | run reference-e2e | tick | replay [id] | verify-ledger | compact-memory | benchmark | export-evidence');}
