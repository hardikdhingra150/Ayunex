"""Install one visually/source-checked excerpt, never bulk-approve the corpus.

The immutable PDF page and the official Section 3 web page were checked by an
AI assistant on 26 September 2026. This is NOT expert legal certification.
Only the pinned source version and exact clause below may be installed.
"""
import argparse
from datetime import date
from hashlib import sha256
from pathlib import Path
from pypdf import PdfReader
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from app.config import Settings
from app.environment import load_local_env
from app.models import SourceDocument,Passage,CorpusReviewEvent,now

ROOT=Path(__file__).resolve().parents[2]
DOCUMENT_HASH='d57084888c69d70b16ed6a52a612363a526994203effa58880a26faaaa6e0678'
EXPECTED='(p) an invention which, in effect, is traditional knowledge or which is an aggregation or duplication of known properties of traditionally known component or components.]'
PASSAGE_ID='pilot-patents-section-3p-v1'


def prepare(db):
    doc=db.scalar(select(SourceDocument).where(SourceDocument.sha256==DOCUMENT_HASH,SourceDocument.active.is_(True)))
    if not doc:raise ValueError('Pinned official Patents Act source must be imported first')
    path=ROOT/'data/corpus/raw'/f'{DOCUMENT_HASH}.pdf'
    if sha256(path.read_bytes()).hexdigest()!=DOCUMENT_HASH:raise ValueError('Source hash mismatch')
    page=PdfReader(path).pages[9].extract_text()
    start=page.index('(p) an invention');end=page.index('components.]',start)+len('components.]')
    text=page[start:end]
    if ' '.join(text.split())!=EXPECTED:raise ValueError('Clause differs from checked source; review required')
    existing=db.get(Passage,PASSAGE_ID)
    if existing:return {'status':'ALREADY_EXISTS_REVIEW_NOT_OVERRIDDEN','passage_id':existing.id}
    review={'approved':True,'review_status':'SOURCE_TEXT_CHECKED','expert_reviewed':False,
            'provision':'Patents Act 1970, Section 3(p)', 'effective_from':'2003-05-20',
            'effective_to':None,'review_valid_until':'2026-10-03','reviewer':'ai-source-check:2026-09-26',
            'reviewed_at':now().isoformat(),'conflict':False,
            'notes':'AI-assisted source-text review only, not expert legal review. PDF page 10 visually checked including amendment footnote (effective 20 May 2003). Clause cross-checked against https://www.ipindia.gov.in/acts/patent-act-1970/section-3 . No certification of current-law completeness. One-clause informational pilot only.'}
    if date.today()>date(2026,10,3):raise ValueError('Pilot review expired; fresh review required')
    db.add(Passage(id=PASSAGE_ID,document_id=doc.id,page=10,text=text,sha256=sha256(text.encode()).hexdigest(),
                   review=review,review_revision=1,extraction={'parser_version':'source-checked-pilot-1','page':10,
                   'segments':[{'page':10,'start':start,'end':end}],'quarantined':False,'scope':'SECTION_3_P_ONLY'}))
    db.flush()
    db.add(CorpusReviewEvent(passage_id=PASSAGE_ID,actor=review['reviewer'],payload=review))
    return {'status':'SOURCE_TEXT_CHECKED','expert_reviewed':False,'passage_id':PASSAGE_ID}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    load_local_env(ROOT/'backend/.env');settings=Settings()
    if settings.environment!='development':raise SystemExit('Pilot installer is development-only')
    if not args.apply:raise SystemExit('Use --apply to install the single, audited source-text pilot')
    with Session(create_engine(settings.database_url)) as db:
        result=prepare(db);db.commit();print(result)
