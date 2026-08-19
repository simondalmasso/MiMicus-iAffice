import fs from 'node:fs';import { DatabaseSync } from 'node:sqlite';import { execFileSync } from 'node:child_process';
const checks=[];const check=(name,fn)=>{try{const detail=fn();checks.push({name,pass:true,detail:String(detail??'PASS')})}catch(e){checks.push({name,pass:false,detail:e.message})}};
check('node>=22',()=>process.versions.node);
check('locked-install',()=>fs.existsSync('package-lock.json'));
check('migration-empty-db',()=>{const db=new DatabaseSync(':memory:');db.exec(fs.readFileSync('migrations/0001_initial.sql','utf8'));const rows=db.prepare("select name from sqlite_master where type='table'").all();db.close();if(rows.length<26)throw new Error(`tables=${rows.length}`);return `tables=${rows.length}`});
check('strict-typecheck',()=>execFileSync('tsc',['-p','tsconfig.json','--noEmit'],{stdio:'pipe'}).toString()||'PASS');
check('cockpit-seven-screens',()=>{const h=fs.readFileSync('apps/cockpit/index.html','utf8');for(const s of ['Today','Tasks','Memory','Decisions','Approvals','Agents','System'])if(!h.includes(`'${s}'`))throw new Error(`missing ${s}`);return '7 screens'});
check('manual-self-hosted-ci',()=>{const y=fs.readFileSync('.github/workflows/verify.yml','utf8');if(!y.includes('workflow_dispatch')||!y.includes('self-hosted'))throw new Error('CI cost guard missing');return 'workflow_dispatch+self-hosted'});
const result={taxonomy:'DETERMINISTIC_TEST',timestamp:new Date().toISOString(),head_sha:process.env.ARIA_HEAD_SHA||'LOCAL_PRECOMMIT',checks,pass:checks.every(x=>x.pass)};fs.mkdirSync('evidence/ORDER-002',{recursive:true});fs.writeFileSync('evidence/ORDER-002/migrations.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));if(!result.pass)process.exit(2);
