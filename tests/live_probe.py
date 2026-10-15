"""Opt-in upstream probe. Never a fixture-based claim of live success."""
import json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
urls=sys.argv[1:] or ['https://www.instagram.com/p/BQ0eAlwhDrw/','https://www.instagram.com/reel/Chunk8-jurw/','https://www.instagram.com/tv/BkfuX9UB-eK/']
results=[]
for url in urls:
    start=time.monotonic()
    try:
        r=httpx.post('http://127.0.0.1:8000/api/resolve',json={'url':url},timeout=100)
        body=r.json()
        result={'url':url,'status':r.status_code,'seconds':round(time.monotonic()-start,2),'method':body.get('method'),'error':body.get('error'),'message':body.get('message'),'item_count':len(body.get('items',[]))}
    except Exception as exc:result={'url':url,'error':type(exc).__name__,'seconds':round(time.monotonic()-start,2)}
    results.append(result);print(json.dumps(result),flush=True)
Path('artifacts/live-results.json').write_text(json.dumps({'date':'2026-10-15','source':'Historical public test URLs in the installed yt-dlp Instagram extractor. Current availability not independently confirmed.','results':results},indent=2))
