"""Explicit local reparse. Preserves old passages and invalidates their approvals."""
import argparse
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from app.config import Settings
from app.models import SourceDocument,Passage
from app.corpus import RAW,extract_pdf,sha
from app.legal_parser import chunks,validate_pages,VERSION


def reparse(db,doc,expected_sha):
    if doc.sha256!=expected_sha:raise ValueError('Source version changed')
    path=RAW/(doc.sha256+'.pdf')
    if sha(path.read_bytes())!=doc.sha256:raise ValueError('Raw file checksum mismatch')
    if doc.metadata_json.get('parser_version')==VERSION:return {'status':'UNCHANGED'}
    pages=extract_pdf(path);validate_pages(pages)
    parsed=chunks(pages)
    if not parsed:raise ValueError('No usable passages; old parse retained')
    for p in db.scalars(select(Passage).where(Passage.document_id==doc.id)):p.active=False
    for item in parsed:
        text=item.pop('text').strip()
        db.add(Passage(document_id=doc.id,page=item['page'],text=text,sha256=sha(text.encode()),extraction=item,review={}))
    doc.metadata_json={**doc.metadata_json,'parser_version':VERSION,'reparse_requires_new_reviews':True}
    return {'status':'REPARSED_PENDING_REVIEW','passages':len(parsed)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--document-id',required=True);parser.add_argument('--expected-sha256',required=True);args=parser.parse_args()
    with Session(create_engine(Settings().database_url)) as db:
        doc=db.get(SourceDocument,args.document_id)
        if not doc or not doc.active:raise SystemExit('Active document not found')
        print(reparse(db,doc,args.expected_sha256));db.commit()
