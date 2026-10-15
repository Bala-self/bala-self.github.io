"""Whole-public-site UX/SEO regression; no upstream Instagram dependency."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8000'
OUT=Path('artifacts/seo')
OUT.mkdir(parents=True,exist_ok=True)
report={'responsive':[],'axe':[],'no_javascript':[],'console_errors':[],'pwa':{}}
axe=Path('node_modules/axe-core/axe.min.js').read_text()
with sync_playwright() as p:
    browser=p.chromium.launch()
    context=browser.new_context(bypass_csp=True,service_workers='block')
    page=context.new_page();page.on('pageerror',lambda e:report['console_errors'].append(str(e)))
    for path in ['/','/privacy','/terms']:
        for width in [360,390,768,1024,1440,1920]:
            page.set_viewport_size({'width':width,'height':900});page.goto(BASE+path)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('h1').count()==1
            report['responsive'].append({'path':path,'width':width,'horizontal_overflow':False})
        for theme in ['light','dark']:
            page.evaluate('(v)=>document.documentElement.dataset.theme=v',theme)
            page.add_script_tag(content=axe)
            r=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
            violations=[{'id':v['id'],'impact':v['impact'],'nodes':len(v['nodes'])} for v in r['violations']]
            report['axe'].append({'path':path,'theme':theme,'violations':violations});assert not violations
        page.set_viewport_size({'width':390,'height':844});page.evaluate("document.documentElement.dataset.theme='light'")
        page.screenshot(path=str(OUT/('home-mobile.png' if path=='/' else path[1:]+'-mobile.png')),full_page=True)
    # Real no-JS reads: policy text isn't hidden behind a dialog or client-side routing.
    nojs=browser.new_context(java_script_enabled=False)
    for path in ['/','/privacy','/terms']:
        tab=nojs.new_page();tab.goto(BASE+path)
        assert tab.locator('h1').is_visible()
        if path=='/':assert tab.locator('noscript').is_visible()
        else:assert tab.locator('.policy-content h2').first.is_visible() and not tab.locator('dialog').count()
        report['no_javascript'].append({'path':path,'visible_content':True})
    # Strict CSP context: inline theme hash must work without permitting arbitrary inline scripts.
    strict=browser.new_context(service_workers='block')
    tab=strict.new_page();strict_errors=[]
    tab.on('console',lambda m:strict_errors.append(m.text) if m.type=='error' else None)
    tab.goto(BASE);tab.locator('#theme').click();assert tab.evaluate('document.documentElement.dataset.theme')=='dark'
    tab.locator('footer a[href="/privacy"]').click();assert tab.evaluate('document.documentElement.dataset.theme')=='dark'
    tab.locator('#theme').click();assert tab.evaluate('document.documentElement.dataset.theme')=='light'
    assert not strict_errors;report['strict_csp_theme_errors']=strict_errors
    # Check the installed worker caches the shell/policies, but not tokenized media or API responses.
    swcontext=browser.new_context();tab=swcontext.new_page();tab.goto(BASE)
    tab.evaluate('async()=>await navigator.serviceWorker.ready')
    tab.wait_for_function('!!navigator.serviceWorker.controller')
    keys=tab.evaluate('async()=>{let keys=[];for(const name of await caches.keys()){for(const req of await (await caches.open(name)).keys())keys.push(new URL(req.url).pathname);}return keys;}')
    assert '/privacy' in keys and '/terms' in keys and not any(k.startswith('/api/') for k in keys)
    swcontext.set_offline(True);tab.goto(BASE+'/privacy');assert tab.locator('h1').inner_text()=='Privacy policy'
    report['pwa']={'offline_privacy_page':'pass','cached_paths':keys,'no_api_or_media_cache':True}
    swcontext.set_offline(False)
    browser.close()
(OUT/'whole-site-browser.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
