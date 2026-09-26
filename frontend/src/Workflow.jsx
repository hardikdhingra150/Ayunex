import { Link } from 'react-router-dom'
import { Sparkles, FlaskConical, ShieldCheck, FileText, LockKeyhole, User, LoaderCircle, ArrowRight } from 'lucide-react'
import { useApp } from './context'

export default function Workflow(){
  const { profile, language } = useApp()
  const hi = language === 'hi'

  const steps = [
    {
      num: '01',
      icon: Sparkles,
      title: hi ? 'प्रश्न या केस से शुरू करें' : 'Start with your question',
      body: hi
        ? 'धारा 3(p) या जैव संसाधनों पर सामान्य प्रश्न पूछें, या किसी उत्पाद के लिए केस बनाएँ।'
        : 'Ask a general IP question about Section 3(p) or biological resources, or register an ASU product case.',
      to: '/ask',
      label: hi ? 'प्रश्न पूछें' : 'Ask question'
    },
    {
      num: '02',
      icon: FlaskConical,
      title: hi ? 'उत्पाद पासपोर्ट तैयार करें' : 'Describe the product',
      body: hi
        ? 'उत्पाद का उपयोग, शास्त्रीय ग्रंथ संदर्भ, घटक और जैव विविधता उत्पत्ति दर्ज करें।'
        : 'Record formulation facts, textbook citations, botanical species, and sourcing origin.',
      to: '/cases/new',
      label: hi ? 'नया केस' : 'Create case'
    },
    {
      num: '03',
      icon: ShieldCheck,
      title: hi ? 'वैधानिक साक्ष्य जांचें' : 'Check statutory evidence',
      body: hi
        ? 'पेटेंट अधिनियम, औषधि नियम और जैव विविधता अधिनियम के सत्यापित संदर्भों से मिलान करें।'
        : 'Review original statutory citations, effective dates, and Section 3(p) traditional knowledge checks.',
      to: '/sources',
      label: hi ? 'स्रोत देखें' : 'Explore sources'
    },
    {
      num: '04',
      icon: FileText,
      title: hi ? 'निर्णय और अगली कार्रवाई' : 'Export & take forward',
      body: hi
        ? 'संरचित केस फ़ाइल डाउनलोड करें और विशेषज्ञ सलाहकारों के साथ समीक्षा की तैयारी करें।'
        : 'Export court-ready compliance records and consult qualified IP facilitators with evidence in hand.',
      to: '/cases',
      label: hi ? 'मेरे केस' : 'My cases'
    }
  ]

  return (
    <section className="panel" aria-labelledby="workflow-title" style={{ margin: '24px 0', border: '1px solid #c7a46440' }}>
      <div className="section-heading">
        <div>
          <div className="eyebrow">{hi ? 'मार्गदर्शिका एवं कार्यप्रणाली' : 'HOW AYUNEX WORKS'}</div>
          <h2 id="workflow-title">{hi ? 'विचार से लेकर साक्ष्य-आधारित निर्णय तक' : 'From an idea to an informed next step'}</h2>
        </div>
        {!profile && (
          <Link className="button primary" to="/login">
            <User size={15} style={{ marginRight: 6 }} />
            {hi ? 'खाता बनाएं' : 'Create your account'}
          </Link>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginTop: 16 }}>
        {steps.map(s => {
          const Icon = s.icon
          return (
            <div key={s.num} style={{ padding: 18, background: '#17140f', border: '1px solid #453724', borderRadius: 10, display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span className="feature-icon" style={{ width: 34, height: 34, background: '#251e14', color: '#d4af37', border: '1px solid #574528' }}>
                  <Icon size={17} />
                </span>
                <span className="card-number" style={{ fontSize: 13, color: '#8c7e68', fontWeight: 600 }}>{s.num}</span>
              </div>
              <h3 style={{ fontSize: 15, margin: '4px 0 6px', color: '#f5efe3' }}>{s.title}</h3>
              <p style={{ fontSize: 13, color: '#a69b84', lineHeight: 1.5, flex: 1, margin: '0 0 12px' }}>{s.body}</p>
              <Link to={s.to} className="text-link" style={{ fontSize: 13, fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                {s.label} <ArrowRight size={14} />
              </Link>
            </div>
          )
        })}
      </div>

      <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid #332a1c', display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#8f836c' }}>
        <ShieldCheck size={14} style={{ color: '#d4af37', flexShrink: 0 }} />
        <span>
          {hi
            ? 'गोपनीयता सूचना: आपके केस डेटाबेस में सुरक्षित संग्रहीत रहते हैं। AI व्याख्या केवल स्पष्ट सहमति पर की जाती है।'
            : 'Privacy note: Your cases are stored privately in the database. Hosted AI synthesis requires explicit user consent.'}
        </span>
      </div>
    </section>
  )
}

export function RequireAccount({ children }) {
  const { connectionStatus, language } = useApp()
  const hi = language === 'hi'

  if (connectionStatus === 'connecting' || connectionStatus === 'checking') {
    return (
      <div className="panel" style={{ margin: '48px auto', maxWidth: 480, textAlign: 'center', padding: 40 }} role="status">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, color: '#d4af37' }}>
          <LoaderCircle className="spin" size={20} />
          <span>{hi ? 'कार्यक्षेत्र खोला जा रहा है…' : 'Opening your workspace…'}</span>
        </div>
      </div>
    )
  }

  if (connectionStatus !== 'connected') {
    return (
      <section className="panel" style={{ maxWidth: 540, margin: '48px auto', padding: 36, textAlign: 'center' }}>
        <div className="feature-icon" style={{ margin: '0 auto 16px', width: 48, height: 48, background: '#251e14', color: '#d4af37', border: '1px solid #574528' }}>
          <LockKeyhole size={22} />
        </div>
        <div className="eyebrow">{hi ? 'सुरक्षित निजी कार्यक्षेत्र' : 'PRIVATE RESEARCH WORKSPACE'}</div>
        <h1 style={{ marginTop: 8, fontSize: 24 }}>{hi ? 'अपने कार्यक्षेत्र में साइन इन करें' : 'Sign in to your workspace'}</h1>
        <p style={{ color: '#a69b84', lineHeight: 1.6, margin: '10px 0 20px' }}>
          {hi
            ? 'आपके उत्पाद केस और अनुसंधान सुरक्षित रूप से आपके निजी खाते में संग्रहीत किए जाते हैं। जारी रखने के लिए साइन इन करें।'
            : 'Your cases and Product Passports are saved securely and privately in the database under your personal account.'}
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
          <Link to="/login" className="button primary" style={{ padding: '10px 24px', fontSize: 14 }}>
            <User size={16} style={{ marginRight: 6 }} />
            {hi ? 'साइन इन / खाता बनाएं' : 'Sign in / Create account'}
          </Link>
        </div>
      </section>
    )
  }

  return children
}

