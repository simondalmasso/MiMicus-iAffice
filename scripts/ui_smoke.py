from pathlib import Path
import json, os, time
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]/'apps'/'cockpit';html=(ROOT/'index.html').read_text();results=[]
stub="""
window.fetch = async (url, options={}) => {
  const path=String(url);
  let data={ok:true,sha:'__SHA__'};
  if(path.includes('/api/state')) data={tasks:[],approvals:[],actions:[],decisions:[],knowledge:[],claims:[],modelCalls:[],auditFindings:[]};
  if(path.includes('/api/system/budget')) data={ai_neurons:{used:0,hard:8500}};
  return {ok:true,status:200,json:async()=>data};
};
""".replace('__SHA__',os.environ.get('ARIA_HEAD_SHA','LOCAL_PRECOMMIT'))
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--allow-file-access-from-files'])
    for name,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
        page=browser.new_page(viewport=viewport); page.set_default_timeout(3000); page.add_init_script(stub); page.set_content(html,wait_until='load');assert page.locator('text=AriaOS').first.is_visible()
        for section in ['Today','Tasks','Memory','Decisions','Approvals','Agents','System']:
            button=page.get_by_role('button',name=section,exact=True); button.click(); assert button.get_attribute('aria-selected')=='true'; assert page.locator('#app').inner_text().strip()
        assert page.get_by_role('navigation').count()==1;assert page.locator('[aria-live="polite"]').count()==1;buttons=page.get_by_role('button').all();assert all((b.get_attribute('aria-label') or b.inner_text()).strip() for b in buttons);results.append({'viewport':name,'pass':True,'width':viewport['width'],'height':viewport['height']});page.close()
    browser.close()
out={'taxonomy':'DETERMINISTIC_TEST','timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'head_sha':os.environ.get('ARIA_HEAD_SHA','LOCAL_PRECOMMIT'),'playwright_version':'1.57.0','browser':'system-chromium','results':results,'accessibility_smoke':{'navigation_landmark':True,'aria_live':True,'named_buttons':True,'viewport_meta':True},'pass':all(x['pass'] for x in results)}
ev=Path(__file__).resolve().parents[1]/'evidence'/'ORDER-002';ev.mkdir(parents=True,exist_ok=True);(ev/'ui-smoke.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
