from pathlib import Path
import json, os, time
from playwright.sync_api import sync_playwright
html=(Path(__file__).resolve().parents[1]/'apps'/'cockpit'/'index.html').read_text()
stub="""window.fetch=async(url,opts={})=>{const p=String(url);let data={ok:true,sha:'__SHA__'};if(p.includes('/api/state'))data={tasks:[],approvals:[],decisions:[],knowledge:[],modelCalls:[]};if(p.includes('/api/compute/providers'))data=[{providerName:'Cloudflare Workers AI',freeType:'RECURRING_FREE',billingSafety:'FREE_TIER_FAILS_CLOSED',privacyClass:'CONFIDENTIAL_ALLOWED',routeState:'ACTIVE',productionEligible:true,lastVerifiedAt:'2026-08-19'}];if(p.includes('/api/compute/models'))data=[{modelId:'m'}];if(p.includes('/api/compute/routes'))data=[{task_id:'t',selected_provider_id:'cloudflare-workers-ai',selected_model_id:'m',selected_score:9000,reason:'DETERMINISTIC'}];if(p.includes('/api/compute/incidents'))data=[];if(p.includes('/api/compute/budget'))data={cumulativeMonetarySpendUsd:0,currentReserved:12};return {ok:true,status:200,json:async()=>data}};""".replace('__SHA__',os.environ.get('ARIA_HEAD_SHA','LOCAL_PRECOMMIT'))
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--allow-file-access-from-files'])
 for name,vp in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
  page=browser.new_page(viewport=vp);page.add_init_script(stub);page.set_content(html,wait_until='load');page.get_by_role('button',name='Compute',exact=True).click();assert page.get_by_text('Compute Market',exact=True).is_visible();assert page.get_by_text('Cloudflare Workers AI',exact=True).is_visible();assert page.get_by_text('$0',exact=True).count()>=1
  for section in ['Today','Tasks','Memory','Decisions','Approvals','Agents','Compute','System']: page.get_by_role('button',name=section,exact=True).click();assert page.locator('#app').inner_text().strip()
  assert page.get_by_role('navigation').count()==1;results.append({'viewport':name,'pass':True});page.close()
 browser.close()
out={'taxonomy':'DETERMINISTIC_TEST','timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'head_sha':os.environ.get('ARIA_HEAD_SHA','LOCAL_PRECOMMIT'),'results':results,'compute_tab':True,'eight_sections_parent_seven_preserved':True,'pass':all(x['pass'] for x in results)};ev=Path(__file__).resolve().parents[1]/'evidence'/'ORDER-003';ev.mkdir(parents=True,exist_ok=True);(ev/'cockpit-smoke.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
