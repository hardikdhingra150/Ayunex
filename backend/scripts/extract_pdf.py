"""Isolated, time-bounded PDF extraction worker; no network or execution of PDF scripts."""
import json
import sys
import resource
import csv
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from pypdf import PdfReader


def ocr_page(path,page_number):
    if not shutil.which('tesseract') or not shutil.which('pdftoppm'):
        raise ValueError('OCR requires Tesseract and Poppler; no text has been fabricated')
    with tempfile.TemporaryDirectory(prefix='ayunex-ocr-') as scratch:
        prefix=str(Path(scratch)/'page')
        subprocess.run(['pdftoppm','-f',str(page_number),'-l',str(page_number),'-singlefile',
                        '-scale-to','2400','-png',str(path),prefix],check=True,timeout=30,capture_output=True)
        result=subprocess.run(['tesseract',prefix+'.png','stdout','-l',os.getenv('OCR_LANGUAGES','eng'),
                               '--psm','3','tsv'],check=True,timeout=60,capture_output=True,text=True)
        rows=list(csv.DictReader(io.StringIO(result.stdout),delimiter='\t'))
        lines={};confidence=[]
        for row in rows:
            word=row.get('text','').strip()
            if not word:continue
            certainty=float(row['conf'])
            if certainty<0:continue
            confidence.append(certainty)
            key=(row['block_num'],row['par_num'],row['line_num'])
            lines.setdefault(key,[]).append(word)
        average=sum(confidence)/max(1,len(confidence))
        if average<80:raise ValueError('OCR confidence below engineering threshold; manual transcription required')
        return '\n'.join(' '.join(words) for words in lines.values()),round(average,2)

def main():
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    if sys.platform.startswith('linux'):resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    path=Path(sys.argv[1]);reader=PdfReader(path)
    if reader.is_encrypted or len(reader.pages)>300:raise ValueError('Encrypted/oversized PDF requires manual review')
    output=[];total=0;ocr_count=0
    for i,page in enumerate(reader.pages):
        text=page.extract_text() or '';method='TEXT';confidence=None
        if len(text.strip())<40 and os.getenv('OCR_ENABLED')=='true':
            ocr_count+=1
            if ocr_count>20:raise ValueError('OCR page budget exceeded; split into reviewed batches outside automatic ingestion')
            text,confidence=ocr_page(path,i+1);method='OCR'
        total+=len(text)
        if total>2_000_000:raise ValueError('Extraction character budget exceeded')
        output.append({'page':i+1,'text':text,'method':method,'confidence':confidence})
    print(json.dumps(output,ensure_ascii=False))

if __name__=='__main__':main()
