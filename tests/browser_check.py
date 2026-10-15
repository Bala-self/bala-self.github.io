import json
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8000'
report={'responsive':[],'flows':[],'console_errors':[],'axe':[]}
axe=Path('node_modules/axe-core/axe.min.js').read_text()
with sync_playwright() as p:
    browser=p.chromium.launch(args=['--no-sandbox'])
    context=browser.new_context(accept_downloads=True,service_workers='block',bypass_csp=True)
    page=context.new_page()
    page.on('pageerror',lambda e:report['console_errors'].append(str(e)))
    for width in [360,390,768,1024,1440,1920]:
        page.set_viewport_size({'width':width,'height':1000})
        page.goto(BASE)
        no_overflow=page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert no_overflow, f'Horizontal overflow at {width}'
        report['responsive'].append({'width':width,'no_horizontal_scroll':no_overflow})
        if width in (390,1440):page.screenshot(path=f'artifacts/ui-{width}.png',full_page=True)
    for theme in ['light','dark']:
        page.evaluate('(theme)=>document.documentElement.dataset.theme=theme',theme)
        page.add_script_tag(content=axe)
        result=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
        report['axe'].append({'state':'idle','theme':theme,'violations':[{'id':v['id'],'impact':v['impact'],'nodes':len(v['nodes']),'summary':[n['failureSummary'] for n in v['nodes']]} for v in result['violations']]})
    page.goto(BASE)
    page.locator('#url').fill('https://evil.org/p/ABCDEF/')
    page.locator('#submit').click();assert page.locator('#input-error').is_visible()
    report['flows'].append('Invalid input rejected inline')
    page.locator('#clear').click();assert page.locator('#url').input_value()==''
    page.locator('#demo').click();assert page.locator('.demo-notice').is_visible()
    with page.expect_download() as event:page.locator('.download-button').click()
    dl=event.value;assert dl.suggested_filename=='pocket-sample.svg'
    report['flows'].append('Explicit sample renders and downloads SVG')
    page.add_script_tag(content=axe)
    result=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
    report['axe'].append({'state':'sample success','violations':[{'id':v['id'],'nodes':len(v['nodes'])} for v in result['violations']]})
    page.locator('#history-open').click();assert page.locator('#history-dialog').is_visible()
    page.locator('#remember').check();page.keyboard.press('Escape');assert not page.locator('#history-dialog').is_visible()
    report['flows'].append('History opt-in and Escape dialog dismissal')
    page.locator('footer a[href="/privacy"]').click();assert page.locator('h1').inner_text()=='Privacy policy'
    assert page.locator('.policy-content').is_visible()
    page.goto(BASE)
    report['flows'].append('Server-rendered privacy policy navigates accessibly')
    # Fixture tests verify frontend error/success behavior independently of upstream availability.
    def limited(route):route.fulfill(status=429,content_type='application/json',body=json.dumps({'error':'rate_limited','message':'Please wait.','retry_after':2}))
    page.route('**/api/resolve',limited)
    page.locator('#url').fill('https://www.instagram.com/p/ABCDEF/')
    page.locator('#submit').click();page.locator('.error-card').wait_for()
    assert page.locator('.error-card button').is_disabled()
    page.locator('.error-card button').wait_for(state='visible')
    page.wait_for_function('!document.querySelector(".error-card button").disabled')
    report['flows'].append('429 countdown enables retry')
    page.unroute('**/api/resolve',limited)
    page.set_viewport_size({'width':390,'height':844})
    page.locator('#url').fill('https://www.instagram.com/p/BQ0eAlwhDrw/')
    page.locator('#submit').click();page.locator('#results:not([hidden])').wait_for(timeout=100000)
    assert page.locator('.media-item').count()>=1
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    report['flows'].append('Live public post resolved and carousel cards rendered on mobile width')
    page.screenshot(path='artifacts/live-success-mobile.png',full_page=True)
    # Verify safe text rendering of a malicious-looking caption via a fixture.
    def xss(route):route.fulfill(status=200,content_type='application/json',body=json.dumps({'type':'image','caption':'<script>window.injected=true</script>','author':'<img onerror=alert(1)>','items':[{'id':'0','quality':'Original','ext':'svg','url':'/sample.svg','preview_url':'/sample.svg'}]}))
    page.route('**/api/resolve',xss);page.locator('#submit').click();page.locator('.result-caption').wait_for()
    assert '<script>' in page.locator('.result-caption').inner_text() and not page.evaluate('!!window.injected')
    report['flows'].append('Caption/author HTML rendered as text, not executed')
    browser.close()
Path('artifacts/browser-results.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
