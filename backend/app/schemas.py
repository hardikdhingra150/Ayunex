from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Principal(Strict):
    subject: str = Field(min_length=1, max_length=160)
    tenant: str = Field(min_length=1, max_length=160)
    role: Literal['user', 'facilitator', 'curator', 'administrator', 'auditor']


class Jurisdiction(Strict):
    layer: Literal['NATIONAL', 'TREATY_FRAMEWORK', 'EXPORT_MARKET']
    country: str | None = Field(default=None, pattern=r'^[A-Z]{2}$')
    framework: Literal['TRIPS', 'CBD', 'NAGOYA', 'GRATK', 'PCT', 'MADRID', 'HAGUE', 'BUDAPEST'] | None = None

    @model_validator(mode='after')
    def distinct(self):
        if self.layer == 'TREATY_FRAMEWORK':
            if not self.framework or self.country:
                raise ValueError('Treaty context needs one named framework, not country approval')
        elif not self.country or self.framework:
            raise ValueError('National/export context needs one country, not a treaty framework')
        return self


class Consent(Strict):
    accepted: Literal[True]
    notice_version: Literal['case-notice-v1']


class CreateCase(Strict):
    title: str = Field(min_length=3, max_length=160)
    query_kind: Literal['GENERAL_INFORMATION', 'PRODUCT_SPECIFIC'] = 'PRODUCT_SPECIFIC'
    jurisdiction: Jurisdiction
    as_of_date: date
    consent: Consent


class PatchCase(Strict):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=3, max_length=160)
    jurisdiction: Jurisdiction | None = None
    as_of_date: date | None = None
    archived: bool | None = None


class Fact(Strict):
    value: str | bool | None = None
    provenance: Literal['user-entered', 'extracted', 'facilitator-confirmed'] = 'user-entered'
    confirmed: bool = False
    unknown: bool = False

    @model_validator(mode='after')
    def limit(self):
        if isinstance(self.value, str) and len(self.value) > 2000:
            raise ValueError('Fact text too long; confidential ratios are not required')
        if self.unknown:
            self.value = None
        return self


class Ingredient(Strict):
    name: str = Field(min_length=1, max_length=160)
    biological_type: Literal['PLANT', 'ANIMAL', 'MICROBIAL', 'NON_BIOLOGICAL', 'UNKNOWN']
    part: str = Field(default='Unknown', max_length=160)
    origin: Literal['IN', 'FOREIGN', 'MIXED', 'UNKNOWN'] = 'UNKNOWN'
    sourcing: Literal['CULTIVATED', 'WILD', 'PURCHASED', 'UNKNOWN'] = 'UNKNOWN'
    alias_unresolved: bool = True


class Passport(Strict):
    facts: dict[str, Fact] = Field(default_factory=dict, max_length=40)
    ingredients: list[Ingredient] = Field(default_factory=list, max_length=50)

    @model_validator(mode='after')
    def names(self):
        allowed = {'ingredient_summary', 'intended_use', 'claims', 'dosage_form', 'administration_route', 'formula_source', 'formula_matches_text', 'method_matches_text', 'ingredients_in_texts', 'modified', 'purified_fraction', 'food_subroute', 'processing', 'evidence', 'applicant', 'origin', 'activity', 'traditional_knowledge', 'exception', 'commercial_stage', 'target_market', 'prior_disclosure', 'brand', 'geographic_link', 'ornamental_design', 'original_content', 'confidential_knowhow', 'new_plant_variety', 'ownership'}
        if set(self.facts) - allowed:
            raise ValueError('Unknown fact keys: ' + ', '.join(sorted(set(self.facts) - allowed)))
        enums={'intended_use':{'THERAPEUTIC','FOOD','COSMETIC','RESEARCH'},'administration_route':{'ORAL','EXTERNAL','OTHER'},'food_subroute':{'AYURVEDA_AAHARA','OTHER'},'origin':{'IN','FOREIGN','MIXED'}}
        boolean_keys={'formula_matches_text','method_matches_text','ingredients_in_texts','modified','purified_fraction'}
        for key,fact in self.facts.items():
            if fact.unknown or fact.value is None:
                continue
            if key in enums and fact.value not in enums[key]:
                raise ValueError('Invalid option for '+key+'; use unknown=true when uncertain')
            if key in boolean_keys and not isinstance(fact.value,bool):
                raise ValueError(key+' requires boolean or explicit unknown')
        return self


class Answers(Strict):
    expected_revision: int = Field(ge=1)
    passport: Passport


class Guidance(Strict):
    question: str = Field(min_length=3, max_length=4000)
    original_language: Literal['en', 'hi'] = 'en'
    allow_hosted_processing: bool = False


class GeneralGuidance(Guidance):
    jurisdiction: Jurisdiction
    as_of_date: date


class Escalate(Strict):
    expected_revision: int = Field(ge=1)
    question: str = Field(min_length=3, max_length=4000)
    consent: Literal[True]
    sharing_scope: Literal['CURRENT_CASE_FACTS_AND_EVIDENCE']
    consent_version: Literal['facilitator-sharing-v1']


class Review(Strict):
    expected_revision: int = Field(ge=1)
    comment: str = Field(min_length=3, max_length=4000)
    status: Literal['Under human review', 'Reviewed']


class ActionUpdate(Strict):
    expected_revision: int = Field(ge=1)
    status: Literal['TODO', 'IN_PROGRESS', 'DONE']


class SearchRecord(Strict):
    expected_revision: int = Field(ge=1)
    query: str = Field(min_length=1, max_length=2000)
    notes: str = Field(max_length=4000)
    source_url: str = Field(pattern=r'^https://', max_length=2000)


SUPPORT = Literal['SUPPORTED_IN_SCOPE', 'MISSING_FACTS', 'MISSING_EVIDENCE', 'CONFLICTING_SOURCES', 'OUT_OF_SCOPE', 'REVIEW_REQUIRED']


class Citation(Strict):
    id: str
    authority: str
    title: str
    url: str = Field(pattern=r'^https://')
    provision: str = Field(min_length=1)
    excerpt: str = Field(min_length=1)
    version: str = Field(min_length=1)
    jurisdiction: Jurisdiction
    effective_from: date
    effective_to: date | None = None
    retrieved_at: str
    review_status: Literal['VERIFIED','SOURCE_TEXT_CHECKED']
    access_class: Literal['PUBLIC']


class Claim(Strict):
    id: str
    text: str = Field(min_length=1, max_length=10000)
    jurisdiction: Jurisdiction
    citation_ids: list[str] = Field(min_length=1)


class GuidanceSection(Strict):
    id: str
    title: str
    support: SUPPORT
    claims: list[Claim]
    reason: str = Field(max_length=2000)


class RetrievalTrace(Strict):
    engine: str
    mode: Literal['LOCAL_EXTRACTIVE','HOSTED_RAG']
    steps: list[str]
    repair_count: int = Field(ge=0, le=1)
    translation: Literal['NOT_PERFORMED']
    source_versions: list[str]
    evidence_ids: list[str]
    verification: Literal['NO_CLAIMS','EXACT_QUOTES_VERIFIED','MODEL_REVIEW_PASSED','REJECTED']
    model: str | None = None
    prompt_version: str | None = None


class GuidanceAnswer(Strict):
    request_id: str
    context_hash: str
    jurisdiction: Jurisdiction
    as_of_date: date
    support: SUPPORT
    sections: list[GuidanceSection] = Field(max_length=20)
    citations: list[Citation] = Field(max_length=100)
    retrieval_trace: RetrievalTrace | None = None

    @model_validator(mode='after')
    def firewall(self):
        ids = {c.id for c in self.citations}
        if len(ids) != len(self.citations):
            raise ValueError('Duplicate citations')
        for citation in self.citations:
            if citation.jurisdiction != self.jurisdiction:
                raise ValueError('Mixed jurisdiction evidence')
            if citation.effective_from > self.as_of_date or (citation.effective_to and self.as_of_date >= citation.effective_to):
                raise ValueError('Evidence is outside effective interval')
        claim_ids = []
        for section in self.sections:
            if section.support == 'SUPPORTED_IN_SCOPE' and not section.claims:
                raise ValueError('Supported sections require cited claims')
            if section.support != 'SUPPORTED_IN_SCOPE' and section.claims:
                raise ValueError('Unresolved sections must not expose legal claim prose')
            for claim in section.claims:
                claim_ids.append(claim.id)
                if claim.jurisdiction != self.jurisdiction or not set(claim.citation_ids) <= ids:
                    raise ValueError('Unbound claim or mixed jurisdiction')
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError('Duplicate claim IDs')
        if self.support == 'SUPPORTED_IN_SCOPE' and (not self.sections or any(s.support != 'SUPPORTED_IN_SCOPE' for s in self.sections)):
            raise ValueError('Partial answers cannot claim full support')
        return self


class CaseResponse(Strict):
    id: str
    title: str
    status: str
    query_kind: Literal['GENERAL_INFORMATION','PRODUCT_SPECIFIC']
    jurisdiction: Jurisdiction
    as_of_date: date
    passport_version: int
    revision: int
    created_at: datetime
    updated_at: datetime
    context_hash: str


class ArtifactResponse(Strict):
    id: str
    kind: str
    context_hash: str
    stale: bool
    created_at: datetime
    payload: dict
    case_revision: int


class PassportResponse(Strict):
    passport: Passport
    version: int
    revision: int
    conflicts: list[str]
