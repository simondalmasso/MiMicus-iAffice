import fs from 'node:fs';
import path from 'node:path';

const required={
  CLOUDFLARE_D1_DATABASE_ID:process.env.CLOUDFLARE_D1_DATABASE_ID,
  ARIA_HEAD_SHA:process.env.ARIA_HEAD_SHA
};
const missing=Object.entries(required).filter(([,v])=>!v).map(([k])=>k);
if(missing.length)throw new Error('DEPLOY_CONFIG_MISSING:'+missing.join(','));

const outDir=process.env.ARIA_DEPLOY_OUT_DIR||'.generated';
fs.mkdirSync(outDir,{recursive:true});

const templates=[
  ['wrangler.core.template.jsonc','wrangler.agent-os.jsonc'],
  ['wrangler.effects.template.jsonc','wrangler.effects.jsonc'],
  ['wrangler.models.template.jsonc','wrangler.models.jsonc']
];

for(const [input,output] of templates){
  let text=fs.readFileSync(input,'utf8')
    .replaceAll('__D1_DATABASE_ID__',required.CLOUDFLARE_D1_DATABASE_ID)
    .replaceAll('__ARIA_GIT_SHA__',required.ARIA_HEAD_SHA);
  if(/__[A-Z0-9_]+__/.test(text))throw new Error('UNRESOLVED_TEMPLATE_PLACEHOLDER:'+input);
  const target=path.join(outDir,output);
  fs.writeFileSync(target,text.endsWith('\n')?text:text+'\n');
  console.log(target);
}

console.log(JSON.stringify({
  ok:true,
  publicWorker:'agent-os',
  internalServices:['aria-effects','aria-models'],
  d1Configured:true,
  gitSha:required.ARIA_HEAD_SHA,
  outputDir:outDir
},null,2));
