from playwright.sync_api import sync_playwright
from pathlib import Path
import json,subprocess,tempfile
report=[]
with sync_playwright() as p:
 for engine,width in [(p.chromium,390),(p.firefox,1440),(p.webkit,390)]:
  print('Testing',engine.name,flush=True)
  browser=engine.launch()
  context=browser.new_context(viewport={'width':width,'height':844},accept_downloads=True,service_workers='block')
  page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://127.0.0.1:8000')
  page.keyboard.press('Tab');assert page.locator('.skip').evaluate('(e)=>e===document.activeElement')
  page.locator('#demo').click()
  with page.expect_download() as event:page.locator('.download-button').click()
  assert event.value.suggested_filename=='pocket-sample.svg'
  page.locator('#url').fill('https://www.instagram.com/reel/Chunk8-jurw/')
  page.locator('#submit').click();page.locator('#results:not([hidden])').wait_for(timeout=100000)
  with page.expect_download(timeout=30000) as event:
   page.locator('.download-button').first.click()
   print('Download clicked',engine.name,page.locator('.toast').inner_text(),flush=True)
  dl=event.value
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/dl.suggested_filename;dl.save_as(path)
   info=json.loads(subprocess.check_output(['ffprobe','-v','quiet','-print_format','json','-show_streams',str(path)]))
   valid=any(s['codec_type']=='video' for s in info['streams'])
   assert valid
  page.locator('#theme').click()
  assert page.evaluate('document.documentElement.dataset.theme')=='dark'
  page.locator('#history-open').click();page.keyboard.press('Escape');assert not page.locator('#history-dialog').is_visible()
  report.append({'engine':engine.name,'viewport':width,'sample_download':'pass','live_mp4_download':'pass','filename':dl.suggested_filename,'ffprobe_video':valid,'theme_toggle':'pass','keyboard_skip_link_and_dialog_escape':'pass','page_errors':errors})
  Path('artifacts/cross-browser.json').write_text(json.dumps(report,indent=2))
  browser.close()
Path('artifacts/cross-browser.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
