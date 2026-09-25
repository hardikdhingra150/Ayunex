"""Reproducible engineering checks; never represents a legal accuracy benchmark."""
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from app.corpus import CATALOG,sha
from app.retrieval import VERSION


def main():
    root=Path(__file__).resolve().parents[1]
    reports=root/'reports';reports.mkdir(exist_ok=True)
    xml=reports/'module-c-junit.xml'
    command=[sys.executable,'-m','pytest','-q','tests/test_knowledge.py','tests/test_corpus_hardening.py','tests/test_hosted_pipeline.py','--junitxml='+str(xml)]
    result=subprocess.run(command,cwd=root,check=False)
    summary={'at':datetime.now(timezone.utc).isoformat(),'engine':VERSION,
             'catalog_sha256':sha(CATALOG.read_bytes()),'fixture_type':'SYNTHETIC_ENGINEERING_ONLY',
             'legal_accuracy':'NOT_MEASURED','expert_benchmark':'NOT_PROVIDED','exit_code':result.returncode}
    if xml.exists():
        suites=ET.parse(xml).getroot().iter('testsuite')
        totals={'tests':0,'failures':0,'errors':0,'skipped':0}
        for suite in suites:
            for key in totals:totals[key]+=int(suite.get(key,0))
        summary.update(totals)
    (reports/'module-c-evaluation.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
