import fs from 'node:fs';
const names=['CLOUDFLARE_API_TOKEN','CLOUDFLARE_ACCOUNT_ID','CF_API_TOKEN','CF_ACCOUNT_ID'];
const present=names.filter(n=>Boolean(process.env[n]));
const core=fs.readFileSync('wrangler.core.template.jsonc','utf8'); const effects=fs.readFileSync('wrangler.effects.template.jsonc','utf8');
const forbiddenPaidModels=['@cf/zai-org/glm-5.2','@cf/moonshotai/kimi-k2.6','@cf/moonshotai/kimi-k2.7-code'];
const result={timestamp:new Date().toISOString(),credential_names_checked:names,credential_names_present:present,secret_values_printed:false,wrangler_available:Boolean(process.env.PATH?.split(':').some(p=>fs.existsSync(`${p}/wrangler`))),core_has_external_write_credentials:/GITHUB_WRITE_TOKEN|NOTION_WRITE_TOKEN|PAYMENT|STRIPE|META_ACCESS_TOKEN/.test(core),effects_has_ai_or_planner_binding:/\"ai\"|BUSINESS_WORKFLOW|COORDINATOR/.test(effects),effects_public_workers_dev:/\"workers_dev\"\s*:\s*true/.test(effects),paid_models_configured:forbiddenPaidModels.filter(m=>core.includes(m)||effects.includes(m)),deploy_authorized:present.some(n=>/TOKEN$/.test(n))&&present.some(n=>/ACCOUNT_ID$/.test(n))};
result.config_pass=!result.core_has_external_write_credentials&&!result.effects_has_ai_or_planner_binding&&!result.effects_public_workers_dev&&result.paid_models_configured.length===0;
console.log(JSON.stringify(result,null,2)); if(!result.config_pass)process.exit(41); if(!result.deploy_authorized)process.exit(42);
