import argparse
import json
import time
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.config import Settings
from app.corpus import sources,ingest,ROOT
from app.models import now

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source');parser.add_argument('--list',action='store_true');args=parser.parse_args()
    catalog=sources()
    if args.source:catalog=[s for s in catalog if s['id']==args.source]
    if not catalog:raise SystemExit('Unknown catalog source')
    if args.list:
        print(json.dumps(catalog,indent=2));raise SystemExit(0)
    results=[];engine=create_engine(Settings().database_url)
    for source in catalog:
        with Session(engine) as db:
            try:result=ingest(db,source);db.commit()
            except Exception as error:
                db.rollback();result={'source':source['id'],'status':'FAILED','error':type(error).__name__+': '+str(error)[:350]}
            results.append(result);print(json.dumps(result),flush=True)
        time.sleep(1)
    report={'completed_at':now().isoformat(),'results':results,'automatic_approvals':0,'note':'Imported content requires expert review; this report is not a completeness claim.'}
    import os
    target=Path(os.getenv('CORPUS_REPORT_PATH',str(ROOT.parent/'data/corpus/ingestion-report.json')))
    if args.source and target.exists():
        previous=json.loads(target.read_text())
        merged={r['source']:r for r in previous.get('results',[])}
        merged.update({r['source']:r for r in results})
        report['results']=list(merged.values())
    target.write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(1 if any(r['status']=='FAILED' for r in results) else 0)
