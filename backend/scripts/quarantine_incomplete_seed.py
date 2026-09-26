"""Quarantine the observed partial ABS table without deleting source/history."""
import argparse
from pathlib import Path
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from app.models import Passage,CorpusReviewEvent,now
from app.config import Settings
from app.environment import load_local_env

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    load_local_env(Path(__file__).resolve().parents[1]/'.env');settings=Settings()
    if settings.environment!='development' or not args.apply:raise SystemExit('Development only; --apply required')
    with Session(create_engine(settings.database_url)) as db:
        changed=0
        for p in db.scalars(select(Passage).where(Passage.active.is_(True))):
            normalized=' '.join(p.text.split())
            if 'Procedure for prior intimation for commercial utilisation' not in normalized or not normalized.endswith('1. Up to 5 crore Nil'):continue
            if p.extraction.get('quarantined'):continue
            reason='Release audit: ABS Regulation 5 excerpt ends after the first table row; later turnover bands/conditions are absent. Reparse and review the full provision before approval.'
            p.review={**p.review,'approved':False,'reviewer':'release-audit:2026-09-26','reviewed_at':now().isoformat(),'notes':reason}
            p.review_revision+=1
            p.extraction={**p.extraction,'quarantined':True,'quarantine_reason':reason}
            db.add(CorpusReviewEvent(passage_id=p.id,actor='release-audit:2026-09-26',payload=p.review));changed+=1
        db.commit();print({'quarantined_partial_table_passages':changed,'source_documents_deleted':0})
