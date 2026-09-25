import { useRef, useState, useEffect } from 'react'
import { Key, Sparkles, BookOpen, ShieldCheck, AlertCircle, ExternalLink, RefreshCw } from 'lucide-react'
import { createBackendClient } from './backendClient'
import { useApp } from './context'

const DEV_TOKEN = '-o7JRlGIO4I9t4q2xvreNNSiDL_3uyTZ9b-95rp9WXo'
const example = 'What does Section 3(p) of the Indian Patents Act say about traditional knowledge?'

export default function LiveQuestion() {
  const { language, backendToken, backendClient } = useApp()
  const hi = language === 'hi'
  const t = (en, hindi) => hi ? hindi : en

  const [customToken, setCustomToken] = useState('')
  const token = customToken || backendToken || ''
  const [question, setQuestion] = useState(example)
  const [consent, setConsent] = useState(true)
  const [busy, setBusy] = useState(false)
  const [answer, setAnswer] = useState(null)
  const [error, setError] = useState('')

  const pending = useRef(null)

  useEffect(() => () => pending.current?.abort(), [])

  async function submit(e) {
    e.preventDefault()
    setError('')
    setAnswer(null)
    setBusy(true)
    const controller = new AbortController()
    pending.current = controller

    try {
      const activeClient = backendClient || createBackendClient({ getToken: () => token.trim(), timeoutMs: 140000 })
      const result = await activeClient.ask({
        question: question.trim(),
        original_language: 'en',
        allow_hosted_processing: consent,
        jurisdiction: { layer: 'NATIONAL', country: 'IN' },
        as_of_date: new Date().toLocaleDateString('en-CA')
      }, controller.signal)
      if (!controller.signal.aborted) setAnswer(result)
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err.status === 401
          ? t('Local token rejected. Copy backend/.dev-token, not your Groq key.', 'स्थानीय टोकन अस्वीकृत। backend/.dev-token कॉपी करें।')
          : err.message === 'Failed to fetch'
          ? t('Backend unavailable. Start npm run backend on port 8000.', 'बैकएंड अनुपलब्ध है। कृपया पोर्ट 8000 पर बैकएंड शुरू करें।')
          : err.message)
      }
    } finally {
      if (pending.current === controller) {
        pending.current = null
        setBusy(false)
      }
    }
  }

  return (
    <div className="page-enter">
      <div className="page-heading">
        <div>
          <div className="eyebrow">{t('LIVE BACKEND · INDIA PILOT', 'लाइव बैकएंड · भारत पायलट')}</div>
          <h1>{t('Ask. Check the source.', 'पूछें। प्रामाणिक स्रोत जांचें।')}</h1>
          <p>{t('Real backend responses with authoritative statutory evidence alongside the explanation.', 'व्याख्या के साथ मूल वैधानिक साक्ष्य प्रस्तुत करने वाला वास्तविक बैकएंड उत्तर।')}</p>
        </div>
      </div>

      <div className="notice" style={{ borderColor: '#d4af37' }}>
        <ShieldCheck size={18} />
        <div>
          <strong>{t('Curated Seed Knowledge Base', 'सत्यापित प्रारंभिक ज्ञान आधार')}</strong>
          <p style={{ margin: '4px 0 0', fontSize: 13 }}>
            {t(
              'Active approved provisions: Patents Act Section 3(p) (traditional knowledge), Section 3(e) (mere admixture), Section 3(d) (known substance efficacy), and Biological Diversity ABS Regulations 2025 Regulation 5 (commercial access intimation). Information only, not legal advice.',
              'सक्रिय अनुमोदित धाराएँ: पेटेंट अधिनियम धारा 3(p) (पारंपरिक ज्ञान), धारा 3(e) (घटकों का सम्मिश्रण), धारा 3(d) (प्रभावकारिता), एवं राष्ट्रीय जैव विविधता प्राधिकरण नियम 5। केवल सूचना हेतु, कानूनी सलाह नहीं।'
            )}
          </p>
        </div>
      </div>

      <form className="panel" onSubmit={submit} style={{ marginTop: 18 }}>
        <div className="field">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <label htmlFor="local-token" style={{ margin: 0 }}>
              {t('Local development token', 'स्थानीय डेवलपर टोकन')}
            </label>
            <button
              type="button"
              className="button"
              style={{ fontSize: 12, padding: '2px 8px' }}
              onClick={() => setCustomToken(DEV_TOKEN)}
            >
              <Key size={13} />
              {t('Fill dev token', 'डेव टोकन भरें')}
            </button>
          </div>
          <input
            id="local-token"
            type="password"
            autoComplete="off"
            required
            disabled={busy}
            value={customToken || token}
            onChange={e => setCustomToken(e.target.value)}
            placeholder="Paste contents of backend/.dev-token"
          />
          <small>{t('Kept in browser memory only. Your Groq API key stays securely on the server.', 'केवल ब्राउज़र मेमोरी में रहता है। आपकी Groq API कुंजी सर्वर पर सुरक्षित रहती है।')}</small>
        </div>

        <div className="field">
          <label htmlFor="live-question">{t('Your question', 'आपका प्रश्न')}</label>
          <textarea
            id="live-question"
            required
            rows={3}
            minLength={3}
            maxLength={4000}
            disabled={busy}
            value={question}
            onChange={e => {
              setQuestion(e.target.value)
              setAnswer(null)
            }}
          />
        </div>

        <label style={{ display: 'flex', gap: 12, alignItems: 'flex-start', margin: '16px 0 20px', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={consent}
            disabled={busy}
            onChange={e => setConsent(e.target.checked)}
            style={{ marginTop: 3 }}
          />
          <span style={{ fontSize: 13 }}>
            <strong>{t('Allow question and source excerpts to be sent to AI provider (Groq / Qwen 27B)', 'प्रश्न और स्रोत अंशों को AI प्रदाता (Groq / Qwen 27B) को भेजने की अनुमति दें')}</strong>
            <span style={{ display: 'block', color: '#888', marginTop: 2 }}>
              {t(
                'Do not include confidential formulations. Without consent, only exact local source excerpts are returned.',
                'गोपनीय विवरण शामिल न करें। सहमति के बिना केवल स्थानीय वैधानिक स्रोत अंश लौटाए जाते हैं।'
              )}
            </span>
          </span>
        </label>

        <div style={{ display: 'flex', gap: 12 }}>
          <button
            className="button primary"
            disabled={busy || !token.trim() || question.trim().length < 3}
          >
            {busy ? (
              <>
                <RefreshCw size={15} className="spin" />
                {t('Checking evidence and preparing response…', 'साक्ष्य की जांच और उत्तर तैयार किया जा रहा है…')}
              </>
            ) : (
              <>
                <Sparkles size={15} />
                {consent ? t('Ask with AI', 'AI के साथ पूछें') : t('Read source excerpts', 'केवल स्रोत अंश पढ़ें')}
              </>
            )}
          </button>
          {busy && (
            <button
              type="button"
              className="button"
              onClick={() => {
                pending.current?.abort()
                setBusy(false)
              }}
            >
              {t('Cancel', 'रद्द करें')}
            </button>
          )}
        </div>
      </form>

      {error && (
        <div role="alert" className="notice" style={{ marginTop: 20, borderColor: '#ff4d4f', color: '#ff7875' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div aria-live="polite">
        {answer && (
          <section className="panel" style={{ marginTop: 24 }}>
            <div className="section-heading">
              <div>
                <span className="code-label" style={{ background: '#252119', color: '#d4af37', border: '1px solid #d4af3755' }}>
                  {answer.retrieval_trace?.mode === 'HOSTED_RAG' ? 'LIVE AI EXPLANATION' : 'LOCAL SOURCE RESPONSE'}
                </span>
                <h2 style={{ marginTop: 8 }}>{answer.support.replaceAll('_', ' ')}</h2>
                <small style={{ color: '#aaa', display: 'block' }}>
                  {answer.retrieval_trace?.model || 'No AI model called'} · {answer.as_of_date} · India
                </small>
              </div>
              <span className="status">{answer.support}</span>
            </div>

            {/* Retrieval Trace Metadata */}
            <div className="notice" style={{ fontSize: 12, marginTop: 14 }}>
              <strong>{t('Retrieval Trace:', 'खोज विवरण:')}</strong>{' '}
              <span>
                Engine: <code>{answer.retrieval_trace?.engine}</code> · Model: <code>{answer.retrieval_trace?.model || 'none'}</code> · Verification: <code>{answer.retrieval_trace?.verification}</code>
              </span>
              <div style={{ marginTop: 4, color: '#888' }}>
                Pipeline steps: {answer.retrieval_trace?.steps?.join(' → ')}
              </div>
            </div>

            {/* Sections & Claims */}
            {answer.sections?.map(section => (
              <div key={section.id} style={{ marginTop: 20 }}>
                <p style={{ color: '#bbb', fontSize: 14 }}>{section.reason}</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
                  {section.claims?.map(claim => (
                    <article key={claim.id} className="panel" style={{ background: '#1c1b18', padding: 14, borderLeft: '3px solid #d4af37' }}>
                      <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>{claim.text}</p>
                      <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {claim.citation_ids?.map(id => (
                          <a
                            key={id}
                            href={'#source-' + id}
                            className="button"
                            style={{ fontSize: 12, padding: '3px 8px' }}
                          >
                            <BookOpen size={13} />
                            {t('View supporting source ↗', 'सहायक स्रोत देखें ↗')} [{id.slice(0, 14)}]
                          </a>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ))}

            {/* Citations List */}
            {answer.citations?.length > 0 && (
              <div style={{ marginTop: 28 }}>
                <h3>{t('Check the original evidence', 'मूल साक्ष्य की समीक्षा करें')}</h3>
                <div className="source-grid" style={{ marginTop: 12 }}>
                  {answer.citations.map(c => (
                    <div key={c.id} id={'source-' + c.id} className="panel source-card">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <span className="tag">{c.review_status?.replaceAll('_', ' ')}</span>
                        {c.url && (
                          <a href={c.url} target="_blank" rel="noopener noreferrer" style={{ color: '#d4af37' }}>
                            <ExternalLink size={15} />
                          </a>
                        )}
                      </div>
                      <h4 style={{ margin: '8px 0 4px', fontSize: 15 }}>{c.provision}</h4>
                      <p style={{ fontSize: 12, color: '#aaa', margin: 0 }}>{c.title}</p>
                      <blockquote style={{ margin: '10px 0', fontSize: 13, background: '#141414', padding: '8px 10px', borderRadius: 6, fontStyle: 'normal', color: '#e0ded8', whiteSpace: 'pre-wrap' }}>
                        {c.excerpt}
                      </blockquote>
                      <small style={{ color: '#888' }}>Source version: {c.version?.slice(0, 16)}…</small>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  )
}
