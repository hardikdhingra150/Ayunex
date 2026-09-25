"""Regenerate the API artifact after schema edits."""
import json
from pathlib import Path
from app.main import app

if __name__=='__main__':
    Path('openapi.json').write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2)+'\n')
