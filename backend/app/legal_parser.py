"""Conservative structural segmentation; inferred locators always need review.

Never splits within an explicit provision. Unstructured pages remain whole and
oversized segments are quarantined. Offsets refer to the extracted page text,
not byte positions in the PDF. Table reading order still needs visual review.
"""
import re

VERSION='provision-parser-1'
HEADING=re.compile(r'(?m)^(?:(?:Section|Rule|Article)\s+\d+[A-Za-z]?(?:\([^\n)]*\))?\b[^\n]*|\d+[A-Z]?\.\s+[A-Z][^\n]{2,120}[.—–][^\n]*)')


def validate_pages(pages):
    if not pages or not any(len(p['text'].strip())>100 for p in pages):
        raise ValueError('No usable text; OCR/manual review required')
    if sum(len(p['text'].strip())>=40 for p in pages)/len(pages)<0.8:
        raise ValueError('Insufficient text coverage across PDF pages; OCR/manual review required')


def chunks(pages):
    output=[]
    current=None
    for page in pages:
        text=page['text']
        matches=list(HEADING.finditer(text))
        spans=[]
        if not matches:
            spans=[(0,len(text),None)]
        else:
            if matches[0].start():spans.append((0,matches[0].start(),None))
            spans.extend((m.start(),matches[i+1].start() if i+1<len(matches) else len(text),m.group(0)) for i,m in enumerate(matches))
        for start,end,heading in spans:
            if not text[start:end].strip():continue
            # A page continuation remains attached to its preceding explicit provision.
            if heading is None and current and current['locator_candidate'] and start==0:
                current['text']+='\n'+text[start:end]
                current['segments'].append({'page':page['page'],'start':start,'end':end})
                current['page_end']=page['page']
                current['ocr']=current['ocr'] or page.get('method')=='OCR'
                current['quarantined']=len(current['text'])>10000
                continue
            current={'text':text[start:end],'page':page['page'],'page_end':page['page'],
                     'locator_candidate':heading,'segments':[{'page':page['page'],'start':start,'end':end}],
                     'parser_version':VERSION,'ocr':page.get('method')=='OCR',
                     'ocr_confidence':page.get('confidence'),'quarantined':end-start>10000,
                     'structure':'PROVISION_CANDIDATE' if heading else 'UNSTRUCTURED_PAGE',
                     'requires_visual_review':True}
            output.append(current)
    for item in output:
        leading=len(item['text'])-len(item['text'].lstrip())
        trailing=len(item['text'])-len(item['text'].rstrip())
        item['segments'][0]['start']+=leading
        item['segments'][-1]['end']-=trailing
        item['text']=item['text'].strip()
    return [item for item in output if len(item['text'])>=40]
