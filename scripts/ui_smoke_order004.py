from pathlib import Path
import json, os, time
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'apps'/'cockpit'/'index.html').read_text()
sha=os.environ.get('ARIA_HEAD_SHA','LOCAL_PRECOMMIT')

stub=r"""
window.fetch=async(url,opts={})=>{
 const p=String(url);let data={};
 if(p.includes('/api/health'))data={ok:true,service:'iAffice',worker:'agent-os',sha:'__SHA__'};
 else if(p.includes('/api/state'))data={approvals:[]};
 else if(p.includes('/api/sniper/dashboard'))data={pipeline:{total:2,qualified:1,negotiating:1,won:0,lost:0},money:{pendingArs:120000,collectedArs:0},topOpportunities:[],activity:[],memory:{episodes:[],patterns:[],tactics:[],decisions:[]}};
 else if(p.includes('/api/sniper/global'))data={portfolio:{total:2,signals:[]},latest:null,architecture:{system1:'typed calibrated decision service',system2:'aria-models reasoning',authority:'policy + audited memory + human gate'}};
 else if(p.includes('/api/sniper/operations'))data={totalCases:2,stages:[{id:'ANALYZE',label:'Analizan',purpose:'Evidence',externalEffectBoundary:[]},{id:'PROSPECT',label:'Prospectan',purpose:'Commercial',externalEffectBoundary:['SEND_OUTREACH']},{id:'EXECUTE',label:'Ejecutan',purpose:'Build',externalEffectBoundary:[]},{id:'DELIVER',label:'Entregan',purpose:'QA',externalEffectBoundary:['DEPLOY_CUSTOMER_WORK']},{id:'COLLECT',label:'Cobran',purpose:'Payment',externalEffectBoundary:['CREATE_PAYMENT_REQUEST']}],workstreams:{ANALYZE:[],PROSPECT:[],EXECUTE:[],DELIVER:[],COLLECT:[]}};
 else if(p.includes('/api/sniper/discovery/sources'))data={totals:{enabled:0,quarantined:4,rejected:1},sources:[]};
 else if(p.includes('/api/sniper/discovery/jobs'))data=[];
 else if(p.includes('/api/sniper/demos'))data=[];
 else if(p.includes('/api/sniper/executors'))data={totals:{enabled:0,quarantined:1,rejected:0},executors:[{label:'Oracle Free Tier job executor',role:'JOB_EXECUTOR',admission:{state:'QUARANTINED'},capabilities:['WEB_BUILD','BROWSER_3D','HEAVY_3D'],endpoint:null,costClass:'FREE_USER_CONFIRMED',zeroCostVerified:false,health:'UNKNOWN'}]};
 else if(p.includes('/api/sniper/telemetry'))data={authority:'ARIA_TELEMETRY_FABRIC',summary:{traces:0,spans:0,errors:0,denied:0,abstained:0,p95LatencyMs:0,actualCostUsd:0,inputTokens:0,outputTokens:0,byAgent:{}},recentSpans:[],recentTraceIds:[],adapters:[]};
 else if(p.includes('/api/sniper/skills'))data={totals:{sources:6,enabled:0,quarantined:6,rejected:0},policy:{revisionPinRequired:true},sources:[]};
 else if(p.includes('/api/sniper/opportunities'))data=[];
 else if(p.includes('/api/sniper/squad'))data=[];
 else if(p.includes('/api/compute/providers'))data=[{providerName:'Cloudflare Workers AI',freeType:'RECURRING_FREE',billingSafety:'FREE_TIER_FAILS_CLOSED',privacyClass:'CONFIDENTIAL_ALLOWED',routeState:'ACTIVE'}];
 else if(p.includes('/api/compute/budget'))data={currentReserved:0,billableExecutionAttempts:0};
 return {ok:true,status:200,json:async()=>data};
};
""".replace('__SHA__',sha)

sections=['Revenue','Global Core','Operations','Discovery','Demos','Cases','Live','Decisions','Learning','Telemetry','Skills','Squad','Approvals','Compute','System']
results=[]

with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox','--allow-file-access-from-files'])
 for name,vp in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
  page=browser.new_page(viewport=vp)
  page.set_default_timeout(4000)
  page.add_init_script(stub)
  page.set_content(html,wait_until='load')
  assert page.get_by_text('iAffice',exact=True).first.is_visible()
  for section in sections:
   button=page.get_by_role('button',name=section,exact=True)
   button.click()
   assert button.get_attribute('aria-selected')=='true'
   assert page.locator('#app').inner_text().strip()
  page.get_by_role('button',name='Demos',exact=True).click()
  assert page.get_by_text('Private proof factory',exact=True).is_visible()
  assert page.get_by_text('Oracle Free Tier job executor',exact=True).is_visible()
  page.get_by_role('button',name='Telemetry',exact=True).click()
  assert page.get_by_text('Agent observability fabric',exact=True).is_visible()
  page.get_by_role('button',name='Compute',exact=True).click()
  assert page.get_by_text('$0',exact=True).count()>=1
  assert page.get_by_role('navigation').count()==1
  assert page.locator('[aria-live="polite"]').count()==1
  results.append({'viewport':name,'pass':True,'sections':len(sections)})
  page.close()
 browser.close()

out={
 'taxonomy':'DETERMINISTIC_TEST',
 'order':'ORDER-004',
 'timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
 'head_sha':sha,
 'results':results,
 'checks':{
   'brand':'iAffice',
   'public_worker':'agent-os',
   'sections':sections,
   'demos_executor_visibility':True,
   'telemetry':True,
   'zero_spend_surface':True
 },
 'pass':all(x['pass'] for x in results)
}
ev=ROOT/'evidence'/'ORDER-004'
ev.mkdir(parents=True,exist_ok=True)
(ev/'ui-smoke.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))