"""Loopback-only local launcher. The private token is never printed or committed."""
import os
import secrets
from pathlib import Path
from alembic.config import Config
from alembic import command
import uvicorn
from app.environment import load_local_env

if __name__=='__main__':
    os.chdir(Path(__file__).parent)
    load_local_env('.env')
    os.environ.setdefault('GUIDANCE_MODE','corpus')
    if os.getenv('APP_ENV','development')!='development':
        raise SystemExit('dev.py is for local development only')
    token_path=Path('.dev-token')
    if not os.getenv('DEV_API_TOKEN'):
        if not token_path.exists():
            fd=os.open(token_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as stream:stream.write(secrets.token_urlsafe(32))
        os.chmod(token_path,0o600)
        os.environ['DEV_API_TOKEN']=token_path.read_text().strip()
    command.upgrade(Config('alembic.ini'),'head')
    print('AYUNEX backend: http://127.0.0.1:8000/docs — local token in backend/.dev-token')
    uvicorn.run('app.main:app',host='127.0.0.1',port=8000)
