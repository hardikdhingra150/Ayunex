"""Explicit dry-run-first retention for stored export snapshots, not cases."""
import argparse
from datetime import timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.config import Settings
from app.models import Artifact, Event, Case, now

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--export-days',type=int,default=30)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if args.export_days<1:parser.error('Retention must be at least one day')
    with Session(create_engine(Settings().database_url)) as db:
        records=list(db.scalars(select(Artifact).where(Artifact.kind=='export',Artifact.created_at<now()-timedelta(days=args.export_days))))
        print(('Delete' if args.apply else 'Dry run: would delete'),len(records),'stored export snapshots; downloaded copies are not affected.')
        if args.apply:
            for record in records:
                case=db.get(Case,record.case_id)
                db.add(Event(case_id=case.id,tenant=case.tenant,actor='retention-worker',action='export.expired',payload={}))
                db.delete(record)
            db.commit()
