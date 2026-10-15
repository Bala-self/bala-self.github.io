"""Small-container entrypoint: no browser or multiprocess cache split; honor host PORT."""
import os
import sys
port=os.getenv('PORT','8000')
if not port.isdigit() or not 1<=int(port)<=65535:
    raise SystemExit('PORT must be an integer from 1 to 65535.')
os.execvp(sys.executable,[sys.executable,'-m','uvicorn','app:app','--host','0.0.0.0','--port',port,'--workers','1','--no-access-log','--no-proxy-headers'])
