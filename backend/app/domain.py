import hashlib
import json
from pathlib import Path
from urllib.parse import quote

RULESET = json.loads(Path(__file__).with_name('rules.json').read_text())
DISCLAIMER = 'Information, not legal advice. Unreviewed routes do not establish approval, patentability or ABS compliance.'
DOMAINS = ['PATENT', 'TRADEMARK', 'GI', 'DESIGN', 'COPYRIGHT', 'TRADE_SECRET', 'PLANT_VARIETY', 'ABS_BIODIVERSITY', 'TRADITIONAL_KNOWLEDGE', 'AYUSH_DRUG', 'NEW_DRUG', 'PHYTOPHARMACEUTICAL', 'FOOD_AYURVEDA_AAHARA', 'FOOD_OTHER_NUTRACEUTICAL', 'COSMETIC', 'LABEL_ADVERTISING', 'INTERNATIONAL_TREATY', 'EXPORT_MARKET']
PORTALS = [
    {'id':'india-code','title':'India Code','url':'https://www.indiacode.nic.in/','domains':['PATENT','AYUSH_DRUG','ABS_BIODIVERSITY']},
    {'id':'ip-india','title':'IP India','url':'https://ipindia.gov.in/','domains':['PATENT','TRADEMARK','GI','DESIGN']},
    {'id':'nba','title':'National Biodiversity Authority','url':'https://nbaindia.org/','domains':['ABS_BIODIVERSITY']},
    {'id':'tkdl','title':'Traditional Knowledge Digital Library','url':'https://www.tkdl.res.in/','domains':['TRADITIONAL_KNOWLEDGE']},
    {'id':'fssai','title':'FSSAI','url':'https://www.fssai.gov.in/','domains':['FOOD_AYURVEDA_AAHARA','FOOD_OTHER_NUTRACEUTICAL']},
    {'id':'wipo','title':'WIPO','url':'https://www.wipo.int/','domains':['INTERNATIONAL_TREATY']},
]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def context(case):
    return digest({'case_id':case.id, 'passport_version':case.passport_version, 'passport':case.passport, 'jurisdiction':case.jurisdiction, 'as_of_date':case.as_of, 'query_kind':case.query_kind})


def known(fact):
    return bool(fact and not fact.get('unknown') and fact.get('value') not in (None, '', 'Unknown', 'UNKNOWN') and (fact.get('provenance') != 'extracted' or fact.get('confirmed')))


def value(facts, key):
    return facts[key]['value'] if known(facts.get(key)) else None


def contradictions(passport):
    facts = passport.get('facts', {})
    errors = []
    if value(facts, 'formula_matches_text') is True and value(facts, 'modified') is True:
        errors.append('Formula described as both unchanged and modified')
    if value(facts, 'intended_use') == 'COSMETIC' and value(facts, 'administration_route') == 'ORAL':
        errors.append('Cosmetic use conflicts with oral administration')
    origins = {i['origin'] for i in passport.get('ingredients', []) if i['origin'] != 'UNKNOWN'}
    if value(facts, 'origin') == 'IN' and 'FOREIGN' in origins:
        errors.append('Overall Indian origin conflicts with a foreign-origin ingredient')
    return errors


def classify(passport, jurisdiction, as_of, query_kind='PRODUCT_SPECIFIC'):
    if query_kind == 'GENERAL_INFORMATION':
        return {'route':'NOT_REQUIRED','alternatives':[],'conditions':[],'missing_facts':[],'conflicts':[],'facts_used':[],'evidence_refs':[],'ruleset_version':RULESET['version'],'review_required':False,'provisional':True,'reasons':['General information bypasses product classification']}
    facts = passport.get('facts', {})
    candidates, all_conditions, missing = [], [], set()
    for rule in RULESET['rules']:
        conditions = []
        for key, expected in rule['conditions'].items():
            actual = value(facts, key)
            state = 'unknown' if actual is None else ('met' if type(actual) is type(expected) and actual == expected else 'not_met')
            conditions.append({'fact_id':key, 'state':state, 'expected':expected, 'evidence_refs':[], 'effective_from':None, 'effective_to':None})
        states = [c['state'] for c in conditions]
        if 'not_met' not in states:
            candidates.append({'route':rule['route'], 'conditions':conditions, 'all_conditions_met':'unknown' not in states})
            missing.update(c['fact_id'] for c in conditions if c['state'] == 'unknown')
        all_conditions.append({'route':rule['route'], 'conditions':conditions})
    conflicts = contradictions(passport)
    in_scope = jurisdiction == {'layer':'NATIONAL','country':'IN','framework':None}
    return {'route':'UNRESOLVED' if in_scope else 'OUTSIDE_SUPPORTED_SCOPE', 'alternatives':candidates, 'conditions':all_conditions, 'missing_facts':sorted(missing), 'conflicts':conflicts, 'facts_used':sorted(k for k,f in facts.items() if known(f)), 'evidence_refs':[], 'ruleset_version':RULESET['version'], 'review_status':RULESET['review_status'], 'review_required':True, 'provisional':True, 'as_of_date':as_of, 'jurisdiction':jurisdiction, 'reasons':['Routing table is unvalidated; candidate matches are research paths, not legal classification.', *(['Conflicting facts require human review.'] if conflicts else []), *([] if in_scope else ['No reviewed country-specific classification adapter is enabled.'])], 'disclaimer':DISCLAIMER}


QUESTIONS = {
    'intended_use': ('What is the intended use?', 'प्रस्तावित उपयोग क्या है?',100),
    'administration_route': ('How is it administered?', 'इसका प्रयोग कैसे होता है?',90),
    'formula_matches_text': ('Does the exact formulation match an authoritative text?', 'क्या सूत्र प्रामाणिक ग्रंथ से मेल खाता है?',80),
    'method_matches_text': ('Does the preparation method match that text?', 'क्या निर्माण विधि उस ग्रंथ से मेल खाती है?',75),
    'ingredients_in_texts': ('Are all ingredients documented in authoritative texts?', 'क्या सभी सामग्री प्रामाणिक ग्रंथों में दर्ज हैं?',70),
    'modified': ('Has the formulation been modified?', 'क्या सूत्र बदला गया है?',65),
    'purified_fraction': ('Does it contain a purified or isolated fraction?', 'क्या इसमें पृथक या शुद्ध अंश है?',60),
    'food_subroute': ('Which food subroute are you researching?', 'आप किस खाद्य मार्ग का अध्ययन कर रहे हैं?',85),
}


def clarify(passport, classification):
    facts = passport.get('facts', {})
    missing = classification['missing_facts']
    candidates = [k for k in missing if k in QUESTIONS and not facts.get(k, {}).get('unknown')]
    candidates.sort(key=lambda k:(-QUESTIONS[k][2],k))
    return {'questions':[{'fact_id':k, 'text':QUESTIONS[k][0], 'text_hi':QUESTIONS[k][1], 'reason':'Differentiates possible research routes; not a legal test', 'requires_confirmation':True} for k in candidates[:3]], 'escalate':bool(classification.get('conflicts') or any(facts.get(k,{}).get('unknown') for k in missing)), 'never_reask_unknown':True}


def route_domains(passport, jurisdiction):
    domains = ['PATENT','ABS_BIODIVERSITY','TRADITIONAL_KNOWLEDGE','LABEL_ADVERTISING']
    use = value(passport.get('facts',{}),'intended_use')
    domains += {'FOOD':['FOOD_AYURVEDA_AAHARA','FOOD_OTHER_NUTRACEUTICAL'], 'COSMETIC':['COSMETIC'], 'THERAPEUTIC':['AYUSH_DRUG','NEW_DRUG','PHYTOPHARMACEUTICAL']}.get(use,[])
    if jurisdiction['layer']=='TREATY_FRAMEWORK':
        return ['INTERNATIONAL_TREATY']
    if jurisdiction['layer']=='EXPORT_MARKET' or jurisdiction.get('country')!='IN':
        domains.append('EXPORT_MARKET')
    return domains


def services(passport, jurisdiction, as_of):
    facts = passport.get('facts',{})
    ip = []
    for domain,key in [('PATENT','processing'),('TRADEMARK','brand'),('GI','geographic_link'),('DESIGN','ornamental_design'),('COPYRIGHT','original_content'),('TRADE_SECRET','confidential_knowhow'),('PLANT_VARIETY','new_plant_variety')]:
        ip.append({'domain':domain,'outcome':'Expert review required' if known(facts.get(key)) else 'Needs facts','missing_facts':[] if known(facts.get(key)) else [key], 'evidence_refs':[], 'review_required':True})
    abs_missing = [k for k in ['applicant','origin','activity','traditional_knowledge','exception'] if not known(facts.get(k))]
    if not passport.get('ingredients'): abs_missing.append('ingredients')
    query = ' '.join(i['name'] for i in passport.get('ingredients',[]))[:1500]
    return {'jurisdiction':jurisdiction, 'as_of_date':as_of, 'ip':ip,
        'abs':{'outcome':'Needs facts' if abs_missing else 'Expert review required','missing_facts':abs_missing,'clearance':False,'exceptions':'UNRESOLVED','authority':'UNRESOLVED — retrieve applicable NBA/SBB/BMC authority before routing','evidence_refs':[]},
        'traditional_knowledge':{'outcome':'Expert review required','query':query,'patent_search_url':'https://patentscope.wipo.int/','tkdl_pointer':'https://www.tkdl.res.in/','restricted_access_granted':False,'warning':'Request sourced review of traditional-knowledge exclusions. Search absence does not establish novelty or freedom to operate.'},
        'regulatory':{'route':'UNRESOLVED','competent_authority':None,'forms':[],'review_required':True},
        'international':{'framework':jurisdiction.get('framework'),'adoption':'UNKNOWN','entry_into_force':'UNKNOWN','country_participation':'UNKNOWN','market_approval':False,'review_required':True},
        'retrieval_requests':[{'domain':d,'jurisdiction':jurisdiction,'as_of_date':as_of,'allowed_access_classes':['PUBLIC'],'requirements':['Exact provision/version','Effective interval','Reviewed authority and applicability']} for d in route_domains(passport,jurisdiction)],
        'disclaimer':DISCLAIMER}


def checklist(passport, jurisdiction):
    return [{'id':str(i+1),'domain':domain,'title':title,'status':'TODO','evidence_refs':[],'kind':'PREPARATION_NOT_LEGAL_REQUIREMENT'} for i,(domain,title) in enumerate([
        ('REGULATORY','Confirm intended use, formulation source and evidence with a qualified reviewer'),
        ('PATENT','Record disclosures and ownership; commission prior-art review'),
        ('ABS_BIODIVERSITY','Confirm applicant, resource origin, activity and claimed exception'),
        ('TRADITIONAL_KNOWLEDGE','Record traditional knowledge and investigate authorized search access'),
        ('LABEL_ADVERTISING','Retrieve current claim, label and advertising requirements'),
        *([('EXPORT_MARKET','Obtain dated target-country market-access requirements')] if jurisdiction['layer']!='NATIONAL' or jurisdiction.get('country')!='IN' else [])])]
