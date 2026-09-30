import fs from 'node:fs';

const deployTokenNames=['CLOUDFLARE_API_TOKEN','CF_API_TOKEN'];
const accountNames=['CLOUDFLARE_ACCOUNT_ID','CF_ACCOUNT_ID'];
const providerNames=['GROQ_API_KEY','MISTRAL_API_KEY','GEMINI_API_KEY','ZENMUX_API_KEY'];

const tokenPresent=deployTokenNames.filter(n=>Boolean(process.env[n]));
const accountPresent=accountNames.filter(n=>Boolean(process.env[n]));
const providerPresent=providerNames.filter(n=>Boolean(process.env[n]));

const core=fs.readFileSync('wrangler.core.template.jsonc','utf8');
const effects=fs.readFileSync('wrangler.effects.template.jsonc','utf8');
const models=fs.readFileSync('wrangler.models.template.jsonc','utf8');
const paidModels=['@cf/zai-org/glm-5.2','@cf/moonshotai/kimi-k2.6','@cf/moonshotai/kimi-k2.7-code'];

const result={
  timestamp:new Date().toISOString(),
  secret_values_printed:false,
  deployment:{
    token_names_present:tokenPresent,
    account_names_present:accountPresent,
    authorized:tokenPresent.length>0&&accountPresent.length>0
  },
  optional_external_model_credentials_present:providerPresent,
  config:{
    public_worker_agent_os:core.includes('"name": "agent-os"'),
    cockpit_assets:core.includes('"directory": "./apps/cockpit"'),
    core_has_model_credentials:providerNames.some(n=>core.includes(n)),
    core_has_ai_binding:/\"ai\"/.test(core),
    effects_has_model_credentials:providerNames.some(n=>effects.includes(n)),
    effects_has_ai_or_planner:/\"ai\"|BUSINESS_WORKFLOW|COORDINATOR|COMPUTE_GOVERNOR/.test(effects),
    models_has_business_write_authority:/EFFECTS|GITHUB_WRITE_TOKEN|NOTION_WRITE_TOKEN|STRIPE|META_ACCESS_TOKEN/.test(models),
    models_public_workers_dev:/\"workers_dev\"\s*:\s*true/.test(models),
    effects_public_workers_dev:/\"workers_dev\"\s*:\s*true/.test(effects),
    paid_models_configured:paidModels.filter(m=>core.includes(m)||models.includes(m))
  }
};
result.config_pass=
  result.config.public_worker_agent_os&&
  result.config.cockpit_assets&&
  !result.config.core_has_model_credentials&&
  !result.config.core_has_ai_binding&&
  !result.config.effects_has_model_credentials&&
  !result.config.effects_has_ai_or_planner&&
  !result.config.models_has_business_write_authority&&
  !result.config.models_public_workers_dev&&
  !result.config.effects_public_workers_dev&&
  result.config.paid_models_configured.length===0;

console.log(JSON.stringify(result,null,2));
if(!result.config_pass)process.exit(41);
if(!result.deployment.authorized)process.exit(42);
