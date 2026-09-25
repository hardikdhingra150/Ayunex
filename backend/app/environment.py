"""Small local env loader: no shell expansion, execution, or secret printing."""
import os
import re
from pathlib import Path


def load_local_env(path):
    path=Path(path)
    if not path.exists():return
    for number,line in enumerate(path.read_text().splitlines(),1):
        line=line.strip()
        if not line or line.startswith('#'):continue
        key,separator,value=line.partition('=')
        if not separator or not re.fullmatch(r'[A-Z][A-Z0-9_]*',key):
            raise ValueError(f'Invalid environment setting on line {number}')
        if value.startswith(('"',"'")):
            if len(value)<2 or value[-1]!=value[0]:raise ValueError(f'Unclosed value on line {number}')
            value=value[1:-1]
        os.environ.setdefault(key,value)
