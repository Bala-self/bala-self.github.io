"""Run weekly with TEST_URLS, BASE_URL and optional ALERT_WEBHOOK. No URLs in alerts."""
import json,os,sys,urllib.request,urllib.error
base=os.getenv('BASE_URL','http://127.0.0.1:8000').rstrip('/')
urls=[u.strip() for u in os.getenv('TEST_URLS','').split(',') if u.strip()]
if not urls:sys.exit('Set TEST_URLS to a comma-separated list of public content you own or may test.')
success=0
for url in urls:
    try:
        req=urllib.request.Request(base+'/api/resolve',data=json.dumps({'url':url}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=100) as r: success+=bool(json.load(r).get('items'))
    except Exception:pass
rate=success/len(urls)
summary={'message':'Pocket weekly public resolver check','success':success,'total':len(urls),'success_rate':rate}
print(json.dumps(summary))
if rate<float(os.getenv('SUCCESS_THRESHOLD','0.8')):
    webhook=os.getenv('ALERT_WEBHOOK')
    if webhook:
        try:
            req=urllib.request.Request(webhook,data=json.dumps(summary).encode(),headers={'Content-Type':'application/json'})
            urllib.request.urlopen(req,timeout=15).close()
        except Exception:print('Webhook delivery failed.',file=sys.stderr)
    sys.exit(1)
