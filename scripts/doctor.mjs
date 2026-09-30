import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { execFileSync } from 'node:child_process';

const checks=[];
const check=(name,fn)=>{try{checks.push({name,pass:true,detail:String(fn()??'PASS')})}catch(e){checks.push({name,pass:false,detail:e instanceof Error?e.message:String(e)})}};

check('node>=22',()=>{
  const major=Number(process.versions.node.split('.')[0]);
  if(major<22)throw new Error(process.versions.node);
  return process.versions.node;
});

check('locked-install',()=>{
  if(!fs.existsSync('package-lock.json'))throw new Error('package-lock.json missing');
  return 'package-lock.json';
});

check('all-migrations-empty-db',()=>{
  const db=new DatabaseSync(':memory:');
  const migrationFiles=fs.readdirSync('migrations').filter(x=>/^\d{4}_.+\.sql$/.test(x)).sort();
  if(migrationFiles.length<12)throw new Error('expected >=12 migrations; found '+migrationFiles.length);
  for(const file of migrationFiles)db.exec(fs.readFileSync(path.join('migrations',file),'utf8'));
  const rows=db.prepare("select name from sqlite_master where type='table'").all();
  const names=new Set(rows.map(r=>r.name));
  const required=[
    'compute_providers',
    'sniper_opportunities',
    'sniper_memory_episodes',
    'sniper_global_decisions',
    'sniper_telemetry_spans',
    'sniper_skill_registry',
    'sniper_discovery_jobs',
    'sniper_demo_jobs',
    'sniper_executor_registry',
    'sniper_contact_controls',
    'sniper_commercial_effects'
  ];
  for(const table of required)if(!names.has(table))throw new Error('missing '+table);
  db.close();
  return 'migrations='+migrationFiles.length+';tables='+rows.length;
});

check('strict-typecheck',()=>execFileSync('tsc',['-p','tsconfig.json','--noEmit'],{stdio:'pipe'}).toString()||'PASS');


check('oracle-executor-python',()=>{
  return execFileSync('python3',['-m','py_compile','apps/oracle-executor/iaffice_executor.py'],{stdio:'pipe'}).toString()||'PASS';
});

check('oracle-executor-selftest',()=>{
  return execFileSync('python3',['scripts/oracle_executor_selftest.py'],{stdio:'pipe'}).toString().trim()||'PASS';
});

check('oracle-executor-security-guard',()=>{
  const py=fs.readFileSync('apps/oracle-executor/iaffice_executor.py','utf8');
  const unit=fs.readFileSync('apps/oracle-executor/iaffice-executor.service','utf8');
  for(const forbidden of ['shell=True','os.system(','/bin/sh','ARBITRARY_SHELL']){
    if(py.includes(forbidden))throw new Error('forbidden executor primitive: '+forbidden);
  }
  for(const required of ['IAFFICE_EXECUTOR_SIGNING_KEY','DISCOVERY_EXECUTOR_ADAPTER_NOT_ENABLED','actualCostUsd','executor://']){
    if(!py.includes(required))throw new Error('missing executor guard: '+required);
  }
  for(const hardening of ['NoNewPrivileges=true','ProtectSystem=strict','CapabilityBoundingSet=']){
    if(!unit.includes(hardening))throw new Error('missing systemd hardening: '+hardening);
  }
  return 'typed jobs+hmac+no arbitrary shell+systemd hardening';
});

check('cockpit-integrity',()=>{
  const h=fs.readFileSync('apps/cockpit/index.html','utf8');
  const required=['Revenue','Global Core','Operations','Discovery','Demos','Cases','Live','Decisions','Learning','Telemetry','Skills','Squad','Approvals','Compute','System'];
  for(const section of required)if(!h.includes("'"+section+"'"))throw new Error('missing cockpit section '+section);
  if((h.match(/<script>/g)||[]).length!==1)throw new Error('script open count');
  if((h.match(/<\/script>/g)||[]).length!==1)throw new Error('script close count');
  if((h.match(/<\/html>/g)||[]).length!==1)throw new Error('html close count');
  const close=h.lastIndexOf('</html>');
  if(h.slice(close+7).trim())throw new Error('content after html close');
  if(h.includes('</html>+Number('))throw new Error('known cockpit corruption marker');
  return required.length+' sections;structure=clean';
});

check('public-worker-target',()=>{
  const core=fs.readFileSync('wrangler.core.template.jsonc','utf8');
  if(!core.includes('"name": "agent-os"'))throw new Error('agent-os worker name missing');
  if(!core.includes('"directory": "./apps/cockpit"'))throw new Error('cockpit assets missing');
  return 'agent-os + cockpit assets';
});

check('three-worker-boundary',()=>{
  const core=fs.readFileSync('wrangler.core.template.jsonc','utf8');
  const models=fs.readFileSync('wrangler.models.template.jsonc','utf8');
  const effects=fs.readFileSync('wrangler.effects.template.jsonc','utf8');
  if(!core.includes('MODELS')||!core.includes('EFFECTS')||/\"ai\"/.test(core))throw new Error('core binding topology');
  if(!/\"ai\"/.test(models)||/EFFECTS/.test(models))throw new Error('model topology');
  if(/\"ai\"/.test(effects))throw new Error('effects model binding');
  if(!effects.includes('"workers_dev": false')||!models.includes('"workers_dev": false'))throw new Error('internal workers must not expose workers.dev');
  return 'agent-os→aria-models/aria-effects private domains';
});

check('cron-count-unchanged',()=>{
  const c=(fs.readFileSync('wrangler.core.template.jsonc','utf8').match(/\*\/15|0 14|0 6|0 10/g)||[]).length;
  if(c!==4)throw new Error('crons='+c);
  return c;
});

check('zero-cost-ci-guard',()=>{
  const y=fs.readFileSync('.github/workflows/verify.yml','utf8');
  if(!y.includes('workflow_dispatch')||!y.includes('[self-hosted, linux, oracle-free, iaffice]'))throw new Error('CI Oracle-only cost/host guard');
  return 'workflow_dispatch+oracle-free-linux-iaffice';
});

check('commercial-double-gate',()=>{
  const core=fs.readFileSync('apps/worker/src/index.ts','utf8');
  const effects=fs.readFileSync('apps/effects-worker/src/index.ts','utf8');
  const guard=fs.readFileSync('packages/sniper/src/commercialGuard.ts','utf8');
  const policy=fs.readFileSync('packages/sniper/src/commercialPolicy.ts','utf8');
  for(const required of ['CommercialGuard','/api/sniper/commercial/action','CASE_EXTERNAL_ACTION_REQUIRES_COMMERCIAL_GATE']){
    if(!core.includes(required))throw new Error('core commercial gate missing: '+required);
  }
  for(const required of ['CommercialGuard','COMMERCIAL_POLICY_REVALIDATION_DENIED','COMMERCIAL_PAYLOAD_DIGEST_MISMATCH','recordExecuted']){
    if(!effects.includes(required))throw new Error('effects commercial revalidation missing: '+required);
  }
  for(const required of ['COMMERCIAL_COPY_GUARD','sniper_commercial_effects','sniper_contact_controls']){
    if(!guard.includes(required))throw new Error('durable commercial guard missing: '+required);
  }
  for(const required of ['DO_NOT_CONTACT','BULK_BLAST_DENIED','HUMAN_IMPERSONATION_DENIED','CONTACT_COOLDOWN']){
    if(!policy.includes(required))throw new Error('commercial policy rule missing: '+required);
  }
  return 'core+effects+D1+AUD commercial guard';
});

check('zero-spend-source-guards',()=>{
  const telemetry=fs.readFileSync('packages/sniper/src/telemetry.ts','utf8');
  const executor=fs.readFileSync('packages/sniper/src/executorRegistry.ts','utf8');
  const discovery=fs.readFileSync('packages/sniper/src/discoverySources.ts','utf8');
  if(!telemetry.includes('TELEMETRY_PAID_EXECUTION_FORBIDDEN'))throw new Error('telemetry spend guard missing');
  if(!executor.includes('PAID_RUNTIME_FORBIDDEN'))throw new Error('executor spend guard missing');
  if(!discovery.includes('PAID_RUNTIME_FORBIDDEN'))throw new Error('discovery spend guard missing');
  return 'telemetry+executor+discovery';
});

const result={
  taxonomy:'DETERMINISTIC_TEST',
  order:'ORDER-004',
  timestamp:new Date().toISOString(),
  head_sha:process.env.ARIA_HEAD_SHA||'LOCAL_PRECOMMIT',
  checks,
  pass:checks.every(x=>x.pass)
};
fs.mkdirSync('evidence/ORDER-004',{recursive:true});
fs.writeFileSync('evidence/ORDER-004/doctor.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
if(!result.pass)process.exit(2);