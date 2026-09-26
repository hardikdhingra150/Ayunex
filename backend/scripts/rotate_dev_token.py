"""Invalidate a leaked local credential. Never prints the new credential."""
import os
import secrets
from pathlib import Path
from app.environment import load_local_env

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1];load_local_env(root/'.env')
    if os.getenv('APP_ENV','development')!='development':raise SystemExit('Local development only')
    if os.getenv('DEV_API_TOKEN'):raise SystemExit('Rotate DEV_API_TOKEN in your private environment instead')
    temp=root/('.dev-token-'+secrets.token_hex(8))
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:stream.write(secrets.token_urlsafe(32))
    os.replace(temp,root/'.dev-token')
    print('Local development credential rotated. Restart backend; existing token holders must reconnect.')
