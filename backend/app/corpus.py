"""Bounded public-document ingestion. Never treats downloading as legal review."""
import hashlib
from datetime import date
import ipaddress
import json
import re
import socket
import subprocess
import sys
import os
from pathlib import Path
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import httpx
from sqlalchemy import select, or_
from .models import SourceDocument, Passage, now
from .retrieval import search
from .legal_parser import chunks,validate_pages,VERSION as PARSER_VERSION

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT.parent/'data/corpus/catalog.json'
RAW=ROOT.parent/'data/corpus/raw'
HOSTS={'ipindia.gov.in','www.ipindia.gov.in','www.indiacode.nic.in','indiacode.nic.in','indiacode.gov.in','www.indiacode.gov.in','upload.indiacode.nic.in','nbaindia.org','www.nbaindia.nic.in','nbaindia.nic.in','fssai.gov.in','www.fssai.gov.in'}
MAX_BYTES=15*1024*1024
USER_AGENT='AYUNEX-ResearchCorpus/1.0'


def sources():return json.loads(CATALOG.read_text())['sources']
def sha(data):return hashlib.sha256(data).hexdigest()


def validate_url(url):
    p=urlparse(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):
        raise ValueError('Source URL is outside the HTTPS authority allowlist')
    addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):
        raise ValueError('Non-public source address rejected')


def fetch(url,client,limit=MAX_BYTES):
    for _ in range(4):
        validate_url(url)
        with client.stream('GET',url,headers={'User-Agent':USER_AGENT},follow_redirects=False) as response:
            if response.status_code in (301,302,303,307,308):
                url=urljoin(url,response.headers['location']);continue
            response.raise_for_status()
            chunks=[];size=0
            for part in response.iter_bytes():
                size+=len(part)
                if size>limit:raise ValueError('Document exceeds byte limit')
                chunks.append(part)
            return b''.join(chunks),url,response.headers.get('content-type','')
    raise ValueError('Redirect limit exceeded')


def permitted(url,client):
    p=urlparse(url);robots=p.scheme+'://'+p.netloc+'/robots.txt'
    try:body,_,_=fetch(robots,client,128000)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code==404:return True
        raise ValueError('Robots policy unavailable; ingestion deferred') from None
    parser=RobotFileParser();parser.parse(body.decode('utf-8',errors='replace').splitlines())
    return parser.can_fetch(USER_AGENT,url)


def extract_pdf(path):
    result=subprocess.run([sys.executable,'-m','scripts.extract_pdf',str(path)],capture_output=True,text=True,timeout=1800 if os.getenv('OCR_ENABLED')=='true' else 40,check=True)
    return json.loads(result.stdout)


def persist(db,source,data,final_url,pages):
    fingerprint=sha(data)
    existing=db.scalar(select(SourceDocument).where(SourceDocument.source_key==source['id'],SourceDocument.sha256==fingerprint))
    if existing:return {'source':source['id'],'status':'UNCHANGED','document_id':existing.id,'sha256':fingerprint}
    validate_pages(pages)
    for old in db.scalars(select(SourceDocument).where(SourceDocument.source_key==source['id'])):old.active=False
    document=SourceDocument(source_key=source['id'],sha256=fingerprint,title=source['title'],authority=source['authority'],url=final_url,domain=source['domain'],country='IN',active=True,metadata_json={'access':'PUBLIC','review_status':'PENDING','discovery_url':source.get('discovery_url'),'page_count':len(pages),'effective_interval':'UNKNOWN','download_is_not_legal_review':True})
    db.add(document);db.flush()
    count=0
    for chunk in chunks(pages):
        passage=chunk.pop('text').strip()
        db.add(Passage(document_id=document.id,page=chunk['page'],text=passage,sha256=sha(passage.encode()),review={},extraction=chunk))
        count+=1
    document.metadata_json={**document.metadata_json,'parser_version':PARSER_VERSION}
    db.flush()
    return {'source':source['id'],'status':'IMPORTED_PENDING_REVIEW','document_id':document.id,'sha256':fingerprint,'pages':len(pages),'passages':count}


def ingest(db,source):
    if source['kind']!='PDF' or source['access']!='PUBLIC':
        return {'source':source['id'],'status':'POINTER_ONLY','reason':'No automated restricted/registry access'}
    with httpx.Client(timeout=httpx.Timeout(25,connect=10),trust_env=False) as client:
        if not permitted(source['url'],client):raise ValueError('Robots policy disallows this document')
        data,url,mime=fetch(source['url'],client)
        if not data.startswith(b'%PDF-') or 'pdf' not in mime.lower():raise ValueError('Expected a PDF; login, error or challenge content rejected')
    RAW.mkdir(parents=True,exist_ok=True)
    path=RAW/(sha(data)+'.pdf')
    if not path.exists():path.write_bytes(data)
    pages=extract_pdf(path)
    result=persist(db,source,data,url,pages)
    result['raw_path']=str(path.relative_to(ROOT.parent))
    return result
