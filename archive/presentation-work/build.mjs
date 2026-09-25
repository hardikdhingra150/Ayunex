import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const ROOT='/Users/hardik/Desktop/SIH (Moa_26045)';
const SKILL='/Users/hardik/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const source='/Users/hardik/Desktop/26045_SIH_NAUT IQ.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const records=(await fs.readFile(ROOT+'/.ppt_revision/source.ndjson','utf8')).trim().split('\n').map(JSON.parse);
const navy='#234F7B', ink='#202C37', gray='#56636D', pale='#F1F4F7', border='#AAB8C5';
const teal='#117F80',lightBlue='#EEF4FA',lightTeal='#EAF6F3';
function box(s,x,y,w,h,fill=lightBlue,stroke='#CBD9E5',radius=12){
 const a=s.shapes.add({geometry:'roundRect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:1},borderRadius:radius});a.sendToBack();return a;
}
function text(s,t,x,y,w,h,size=23,bold=false,color=ink,align='left'){
 const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=t;a.text.style={typeface:bold?'Arial Bold':'Arial',fontSize:size,bold,color,alignment:align,verticalAlignment:'top',autoFit:'none',insets:{left:0,right:0,top:0,bottom:0}};return a;
}
function node(s,t,x,y,w,h,diamond=false){
 const a=s.shapes.add({geometry:diamond?'diamond':'roundRect',position:{left:x,top:y,width:w,height:h},fill:pale,line:{fill:navy,width:1.5}});
 a.text=diamond?'':t;a.text.style={typeface:'Arial Bold',fontSize:20,bold:true,color:navy,alignment:'center',verticalAlignment:'middle',autoFit:'none',insets:{left:12,right:12,top:5,bottom:5}};
 if(diamond)text(s,t,x+20,y+24,w-40,h-30,18,true,navy,'center');return a;
}
function arrow(s,pts){
 const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);const x=Math.min(...xs),y=Math.min(...ys),w=Math.max(1,Math.max(...xs)-x),h=Math.max(1,Math.max(...ys)-y);
 s.shapes.add({geometry:'custom',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:navy,width:1.6},customPaths:[{width:w,height:h,commands:pts.map((p,i)=>i?{lineTo:{x:p[0]-x,y:p[1]-y}}:{moveTo:{x:p[0]-x,y:p[1]-y}})}]});
 const b=pts.at(-1),a=pts.at(-2),dx=Math.sign(b[0]-a[0]),dy=Math.sign(b[1]-a[1]);
 const tri=[b,[b[0]-dx*8-dy*4,b[1]-dy*8+dx*4],[b[0]-dx*8+dy*4,b[1]-dy*8-dx*4]];
 const tx=Math.min(...tri.map(p=>p[0])),ty=Math.min(...tri.map(p=>p[1]));
 s.shapes.add({geometry:'custom',position:{left:tx,top:ty,width:8,height:8},fill:navy,line:{fill:'none',width:0},customPaths:[{width:8,height:8,commands:[...tri.map((p,i)=>i?{lineTo:{x:p[0]-tx,y:p[1]-ty}}:{moveTo:{x:p[0]-tx,y:p[1]-ty}}),{close:{}}]}]});
}
function connect(s,a,b,from='bottom',to='top'){return s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{fill:navy,width:1.6},head:{type:'triangle',width:'sm',length:'sm'}});}
function notes(s,t){s.speakerNotes.textFrame.setText(t);}
const titles=['','PROBLEM AND SOLUTION','SYSTEM WORKFLOW','TECHNICAL APPROACH','KEY FEATURES AND INNOVATION','FEASIBILITY AND VIABILITY','IMPACT AND BENEFITS','REFERENCES'];
// Keep the imported masters, canvas, cover artwork and SIH/team header artwork.
for(let n=2;n<=8;n++){
 const s=p.slides.items[n-1];
 for(const r of records.filter(r=>r.slide===n&&['textbox','shape'].includes(r.kind))){
  const [x,y,w,h]=r.bbox;
  const keepArtwork=(!r.text&&y<30&&h>65&&h<130)||(n===8&&r.name==='Oval 28');
  if(n===8&&r.name==='Oval 28')p.resolve(r.id).text='';
  if(!keepArtwork)p.resolve(r.id).delete();
 }
 if(n===5){p.resolve('sh/dgbulwnm').delete();p.resolve('sh/z2tcnm5s').delete();}
 // Slide 6 embeds its existing title with the logo in one imported graphic.
 text(s,titles[n-1],205,28,805,65,n===5?38:n===6?40:44,true,ink,'center');
 text(s,'Naut IQ',51,49,115,34,24,true,navy,'center');
}
// Cover: preserve its layout and required fields, correct spacing and identify the solution.
const cover=p.slides.items[0];
for(const r of records.filter(r=>r.slide===1&&r.kind==='textbox'))p.resolve(r.id).delete();
// Create backgrounds before their text so native PowerPoint stacking stays stable.
box(cover,38,121,597,415,lightBlue,'#D3DFEB',18);
box(cover,38,539,597,69,navy,navy,14);
box(p.slides.items[1],40,140,462,418,lightBlue);
box(p.slides.items[1],691,140,550,418,lightTeal,'#BFDCD7');
box(p.slides.items[1],40,591,1201,62,navy,navy);
box(p.slides.items[3],42,214,1193,34,navy,navy,4);
for(let i=0;i<5;i++)box(p.slides.items[3],42,251+i*75,1193,70,i%2?'#FFFFFF':lightBlue,'#D9E2EB',6);
box(p.slides.items[5],40,135,580,442,lightBlue);
box(p.slides.items[5],678,135,558,442,lightTeal,'#BFDCD7');
box(p.slides.items[5],40,608,1196,43,navy,navy,8);
text(cover,'SMART INDIA HACKATHON 2026',105,22,915,65,47,true,navy,'center');
text(cover,'IP-SAKTI SAHAYAK',58,134,580,60,39,true,ink);
text(cover,'Problem Statement ID: 26045',58,214,565,36,27,true);
text(cover,'Multilingual, source-cited AI assistant for\nAyurveda IP and regulatory guidance',58,265,575,94,28);
text(cover,'Theme: MedTech / BioTech / HealthTech',58,386,560,38,25);
text(cover,'Category: Software',58,442,550,34,25);
text(cover,'Team ID: To be assigned',58,498,550,34,25);
text(cover,'Team Name: Naut IQ',58,554,550,40,29,true,navy);
notes(cover,'SIH Problem Statement 26045, Ministry of Ayush / All India Institute of Ayurveda. Official problem title: IP-SAKTI Sahayak, a multilingual, RAG-based (source-cited) AI assistant for Intellectual Property and regulatory guidance in Ayurveda, across national and international regimes. Team ID remains unassigned in the supplied deck.');
// Problem / solution: retain the template’s left-to-right composition with less copy.
{
 const s=p.slides.items[1];
 text(s,'THE PROBLEM',60,160,420,35,25,true,navy);
 text(s,'One Ayurvedic product.\nSeveral legal questions.',60,213,440,75,29,true);
 text(s,'Which product rules apply?\n\nWhich IP rights may be relevant?\n\nWhat biological-resource duties arise?\n\nWhat changes in an export market?',60,315,440,255,23);
 text(s,'OUR SOLUTION',710,160,500,35,25,true,navy);
 text(s,'IP-SAKTI Sahayak',710,210,500,48,34,true);
 text(s,'Ask only the facts the question needs.\n\nAssess regulation, IP and ABS separately.\n\nRetrieve dated provisions. Keep India and\ntarget-country guidance separate.\n\nCheck the evidence before answering.',710,280,500,270,24);
 const pass=node(s,'PRODUCT\nPASSPORT',526,290,150,90);pass.text.fontSize=20;
 text(s,'Product-specific\nquestions only',512,403,180,60,18,false,gray,'center');
 text(s,'General questions can go straight to source-based guidance.',60,606,1150,36,24,true,navy);
 notes(s,'Proposed design. Regulatory classification does not establish patentability or ABS compliance. ABS means Access and Benefit Sharing. Product Passport fact collection is progressive and unnecessary for general information queries. Research rationale: https://arxiv.org/abs/2405.20362 and https://aclanthology.org/2023.emnlp-main.398/');
}
// Editable decision flow, replacing the old category-to-IP shortcut.
{
 const s=p.slides.items[2];
 const q=node(s,'USER QUESTION',500,123,280,43);
 const j=node(s,'Language, jurisdiction and as-of date',420,190,440,50);
 const d=node(s,'Product\nquestion?',544,264,192,90,true);
 const g=node(s,'General information\nNo Passport required',75,282,305,67);
 const f=node(s,'Ask relevant facts\nConfirm key details',902,273,305,72);
 const a=node(s,'Regulatory route, IP and ABS\nSeparate assessments',870,380,345,67);
 const r=node(s,'Retrieve official provisions\nCheck dates and exceptions',420,431,440,68);
 const v=node(s,'Evidence\nsufficient?',520,534,240,92,true);
 const out=node(s,'CITED ACTION PLAN\nSources, next steps and forms',65,551,320,76);
 const no=node(s,'MISSING OR CONFLICTING EVIDENCE\nOne retrieval retry, then partial\nguidance or human review',883,541,342,98);no.text.fontSize=18;
 arrow(s,[[640,166],[640,190]]);arrow(s,[[640,240],[640,264]]);
 arrow(s,[[544,309],[458,309],[458,315],[380,315]]);arrow(s,[[736,309],[820,309],[820,309],[902,309]]);
 arrow(s,[[1054,345],[1054,365],[1042,365],[1042,380]]);
 arrow(s,[[870,413],[865,413],[865,465],[860,465]]);
 arrow(s,[[227,349],[227,465],[420,465]]);arrow(s,[[640,499],[640,534]]);
 arrow(s,[[520,580],[455,580],[455,589],[385,589]]);arrow(s,[[760,580],[820,580],[820,590],[883,590]]);
 text(s,'No',438,293,55,26,17,false,gray,'center');text(s,'Yes',790,293,55,26,17,false,gray,'center');
 text(s,'Yes',424,550,50,25,17,false,gray,'center');text(s,'No',800,550,50,25,17,false,gray,'center');
 text(s,'Unknown facts stay unresolved. A product category never guarantees a patent or ABS clearance.',92,667,1100,28,19,false,gray,'center');
 notes(s,'Proposed workflow. Rules use met/not_met/unknown conditions and reviewed provision references. Missing decisive facts can trigger clarification or partial guidance. Verification includes source IDs, exact passages, jurisdiction, dates, conditions and semantic support. At most one retrieval repair is allowed. General information bypasses product classification. Only verified sections reach the user. https://aclanthology.org/2023.emnlp-main.398/ https://arxiv.org/abs/2310.11511');
}
// Tech stack: actual choices, purpose and candidate status, no conflicting databases.
{
 const s=p.slides.items[3];
 const moduleNodes=[node(s,'A  FRONTEND',60,141,245,54),node(s,'B  DOMAIN LOGIC',360,141,245,54),node(s,'C  AI + EVIDENCE',660,141,245,54),node(s,'D  PLATFORM',960,141,245,54)];
 moduleNodes.forEach((n,i)=>{n.fill=i===2?teal:navy;n.text.color='#FFFFFF';});
 arrow(s,[[305,168],[360,168]]);arrow(s,[[605,168],[660,168]]);
 moduleNodes[3].text='D  PLATFORM\nSupports all modules';moduleNodes[3].text.fontSize=17;
 const rows=[
 ['A  FRONTEND','Next.js, TypeScript, Tailwind\nBHASHINI adapter','Guided questions and evidence views\nHindi text first, voice after validation'],
 ['B  BACKEND','FastAPI, Pydantic\nVersioned decision tables','Typed APIs and confirmed facts\nIndependent regulatory, IP and ABS rules'],
 ['C  RETRIEVAL','PostgreSQL FTS + pgvector\nBGE-M3 embeddings','Exact terms and semantic search\nProvision versions and reviewed aliases'],
 ['C  ANSWERS','Qwen3-8B candidate\nTyped verification workflow','Structured answers with evidence IDs\nReranker and model selection by testing'],
 ['D  PLATFORM','Docker Compose, object storage\nRole-based access, audit logs','One backend and one worker initially\nPrivate cases stay outside the legal corpus']
 ];
 text(s,'MODULE',60,218,220,25,18,true,gray);text(s,'TECHNOLOGY',290,218,420,25,18,true,gray);text(s,'PURPOSE',742,218,478,25,18,true,gray);
 rows.forEach((r,i)=>{const y=260+i*75;text(s,r[0],60,y,220,55,21,true,navy);text(s,r[1],290,y,420,65,22,true);text(s,r[2],742,y,478,65,21);});
 text(s,'Graph database and extra agents follow only if evaluation shows a benefit.',60,660,1160,29,20,false,gray);
 notes(s,'Proposed technology stack, not an implemented or benchmark-proven system. Qwen3-8B retains the supplied deck\'s generator as an evaluation candidate, not a selected production winner. BGE-M3 is a retrieval candidate. PostgreSQL FTS ranking is not BM25. Reranker and generator revisions will be selected and pinned using the project benchmark and available hardware. BHASHINI processing requires approved data handling. https://arxiv.org/abs/2402.03216 https://www.postgresql.org/docs/current/textsearch-controls.html https://github.com/AI4Bharat/IndicTrans2');
}
{
 const s=p.slides.items[4];
 const rows=[
 ['Relevant questions','General queries bypass the Passport. Product guidance asks only\nfor facts that change the assessment.'],
 ['Separate legal assessments','Regulatory category, IP opportunities and ABS duties each have\ntheir own conditions. Unknown facts remain visible.'],
 ['Evidence users can inspect','Each material claim links to the exact provision and source version.\nThe system checks jurisdiction, effective dates and exceptions.'],
 ['A clear path when uncertain','Unsupported sections trigger clarification or human review.\nThe case file preserves facts, sources and unresolved questions.']
 ];
 rows.forEach((r,i)=>{const x=60+(i%2)*610,y=166+Math.floor(i/2)*223;box(s,x,y,560,190,i%2?lightTeal:lightBlue);text(s,`0${i+1}`,x+25,y+20,55,40,28,true,i%2?teal:navy);text(s,r[0],x+94,y+22,440,63,25,true,ink);text(s,r[1].replaceAll('\n',' '),x+25,y+87,510,88,23);});
 text(s,'Information, not legal advice. Expert review remains essential for legal decisions.',65,644,1150,37,22,false,gray);
 notes(s,'Proposed features. Claim verification reduces risk but cannot guarantee correctness. Evidence-support labels are not confidence probabilities. For international requests, treaty frameworks and target-country market access remain distinct. https://arxiv.org/abs/2405.20362 https://aclanthology.org/2023.emnlp-main.398/');
}
{
 const s=p.slides.items[5];
 text(s,'BUILD AND VALIDATE',60,147,550,35,25,true,navy);
 const phases=[['01  Reviewed foundation','Official provisions, decision rules and 30 expert-reviewed cases'],['02  Working demonstrator','Two product journeys, general queries and verified citations'],['03  Tested expansion','About 150 base cases, then Hindi and one export market']];
 phases.forEach((r,i)=>{text(s,r[0],60,208+i*125,550,35,26,true);text(s,r[1],60,254+i*125,515,64,24);});
 text(s,'PRACTICAL CONTROLS',700,147,500,35,25,true,navy);
 const controls=[['Changing law','Curator approval, effective dates and regression tests'],['Incorrect or incomplete answers','Claim checks, one repair attempt and human review'],['Confidential product details','Minimum data collection, scoped access and redacted logs']];
 controls.forEach((r,i)=>{text(s,r[0],700,208+i*125,500,35,26,true);text(s,r[1],700,254+i*125,500,64,24);});
 text(s,'Pilot targets: 95% citation support and 90% required-abstention recall.',60,618,1160,33,24,true,navy);
 text(s,'Targets await testing. Qualified reviewers and permitted source access are prerequisites.',60,661,1160,28,20,false,gray);
 notes(s,'Proposed scope and acceptance targets, not achieved results. Begin with 30 expert-reviewed cases and grow to approximately 150 independent base cases, with separate paired Hindi variants. Assess answer correctness, citation completeness, unnecessary abstention, jurisdiction leakage, latency and cost as well. Any observed critical fabricated authority or wrong-jurisdiction obligation blocks release. Keep unreviewed routes explicitly unsupported. Corpus update example: NBA lists the 2025 ABS Regulations at https://nbaindia.nic.in/public-information/notification-guidelines . Evaluation methodologies: https://arxiv.org/abs/2408.10343 and https://arxiv.org/abs/2603.01710');
}
// Impact: four spacious statements, no metric cards or unsupported performance claims.
{
 const s=p.slides.items[6];
 text(s,'Expected benefits for the Ayurveda community',65,159,1150,42,28,false,gray);
 const impacts=[
 ['Startups and MSMEs','Clearer next steps before spending on filings,\nlicences or export preparation.'],
 ['Practitioners and researchers','Plain-language explanations with official evidence\nthat they can inspect and discuss with experts.'],
 ['Cultivators and TK holders','Earlier visibility of resource-origin questions\nand benefit-sharing checkpoints.'],
 ['IP facilitators','A structured case file with the facts, provisions\nand unresolved issues ready for review.']
 ];
 impacts.forEach((r,i)=>{const x=60+(i%2)*610,y=230+Math.floor(i/2)*205;box(s,x,y,560,178,i%2?lightTeal:lightBlue);const title=text(s,r[0].replace(' and ',' & '),x+25,y+20,510,66,26,true,i%2?teal:navy);text(s,r[1].replaceAll('\n',' '),x+25,y+88,510,80,23);});
 text(s,'The pilot will measure guidance quality, review effort and language accessibility.',65,667,1150,28,20,false,gray);
 notes(s,'These are expected benefits to validate in a pilot, not measured outcomes. Do not interpret guidance as a guarantee of compliance, patent grant, market entry or protection from misappropriation. TK means traditional knowledge. Compare expert review effort and user comprehension alongside correctness and citation quality.');
}
{
 const s=p.slides.items[7];
 const refs=[
 ['India Code and IP India','Patents Act, rules and amendments','https://www.indiacode.nic.in/handle/123456789/1392'],
 ['CDSCO and FSSAI','Product definitions and Ayurveda Aahara','https://www.cdsco.gov.in/opencms/opencms/en/Traditional_Drugs/'],
 ['National Biodiversity Authority','Biodiversity rules and ABS Regulations, 2025','https://nbaindia.nic.in/public-information/notification-guidelines'],
 ['WIPO and TKDL','Treaty status and traditional-knowledge resources','https://www.wipo.int/en/web/treaties/ip/gratk'],
 ['ALCE, Gao et al. (2023)','Answer generation with supporting citations','https://aclanthology.org/2023.emnlp-main.398/'],
 ['LegalBench-RAG (2024)','Precise legal retrieval evaluation','https://arxiv.org/abs/2408.10343'],
 ['BGE-M3 (2024)','Multilingual text embeddings','https://arxiv.org/abs/2402.03216'],
 ['IndicTrans2, Gala et al. (2023)','Translation across Indian languages','https://arxiv.org/abs/2305.16307']
 ];
 refs.forEach((r,i)=>{const col=i<4?0:1,row=i%4,x=65+col*610,y=170+row*119;const t=text(s,r[0],x,y,545,35,24,true,navy);t.text.get(r[0]).link={uri:r[2],isExternal:true};text(s,r[1],x,y+43,545,60,22);});
 notes(s,'Official sources and research references. Additional links: https://www.ipindia.gov.in/ https://fssai.gov.in/upload/notifications/2022/05/62789a20b54bdGazette_Notification_Ayurveda_Aahara_09_05_2022.pdf https://www.tkdl.res.in/ https://bhashini.gov.in/ https://arxiv.org/abs/2202.00216 https://arxiv.org/abs/2405.20362 . Source access and reuse terms require review before ingestion. Research supports individual design choices, not a proven best complete system.');
}
// Colour and content containers follow the requested template and retain editable text.
{
 const snap=(await p.inspect({kind:'textbox,shape',maxChars:250000})).ndjson.trim().split('\n').map(JSON.parse);
 for(const r of snap){
  if(!r.text)continue;const a=p.resolve(r.id);
  if((r.slide===1&&r.text==='Team Name: Naut IQ')||(r.slide===2&&r.text.startsWith('General questions can'))||(r.slide===6&&r.text.startsWith('Pilot targets:')))a.text.color='#FFFFFF';
  if(r.slide===4&&['MODULE','TECHNOLOGY','PURPOSE'].includes(r.text))a.text.color='#FFFFFF';
  if(r.slide===2&&r.text==='PRODUCT\nPASSPORT'){a.fill=navy;a.text.color='#FFFFFF';}
  if(r.slide===3){
   if(r.text==='USER QUESTION'||r.text.startsWith('Retrieve official')){a.fill=navy;a.text.color='#FFFFFF';}
   if(r.text.startsWith('CITED ACTION PLAN')){a.fill=teal;a.line={fill:teal,width:1};a.text.color='#FFFFFF';}
   if(r.text.startsWith('Ask relevant')||r.text.startsWith('Regulatory route,')){a.fill=lightTeal;a.line={fill:teal,width:1.5};a.text.color=teal;}
   if(r.text.startsWith('MISSING OR CONFLICTING')){a.fill='#FFF6E9';a.line={fill:'#B58A43',width:1.5};a.text.color='#75511D';}
  }
 }
}
const candidate=ROOT+'/.ppt_revision/enhanced-candidate.pptx';
await (await PresentationFile.exportPptx(p)).save(candidate);
for(let i=0;i<8;i++)await fs.writeFile(`${ROOT}/.ppt_revision/updated-${i+1}.png`,new Uint8Array(await(await p.slides.items[i].export({format:'png',scale:1})).arrayBuffer()));
await fs.writeFile(ROOT+'/.ppt_revision/updated.ndjson',(await p.inspect({kind:'slide,textbox,shape',maxChars:150000})).ndjson);
console.log('Draft exported');
if(process.argv.includes('--final')){
 const {finalizePresentation}=await import(SKILL+'/container_tools/artifact_tool_utils.mjs');
 const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:ROOT+'/output/26045_SIH_NAUT_IQ_Enhanced.pptx',pythonExecutable:'/Users/hardik/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',integrityValidatorPath:SKILL+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:SKILL+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:8,fontPolicy:{basis:'reference',families:['Arial','Arial Bold'],referencePath:source,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex')},verifyArtifactToolImport:true,receiptPath:ROOT+'/.ppt_revision/enhanced-validation.json'});
 console.log('Finalization complete');
 const finalDeck=await PresentationFile.importPptx(await FileBlob.load(ROOT+'/output/26045_SIH_NAUT_IQ_Enhanced.pptx'));
 for(let i=0;i<8;i++)await fs.writeFile(`${ROOT}/.ppt_revision/final-${i+1}.png`,new Uint8Array(await(await finalDeck.slides.items[i].export({format:'png',scale:1})).arrayBuffer()));
}
