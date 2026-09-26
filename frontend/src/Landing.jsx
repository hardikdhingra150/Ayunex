import Localized from './Localized'
import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, ArrowRight, ArrowDown, Orbit, Fingerprint, Globe2, ShieldCheck, BookOpen, FlaskConical, Check, Menu, X, Plus, Languages, FileText, ScanLine } from 'lucide-react'
import { useApp } from './context'
import './Landing.css'
const KnowledgeGlobe = lazy(() => import('./components/KnowledgeGlobe'))

const journeys = [
  { name: 'Describe', label: 'Your idea, in context.', text: 'Start with intended use, ingredients and origin. The Product Passport keeps decisive facts together—and leaves unknowns visible.', icon: FileText, fields: ['Intended use', 'Ingredient origin', 'Formula reference'], action: 'Build your Passport', link: '/cases/new' },
  { name: 'Separate', label: 'Three questions. Not one verdict.', text: 'Regulatory category, intellectual-property opportunities and biodiversity duties are distinct assessments. A medicine category is not a patentability decision.', icon: ScanLine, fields: ['Regulatory route', 'IP opportunities', 'ABS checkpoints'], action: 'Explore a sample case', link: '/cases/ni-001/classification' },
  { name: 'Inspect', label: 'Follow the evidence.', text: 'Know which authority, jurisdiction and source version an answer depends on. The demo offers official starting points; verified retrieval comes with the backend.', icon: BookOpen, fields: ['Official authority', 'Exact provision', 'Effective date'], action: 'Explore official sources', link: '/sources' },
  { name: 'Take forward', label: 'A clearer next conversation.', text: 'Export your product facts and unresolved questions. Prepare a facilitator packet with explicit consent, then decide what to share.', icon: ArrowUpRight, fields: ['Case summary', 'Open questions', 'Consent scope'], action: 'Open your case desk', link: '/cases' },
]

function Reveal({ children, className = '' }) {
  const ref = useRef(null)
  useEffect(() => {
    const element = ref.current
    if (!('IntersectionObserver' in window)) return
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => { if (entry.isIntersecting) { element.classList.add('is-revealed'); observer.unobserve(element) } })
    }, { threshold: 0.08 })
    element.classList.add('will-reveal')
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  return <Localized><div ref={ref} className={`lp-reveal ${className}`}>{children}</div></Localized>
}

export default function Landing() {
  const { motion, language, setLanguage } = useApp()
  const [menu, setMenu] = useState(false)
  const [step, setStep] = useState(0)
  const [layer, setLayer] = useState('IN')
  const active = journeys[step]
  const ActiveIcon = active.icon
  return <Localized><div className={`landing ${motion ? '' : 'lp-still'}`}>
    <a className="skip-link" href="#landing-main">Skip to content</a>
    <header className="lp-nav">
      <Link className="lp-logo" to="/" aria-label="AYUNEX home"><span><img src="/ayunex-mark.svg" alt="" width="43" height="43" /></span><div>AYUNEX<small>AYURVEDA · IP</small></div></Link>
      <nav className={menu ? 'lp-links open' : 'lp-links'} aria-label="Main navigation">
        <a href="#approach" onClick={() => setMenu(false)}>The approach</a>
        <a href="#workflow" onClick={() => setMenu(false)}>How it works</a>
        <a href="#evidence" onClick={() => setMenu(false)}>Evidence first</a>
      </nav>
      <div className="lp-nav-right"><button className="lp-language" aria-label={language==='en'?'Switch to Hindi':'Switch to English'} onClick={()=>setLanguage(language==='en'?'hi':'en')}><Languages size={16} aria-hidden="true"/><span lang={language==='en'?'hi':'en'}>{language==='en'?'हिन्दी':'English'}</span></button><Link className="lp-nav-cta" to="/workspace" aria-label="Open workspace"><span>Open workspace</span><ArrowUpRight size={17} /></Link><button className="lp-menu" aria-label="Toggle navigation" aria-expanded={menu} onClick={() => setMenu(!menu)}>{menu ? <X /> : <Menu />}</button></div>
    </header>

    <main id="landing-main">
      <section className="lp-hero">
        <div className="lp-hero-grid lp-container">
          <div className="lp-hero-copy">
            <div className="lp-eyebrow"><span className="lp-status-dot" /> AYURVEDA. INTELLECTUAL PROPERTY. POSSIBILITY.</div>
            <h1>Ancient roots.<br />Original ideas.<br /><em>A clearer path.</em></h1>
            <p>Explore product rules, IP and biodiversity duties—with your evidence in view.</p>
            <div className="lp-actions"><Link className="lp-button primary" to="/cases/new">Explore your idea <ArrowUpRight size={20} /></Link><a className="lp-button ghost" href="#workflow">See how it works <ArrowDown size={18} /></a></div>
            <div className="lp-hero-note"><ShieldCheck size={17} /><span>Built for evidence. Designed for human judgment.</span></div>
          </div>
          <div className="lp-hero-art">
            <div className="lp-art-halo" />
            <div className="lp-art-main"><Suspense fallback={<div className="globe-fallback" />}><KnowledgeGlobe animate={motion} /></Suspense></div>
            <div className="lp-art-caption"><span>TRADITION → INNOVATION</span><small>Knowledge worth protecting.</small></div>
            <div className="lp-floating lp-floating-one"><span className="lp-float-icon"><Fingerprint size={21} /></span><div><small>INTELLECTUAL PROPERTY</small><strong>Originality, with context.</strong></div><ArrowUpRight size={15} /></div>
            <div className="lp-floating lp-floating-two"><span className="lp-float-icon gold"><Orbit size={20} /></span><div><small>TRADITIONAL KNOWLEDGE</small><strong>Roots that remain visible.</strong></div></div>
            <span className="lp-coordinate">01 / THE KNOWLEDGE CONTINUUM</span>
          </div>
 </div>
        <div className="lp-hero-bottom lp-container"><span>FOR THE PEOPLE TAKING AYURVEDA FORWARD</span><div>Researchers <i /> AYUSH startups <i /> Practitioners <i /> MSMEs</div><a href="#approach" aria-label="Discover our approach"><ArrowDown size={18} /></a></div>
      </section>

      <div className="lp-source-band"><div className="lp-container"><span>OFFICIAL SOURCES<br /><small>Research starting points, not endorsements</small></span><a href="https://www.indiacode.nic.in/" target="_blank" rel="noreferrer">India Code <ArrowUpRight size={14} /></a><a href="https://ipindia.gov.in/" target="_blank" rel="noreferrer">IP India <ArrowUpRight size={14} /></a><a href="https://nbaindia.org/" target="_blank" rel="noreferrer">NBA <ArrowUpRight size={14} /></a><a href="https://www.wipo.int/" target="_blank" rel="noreferrer">WIPO <ArrowUpRight size={14} /></a><Link to="/sources">All sources <ArrowRight size={16} /></Link></div></div>

      <section className="lp-section lp-container" id="approach">
        <Reveal className="lp-section-intro"><div><div className="lp-eyebrow">01 / A CONNECTED PERSPECTIVE</div><h2>One innovation.<br /><em>More than one question.</em></h2></div><p>Three perspectives. One informed next step.</p></Reveal>
        <div className="lp-bento">
          <Reveal className="lp-feature lp-feature-wide"><span className="lp-card-index">01 — PRODUCT PASSPORT</span><div className="lp-feature-icon"><FlaskConical size={30} /></div><h3>Start with what<br />you’re actually making.</h3><p>Record your ingredients, intended use and origin in one guided Passport.</p><Link className="lp-inline" to="/cases/new">Create a Product Passport <ArrowUpRight size={18} /></Link></Reveal>
          <Reveal className="lp-feature"><div className="lp-card-top"><span className="lp-card-index">02 — INDEPENDENT ASSESSMENTS</span><Fingerprint size={28} /></div><h3>Protect the idea.<br />Respect its origins.</h3><p>Keep IP opportunities, product rules and biodiversity duties distinct.</p><div className="lp-pill-row"><span>Patents & other rights</span><span>Biological resources</span><span>Traditional knowledge</span></div><Link className="lp-inline" to="/ask">Explore a question <ArrowUpRight size={18} /></Link></Reveal>
          <Reveal className="lp-feature lp-jurisdiction"><div className="lp-card-top"><span className="lp-card-index">03 — JURISDICTION MATTERS</span><Globe2 size={28} /></div><h3>A global outlook.<br />A specific context.</h3><div className="lp-segment" role="group" aria-label="Preview jurisdiction context"><button aria-pressed={layer === 'IN'} className={layer === 'IN' ? 'selected' : ''} onClick={() => setLayer('IN')}>India</button><button aria-pressed={layer === 'INT'} className={layer === 'INT' ? 'selected' : ''} onClick={() => setLayer('INT')}>International</button></div><p aria-live="polite">{layer === 'IN' ? 'Keep Indian product, IP and biodiversity questions within the Indian legal context.' : 'Choose a treaty framework or target market. International guidance is not a substitute for Indian obligations.'}</p><span className="lp-context-note"><Check size={15} /> Separate context. No blended conclusions.</span></Reveal>
        </div>
      </section>

      <section className="lp-workflow-wrap" id="workflow"><div className="lp-container lp-section">
        <Reveal className="lp-section-intro"><div><div className="lp-eyebrow">02 / FROM QUESTION TO NEXT STEP</div><h2>Less guesswork.<br /><em>More forward motion.</em></h2></div><p>From product facts to a review-ready case.</p></Reveal>
        <div className="lp-step-nav" role="tablist" aria-label="Product journey">{journeys.map((j, i) => <button key={j.name} role="tab" id={`journey-tab-${i}`} aria-selected={step === i} tabIndex={step === i ? 0 : -1} onKeyDown={event => { const keys = { ArrowRight: (i + 1) % 4, ArrowLeft: (i + 3) % 4, Home: 0, End: 3 }; if (event.key in keys) { event.preventDefault(); const next = keys[event.key]; setStep(next); document.getElementById(`journey-tab-${next}`)?.focus() } }} aria-controls="journey-panel" className={step === i ? 'active' : ''} onClick={() => setStep(i)}><span>0{i + 1}</span>{j.name}<ArrowRight size={18} /></button>)}</div>
        <div className="lp-journey" id="journey-panel" role="tabpanel" aria-labelledby={`journey-tab-${step}`}>
          <div className="lp-journey-copy" key={step}><span className="lp-feature-icon"><ActiveIcon size={28} /></span><h3>{active.label}</h3><p>{active.text}</p><Link className="lp-inline" to={active.link}>{active.action}<ArrowUpRight size={18} /></Link></div>
          <div className="lp-diagram" aria-label={`${active.name}: ${active.fields.join(', ')}`}><div className="lp-diagram-root"><Orbit size={22} /> Product Passport <span>YOUR FACTS</span></div><div className="lp-diagram-stem" /><div className="lp-diagram-branches">{active.fields.map((field, i) => <div className="lp-diagram-node" key={field}><span>0{i + 1}</span>{field}</div>)}</div><div className="lp-diagram-output"><ShieldCheck size={17} /> Evidence + human review <span>before a conclusion</span></div></div>
        </div>
      </div></section>

      <section className="lp-section lp-container lp-evidence" id="evidence">
        <Reveal className="lp-evidence-copy"><div className="lp-eyebrow">03 / TRUST IS TRACEABLE</div><h2>Clarity you<br /><em>can check.</em></h2><p>Check the authority, provision and date behind each answer. Verified retrieval is coming with the backend.</p><ul><li><Check size={18} /> Official sources, not invented authority</li><li><Check size={18} /> Visible uncertainty and missing facts</li><li><Check size={18} /> A path to a qualified human facilitator</li></ul><Link className="lp-button ghost" to="/sources">Explore the source library <ArrowUpRight size={18} /></Link></Reveal>
        <Reveal className="lp-evidence-visual"><div className="lp-evidence-card"><div className="lp-evidence-top"><BookOpen size={22} /><span>SOURCE INSPECTOR</span><span className="lp-outline-badge">DIRECTORY PREVIEW</span></div><h3>The authority.<br />Not just the answer.</h3><div className="lp-record"><small>OFFICIAL STARTING POINT</small><strong>India Code</strong><span>Legislation published by the Government of India</span></div><dl><div><dt>Jurisdiction</dt><dd>India</dd></div><div><dt>Provision / version</dt><dd>Not yet retrieved</dd></div><div><dt>Evidence status</dt><dd><span className="lp-amber-dot" /> Awaiting verified retrieval</dd></div></dl><a href="https://www.indiacode.nic.in/" target="_blank" rel="noreferrer" className="lp-inline">Visit official source <ArrowUpRight size={17} /></a></div><div className="lp-evidence-tag"><ShieldCheck size={20} /><span>No evidence?<strong>No invented certainty.</strong></span></div></Reveal>
      </section>

      <section className="lp-container lp-faq"><div><div className="lp-eyebrow">A LITTLE MORE CLARITY</div><h2>Before you begin.</h2></div><div>{[
        ['Is this legal advice?', 'No. AYUNEX is designed to support research and preparation, not replace a qualified legal professional or regulatory authority.'],
        ['What can I use right now?', 'AYUNEX provides complete Product Passport creation, statutory classification, live legal knowledge retrieval (Indian Patents Act, Drugs Rules, Biological Diversity Act), Groq Qwen 27B AI synthesis, and exportable legal dossiers with permanent database persistence.'],
        ['How is my formulation data protected?', 'User accounts and cases are stored in encrypted databases with salted PBKDF2 password hashing. Case data and Product Passports remain strictly private under your tenant isolation. External AI processing is optional and requires explicit DPDP consent.'],
        ['Which languages are available?', 'The workspace includes full English and Hindi interfaces with bilingual navigation, field labels, voice input, and translated statutory citations.'],
      ].map(([q, a]) => <details key={q}><summary>{q}<Plus size={19} /></summary><p>{a}</p></details>)}</div></section>

      <section className="lp-container"><Reveal className="lp-final"><span className="lp-eyebrow">YOUR NEXT IDEA DESERVES A CLEAR START</span><h2>Your next step starts here.</h2><Link className="lp-button primary" to="/workspace">Step inside the workspace <ArrowUpRight size={21} /></Link><p>Create your private account to save cases and run live statutory assessments.</p></Reveal></section>
    </main>
    <footer className="lp-footer lp-container"><div><Link className="lp-logo" to="/"><span><img src="/ayunex-mark.svg" alt="" width="43" height="43" /></span><div>AYUNEX<small>AYURVEDA · IP</small></div></Link><p>Ayurveda innovation, with a clearer direction.</p></div><div><Link to="/privacy">Privacy & scope</Link><Link to="/about">About the project</Link><a href="#landing-main">Back to top ↑</a></div><div><strong>CRAFTED BY AYUNEX</strong><span>SIH 26045 · Production Release</span><small>Information, not legal advice.</small></div></footer>

  </div></Localized>
}
