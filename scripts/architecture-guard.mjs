import fs from 'node:fs';
import path from 'node:path';

const roots=['packages','apps']; const files=[];
function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isDirectory())walk(p);else if(/\.(ts|js|html)$/.test(e.name))files.push(p)}}
for(const root of roots)walk(root);
const violations=[];
const gatewayPrefixes=['packages/effects/','apps/effects-worker/'];
for(const file of files){const text=fs.readFileSync(file,'utf8'); const gateway=gatewayPrefixes.some((p)=>file.replaceAll('\\','/').startsWith(p));
 if(!gateway){
   if(/GITHUB_WRITE_TOKEN|NOTION_WRITE_TOKEN|STRIPE_SECRET|META_ACCESS_TOKEN/.test(text)) violations.push(`${file}:write-credential-name-outside-gateway`);
   const hasExternalHost=/https:\/\/(?!aria-effects\.internal|coordinator\.internal)[A-Za-z0-9.-]+/.test(text); const hasWriteFetch=/(?<![.A-Za-z0-9_])fetch\s*\([^)]{0,500}[`'"]https:\/\/(?!aria-effects\.internal)[\s\S]{0,500}?method\s*:\s*[`'"](?:POST|PUT|PATCH|DELETE)/.test(text); if(hasExternalHost&&hasWriteFetch) violations.push(`${file}:external-write-fetch-outside-gateway`);
   if(/SafeOutboundEffectAdapter|GitHubIssueCommentEffectAdapter|NotionEffectAdapter/.test(text)) violations.push(`${file}:effect-adapter-import-outside-gateway`);
 }
 if(file.startsWith('apps/effects-worker/')&&/(WorkersAiProvider|ModelRouter|AriaOrchestrator|CEO|RESEARCH|CMO|SALES|DATA|DEV|AUD)/.test(text)) violations.push(`${file}:planner-or-model-in-effects-worker`);
}
const coreConfig=fs.readFileSync('wrangler.core.template.jsonc','utf8'); if(/GITHUB_WRITE_TOKEN|NOTION_WRITE_TOKEN|STRIPE_SECRET|META_ACCESS_TOKEN/.test(coreConfig))violations.push('wrangler.core.template.jsonc:write-credential-binding');
const effectsConfig=fs.readFileSync('wrangler.effects.template.jsonc','utf8'); if(/\"ai\"|BUSINESS_WORKFLOW|COORDINATOR/.test(effectsConfig))violations.push('wrangler.effects.template.jsonc:model-or-planner-binding');
const result={pass:violations.length===0,filesScanned:files.length,violations,invariants:{AGENT_DIRECT_EXTERNAL_WRITE:0,AGENT_WRITE_CREDENTIALS:0,EXTERNAL_EFFECT_PATHS_OUTSIDE_GATEWAY:0}};
console.log(JSON.stringify(result,null,2)); if(!result.pass)process.exit(1);
