# Module B — Backend and Domain Logic

**26 September 2026 audit:** This specification is not a completion certificate. Current fixes, tested scope and remaining production gates are recorded in [the release audit](../RELEASE_AUDIT_2026-09-26.md). Local guest access and source-text pilot evidence do not satisfy real identity or expert legal approval requirements.

**Implementation update — 23 September 2026:** The executable AYUNEX backend now lives in [backend/README.md](../../backend/README.md). See [delivery status and release gates](../PRODUCTION_READINESS.md). The specification below remains the target; expert-reviewed legal journeys and live Modules C/D are not claimed complete.

**Revision:** 2 · 9 September 2026. Updated implementation specification, not implemented application code. [Research and change rationale](../IP-SAKTI_RESEARCH_AND_SOLUTION.md). These revised module documents supersede conflicting details in the older master blueprint.

**Owner:** Backend and domain team  
**Primary stack:** FastAPI, Pydantic, SQLAlchemy, Alembic and PostgreSQL; Redis only when queue/cache needs justify it  
**Depends on:** Module D identity/infrastructure and Module C retrieval/guidance services  
**Provides:** Stable APIs and legal/regulatory routing for Module A

## 1. Objective

Create the deterministic application core. Module B owns cases, Product Passports, provisional classification, clarifying questions, jurisdiction separation, domain routing, IP/ABS/regulatory checklists and human escalation.

Module B must decide **what kind of question should be answered and which evidence is required**. It must not fabricate legal conclusions or rely on the LLM for deterministic classification.

## 2. Backend submodules

### B1 — Identity and organisation integration

**Responsibilities:**

- Consume verified identity from Module D
- Enforce organisation/tenant boundaries
- Apply roles: user, facilitator, curator, administrator and auditor
- Expose permission checks to all services

### B2 — Case service

**Responsibilities:**

- Create, read, update, archive and delete cases
- Store case status and jurisdiction contexts
- Maintain answer and export history
- Enforce tenant isolation
- Publish domain events for audit and background processing

### B3 — Product Passport service

**Responsibilities:**

- Validate structured facts through Pydantic schemas
- Version every change
- Record fact provenance
- Normalize ingredients, claims and source descriptions
- Detect internal contradictions
- Produce a stable passport snapshot for a classification run
- Allow general-information queries without Passport/classification
- Require confirmation of decisive extracted facts; preserve unknown values and ambiguous botanical aliases
- Collect only relevant facts; confidential ratios are not mandatory by default

**Example top-level schema:**

```json
{
  "intended_use": {},
  "claims": [],
  "dosage_form": "",
  "administration_route": "",
  "formula_source": {},
  "ingredients": [],
  "processing": {},
  "evidence": [],
  "applicant_profile": {},
  "biological_origin": [],
  "commercial_stage": "",
  "target_markets": [],
  "prior_disclosures": []
}
```

### B4 — Provisional formulation classification engine

**Candidate routes:**

1. Classical/generic Ayurveda medicine
2. Patent-or-proprietary Ayurveda medicine
3. New/non-classical drug review (not a universal statutory bucket)
4. Phytopharmaceutical
5. Food, with distinct Ayurveda Aahara and other food/nutraceutical subroutes
6. Cosmetic
7. Mixed/ambiguous or insufficient facts

**Implementation rules:**

- Store rules as versioned JSON/YAML decision tables.
- Execute rules in code; do not ask the LLM to choose a route.
- Record matched conditions, unmatched required facts and conflicting conditions.
- Return a primary candidate only when supported; otherwise return unresolved or outside-supported-scope.
- Label the result provisional.
- Require expert review before publishing a production ruleset.
- Evaluate each condition as `met`, `not_met` or `unknown`, with fact IDs, provision-version evidence and rule effective intervals.
- Never default to proprietary AYUSH when classical/phytopharmaceutical eligibility fails.
- Regulatory, IP and ABS results are independent assessments; “patent or proprietary” is not a patentability finding.

**Classification response:**

```json
{
  "route": "UNRESOLVED",
  "alternatives": [],
  "conditions": [],
  "evidence_refs": [],
  "reasons": [],
  "facts_used": [],
  "missing_facts": [],
  "conflicts": [],
  "ruleset_version": "ayush-classifier-0.2.0",
  "review_required": true
}
```

### B5 — Clarifying-question engine

**Goal:** Minimise user effort while resolving routing uncertainty.

**Logic:**

1. Collect unresolved differentiating facts from candidate routes.
2. Remove facts already answered or irrelevant.
3. Score questions by expected uncertainty reduction and risk.
4. Ask the highest-value one to three questions.
5. Re-run classification after each response batch.
6. Escalate if a critical fact cannot be established.

The engine uses curated question templates. An LLM may translate or simplify wording but cannot change the fact being requested.

General queries bypass clarification/classification. If decisive facts cannot be supplied, stop re-asking and offer supported partial guidance or escalation.

### B6 — Jurisdiction firewall and domain router

**Responsibilities:**

- Require a jurisdiction context for dependent questions
- Keep India and target-country workspaces separate
- Activate only relevant domain modules
- Attach jurisdiction to each retrieval request and answer claim
- Reject mixed evidence before final output
- Distinguish `NATIONAL`, `TREATY_FRAMEWORK` and `EXPORT_MARKET`; require a country for national/export contexts and a named framework for treaty guidance
- Check treaty adoption, entry into force and country participation separately using dated evidence
- Recompute dependent assessments when facts, jurisdiction or as-of date change

**Domain routes:**

```text
PATENT
TRADEMARK
GI
DESIGN
COPYRIGHT
TRADE_SECRET
PLANT_VARIETY
ABS_BIODIVERSITY
TRADITIONAL_KNOWLEDGE
AYUSH_DRUG
NEW_DRUG
PHYTOPHARMACEUTICAL
FOOD_AYURVEDA_AAHARA
FOOD_OTHER_NUTRACEUTICAL
COSMETIC
LABEL_ADVERTISING
INTERNATIONAL_TREATY
EXPORT_MARKET
```

### B7 — IP strategy service

**Responsibilities:**

- Route patentability and statutory-exclusion checks
- Identify brand/trademark relevance
- Identify GI, design, copyright, trade-secret and plant-variety relevance
- Create search and filing-path pointers
- Separate Indian rights from PCT/Madrid/Hague pathways
- Flag prior disclosure and ownership issues

**Output categories:** `Potentially relevant`, `Unlikely`, `Needs facts`, `Expert review required`.

The service must never predict grant or enforceability.

Absence of prior art in our corpus is not proof of novelty or freedom to operate. Regulatory status never establishes patentability.

### B8 — ABS and biological-resource helper

**Required facts:**

- Applicant/user category
- Biological-resource identity
- Indian/foreign source and geographic origin
- Research, access, result transfer, IPR or commercialisation activity
- Associated traditional knowledge
- Claimed exception/exemption

**Responsibilities:**

- Route possible NBA/SBB/BMC relevance
- Identify the activity category
- Return a possible e-form/portal pointer where supported
- Produce missing-document and benefit-sharing checkpoints
- Escalate uncertain ownership, origin, user-status or exemption issues

**Hard rule:** Missing ABS facts cannot be silently treated as “not applicable.”

Evaluate exceptions independently against applicant, activity and source facts. Return source-linked checkpoints and unresolved conditions—not automated compliance certificates.

### B9 — Traditional-knowledge/prior-art service

**Responsibilities:**

- Flag Section 3(p) traditional-knowledge risk
- Create a structured prior-art search query
- Link to public patent and literature searches
- Provide a TKDL pointer without copying restricted content
- Save reviewed search records in the case

Restricted TKDL or paid-source access must be delegated to Module D's permissioned connector system.

### B10 — Regulatory route service

**Subdomains:**

- Classical AYUSH medicine
- Patent/proprietary AYUSH medicine
- New/non-classical drug
- Phytopharmaceutical
- Ayurveda Aahara and separately other food/nutraceutical routes
- Cosmetic
- Labelling and claims
- Advertising
- Manufacturing, testing and evidence pointers

**Output:**

- Competent authority
- Applicable route
- Licence/approval/evidence checklist
- Missing prerequisites
- Relevant forms/registry links
- Official-source retrieval request
- Human-review triggers

### B11 — International and export routing

**Responsibilities:**

- Separate treaty information from national market-access law
- Route PCT, Madrid, Hague and Budapest pathways
- Track treaty status as dated evidence
- Support one export market at a time initially
- Prevent an international treaty from being presented as direct national approval

### B12 — Form, registry and action-plan service

**Responsibilities:**

- Maintain form/portal metadata
- Generate route-specific checklists
- Track action status
- Create deep links to official portals
- Monitor stale/broken links through Module D

Early phases should guide users to official filing systems rather than submitting applications automatically.

### B13 — Human escalation service

**Triggers:**

- High-risk legal/regulatory issue
- Missing critical fact
- Conflicting current authority
- Unsupported country or product route
- Low citation support
- User requests legal advice or a formal opinion
- Restricted source required

**Escalation packet:**

- Product Passport version
- User question and jurisdiction
- Candidate classification and reasons
- Missing facts/conflicts
- Evidence already retrieved
- Specific question for the facilitator
- Consent and sharing scope

## 3. Backend service structure

```text
app/
├── api/                 # FastAPI routers
├── auth/                # identity and permission adapters
├── cases/
├── passports/
├── classification/
├── questions/
├── routing/
├── ip_strategy/
├── abs/
├── traditional_knowledge/
├── regulation/
├── international/
├── checklists/
├── escalations/
├── integrations/        # Module C and D clients
├── models/              # SQLAlchemy
├── schemas/             # Pydantic/shared contracts
└── events/
```

## 4. Main APIs

```text
POST   /api/v1/cases
GET    /api/v1/cases/{case_id}
PATCH  /api/v1/cases/{case_id}
DELETE /api/v1/cases/{case_id}

POST   /api/v1/cases/{case_id}/passport/answers
GET    /api/v1/cases/{case_id}/passport
GET    /api/v1/cases/{case_id}/passport/versions

POST   /api/v1/cases/{case_id}/classify
GET    /api/v1/classifications/{run_id}
POST   /api/v1/cases/{case_id}/clarifications

POST   /api/v1/cases/{case_id}/guidance
GET    /api/v1/answers/{answer_id}
GET    /api/v1/answers/{answer_id}/citations

POST   /api/v1/cases/{case_id}/checklists
PATCH  /api/v1/checklists/{checklist_id}/items/{item_id}
POST   /api/v1/cases/{case_id}/escalations
POST   /api/v1/cases/{case_id}/exports
```

## 5. Database ownership

Module B owns:

- `cases`
- `case_jurisdictions`
- `product_passport_versions`
- `ingredients`
- `case_ingredients`
- `classification_runs`
- `rulesets`
- `clarification_questions`
- `checklists`
- `checklist_items`
- `escalations`
- `exports`

Module C owns knowledge and answer-evidence tables. Module D owns identities, consents, connector permissions and audit storage.

## 6. Integration with Module C

Module B sends a structured guidance request:

```json
{
  "case_id": "uuid",
  "query_kind": "PRODUCT_SPECIFIC",
  "passport_version_id": "uuid",
  "classification_run_id": "uuid",
  "jurisdiction": {"country": "IN", "layer": "NATIONAL"},
  "domains": ["PATENT", "ABS_BIODIVERSITY", "AYUSH_DRUG"],
  "as_of_date": "2026-09-09",
  "questions": [],
  "allowed_access_classes": ["PUBLIC"]
}
```

For `GENERAL_INFORMATION`, Passport/classification IDs may be null. Access classes are server-derived from Module D grants, never trusted from client input.

Module C returns structured sections, claim objects, citations and `EvidenceSupportAssessment`. Module B applies final policy before exposure to A. Never expose draft model tokens.

**Shared contracts, versioned through OpenAPI:**

- `DomainAssessment`: domain, outcome, conditions (`met/not_met/unknown`), facts_used, evidence_refs, missing_facts, conflicts, ruleset_version, review_required.
- `EvidenceSupportAssessment`: status (`SUPPORTED_IN_SCOPE`, `MISSING_FACTS`, `MISSING_EVIDENCE`, `CONFLICTING_SOURCES`, `OUT_OF_SCOPE`, `REVIEW_REQUIRED`), reasons, unresolved_claim_ids. Not a correctness probability.
- `GuidanceEvent`: run_id, sequence, event_type (`progress`, `section_verified`, `answer_complete`, `error`), payload. Each verified section preserves its own evidence status.
- `GuidanceRequest`: query_kind, question, original_language, optional case/Passport/classification IDs, jurisdiction, domains, as_of_date and server-resolved access context.

Retain `ClassificationResult` for regulatory routing, not as a substitute for IP/ABS assessments. Invalidate guidance when the underlying fact/context snapshot changes.

## 7. SIH implementation priority

### Must build

- Case service
- Product Passport service
- Two fully reviewed product journeys; other labels explicitly unsupported until validated
- Clarifying-question templates
- Jurisdiction firewall
- Patent + ABS/TK + AYUSH/FSSAI routing
- Module C guidance integration
- Checklist and escalation response

### Build after vertical slice

- All IP rights
- Detailed form directory
- Facilitator workflow
- One export market
- Organisation collaboration

## 8. Backend tests

- Classification decision-table branches
- Missing and conflicting facts
- Jurisdiction isolation
- Tenant access control
- Passport versioning
- Idempotent guidance requests
- ABS route cannot default to not-applicable
- Restricted connector requires permission
- Unsupported country escalates
- Module C timeout and invalid response
- Export deletion/retention workflow

## 9. Module B definition of done

- [ ] Classification is deterministic and versioned.
- [ ] Each result explains triggering and missing facts.
- [ ] Jurisdiction is mandatory and propagated to all claims.
- [ ] Domain modules return structured retrieval/checklist requests.
- [ ] ABS/TK is part of the central flow.
- [ ] High-risk conditions create escalation packets.
- [ ] APIs are documented through OpenAPI.
- [ ] Module A can generate its client from the API contract.
- [ ] Domain logic has expert-reviewed tests.
- [ ] A failed route never defaults into proprietary AYUSH; unknown facts stay unknown.
- [ ] Regulatory classification cannot automatically establish patentability or ABS clearance.
- [ ] General queries and date/fact-change invalidation have contract tests.

## 10. Updated phases

- **Phase 0:** Expert-reviewed scenario boundaries, source-linked three-valued rules and shared API contracts; seed gold tests before coding routes.
- **Phase 1:** General-information path and two reviewed product journeys, independent assessments and jurisdiction/date context.
- **Phase 2:** Expand reviewed IP/ABS conditions, exception handling, version invalidation and facilitator packets.
- **Phase 3:** Hindi fact-confirmation integration and one country-specific export adapter.
- **Phase 4:** Additional routes/countries only with authority coverage and passing tests.

If expert review is unavailable, explicitly label the rules and outputs unvalidated and restrict scope. Deterministic execution does not make unreviewed legal rules correct.
