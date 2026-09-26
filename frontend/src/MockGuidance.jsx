import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, BookOpen, ExternalLink, ShieldCheck, AlertTriangle, RefreshCw, XCircle } from 'lucide-react'
import { useApp } from './context'
import Modal from './components/Modal'

function renderClaimText(text) {
  if (!text) return null
  const clean = text
    .replace(/\*{1,3}(.*?)\*{1,3}/g, '$1')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/^[\*\-•]\s+/gm, '')
    .replace(/`+([^`]+)`+/g, '$1')
    .replace(/\*+/g, '')
    .trim()

  const paras = clean.split(/\n\s*\n/).filter(Boolean)
  return (
    <div className="claim-text-container" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {paras.map((p, idx) => {
        const colonMatch = p.match(/^([A-Za-z0-9\s()·.,/-]{3,50}:)\s*(.*)$/s)
        if (colonMatch) {
          return (
            <p key={idx} style={{ margin: 0, fontSize: 14.5, lineHeight: 1.65, color: '#f3ede2' }}>
              <strong style={{ color: '#d4af37', fontWeight: 600 }}>{colonMatch[1]}</strong>{' '}
              {colonMatch[2]}
            </p>
          )
        }
        return (
          <p key={idx} style={{ margin: 0, fontSize: 14.5, lineHeight: 1.65, color: '#f3ede2' }}>
            {p}
          </p>
        )
      })}
    </div>
  )
}

export default function MockGuidance({ item }) {
  const { language, updateCase, backendMode, backendClient, notify } = useApp()
  const hi = language === 'hi'
  const t = (en, hindi) => hi ? hindi : en

  // Live evidence service only.
  const defaultQuestion = `What are the regulatory classification, patentability, and biological resource conditions for ${item.title || 'this formulation'} under Indian law?`
  const [question, setQuestion] = useState(defaultQuestion)
  const [allowHosted, setAllowHosted] = useState(false)
  const [liveAnswer, setLiveAnswer] = useState(null)
  const [liveBusy, setLiveBusy] = useState(false)
  const [liveError, setLiveError] = useState('')

  // Selected citation for modal inspection
  const [selectedCitation, setSelectedCitation] = useState(null)

  const liveController = useRef(null)
  const key = `${item.id}:${item.jurisdiction}:${item.asOf}`

  useEffect(() => () => {
    liveController.current?.abort()
  }, [key])


  // Request cited guidance from the authenticated API.
  async function runLive() {
    if (!backendClient || !item.id) return
    liveController.current?.abort()
    const control = new AbortController()
    liveController.current = control
    setLiveError('')
    setLiveBusy(true)
    const idempotencyKey = `live-guidance-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`

    try {
      if(allowHosted)await backendClient.recordConsent('hosted_ai_processing','hosted-ai-v1')
      const payload = {
        question: question.trim(),
        original_language: 'en',
        allow_hosted_processing: allowHosted
      }

      const res = await backendClient.guidance(item.id,payload,idempotencyKey,control.signal)
      if(control.signal.aborted)return
      const data = res.payload || res
      setLiveAnswer(data)
      updateCase(item.id, {
        status: 'Guidance ready',
        assessment: { support: data.support },
        versions: [
          ...item.versions,
          {
            id: crypto.randomUUID(),
            at: new Date().toISOString(),
            jurisdiction: item.jurisdiction,
            asOf: item.asOf,
            facts: structuredClone(item.facts),
            answer: data,
            live: true,
            mode: data.retrieval_trace?.mode
          }
        ]
      })
      notify(t('AI guidance evaluated successfully', 'AI मार्गदर्शन सफलतापूर्वक प्राप्त हुआ'))
    } catch (err) {
      if (control.signal.aborted) return
      const msg = err.status === 409
        ? (err.message || 'Case or facts changed during guidance. Please review.')
        : (err.message || 'Live guidance request failed.')
      setLiveError(msg)
    } finally {
      setLiveBusy(false)
    }
  }

  function cancelLive() {
    liveController.current?.abort()
    setLiveBusy(false)
    setLiveError(t('Cancelled live guidance request.', 'लाइव मार्गदर्शन अनुरोध रद्द किया गया।'))
  }

  return (
    <div className="mock-guidance">
      {!backendClient&&<Link to="/login" className="button primary">Sign in to request guidance</Link>}
      {backendMode === 'live' && (
        <div className="live-guidance-container">
          <div className="notice" style={{ borderColor: '#d4af37' }}>
            <ShieldCheck size={18} />
            <div>
              <strong>{t('AYUNEX AI · Authoritative Legal Knowledge & AI Guidance', 'AYUNEX AI · प्रामाणिक वैधानिक ज्ञान एवं AI मार्गदर्शन')}</strong>
              <p style={{ margin: '4px 0 0', fontSize: 13 }}>
                {t(
                  'Responses depend on available reviewed evidence. Inspect every citation; missing evidence or provider failures may produce an abstention or source-only response.',
                  'सत्यापित वैधानिक साक्ष्यों (पेटेंट अधिनियम, जैव विविधता अधिनियम) पर आधारित। प्रकाशन से पूर्व स्वचालित समीक्षा प्रत्येक दावे की जांच करती है।'
                )}
              </p>
            </div>
          </div>

          <div className="panel" style={{ marginTop: 16 }}>
            <h3>{t('Case Research Question', 'केस अनुसंधान प्रश्न')}</h3>
            <p style={{ color: '#aaa', fontSize: 13, marginBottom: 10 }}>
              {t('Refine the question submitted to the statutory RAG engine:', 'वैधानिक RAG खोज इंजन में भेजा जाने वाला प्रश्न:')}
            </p>
            <textarea
              rows={3}
              value={question}
              disabled={liveBusy}
              onChange={e => setQuestion(e.target.value)}
              style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: '#1c1b18', color: '#f3ede2', border: '1px solid #333', fontSize: 14 }}
            />

            <label style={{ display: 'flex', gap: 12, alignItems: 'flex-start', margin: '14px 0 18px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={allowHosted}
                disabled={liveBusy}
                onChange={e => setAllowHosted(e.target.checked)}
                style={{ marginTop: 3 }}
              />
              <span style={{ fontSize: 13 }}>
                <strong>{t('Enable AI-grounded synthesis (Groq / Qwen 27B)', 'AI-आधारित व्याख्या सक्षम करें (Groq / Qwen 27B)')}</strong>
                <span style={{ display: 'block', color: '#888', marginTop: 2 }}>
                  {t(
                    'When checked, the question and retrieved public passages are sent to Groq for strict structured synthesis and independent verification. Without this, only exact local statute excerpts are returned.',
                    'चयनित होने पर, प्रश्न और सार्वजनिक स्रोत अंश Groq को भेजे जाते हैं। अन्यथा, केवल स्थानीय वैधानिक अंश दिखाए जाते हैं।'
                  )}
                </span>
              </span>
            </label>

            <div className="form-actions" style={{ marginTop: 10 }}>
              <button
                type="button"
                className="button primary"
                disabled={liveBusy || !question.trim()}
                onClick={runLive}
              >
                {liveBusy ? (
                  <>
                    <RefreshCw size={16} className="spin" />
                    {t('Querying statutory RAG engine…', 'वैधानिक RAG इंजन से खोज जारी…')}
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    {allowHosted ? t('Run Live AI Guidance', 'लाइव AI मार्गदर्शन चलाएँ') : t('Retrieve Verified Excerpts', 'सत्यापित उद्धरण प्राप्त करें')}
                  </>
                )}
              </button>
              {liveBusy && (
                <button type="button" className="button" onClick={cancelLive}>
                  <XCircle size={16} />
                  {t('Cancel', 'रद्द करें')}
                </button>
              )}
            </div>
          </div>

          {liveError && (
            <div className="notice" role="alert" style={{ marginTop: 16, borderColor: '#ff4d4f', color: '#ff7875' }}>
              <AlertTriangle size={18} />
              <span>{liveError}</span>
            </div>
          )}

          {liveAnswer && (
            <div className="panel" style={{ marginTop: 20 }}>
              <div className="section-heading">
                <div>
                  <span className="code-label" style={{ background: '#252119', color: '#d4af37', border: '1px solid #d4af3755' }}>
                    {liveAnswer.retrieval_trace?.mode === 'HOSTED_RAG' ? 'LIVE HOSTED AI RAG' : 'LOCAL EXTRACTIVE'}
                  </span>
                  <h2 style={{ marginTop: 8 }}>{liveAnswer.support?.replaceAll('_', ' ')}</h2>
                  <small style={{ color: '#aaa', display: 'block' }}>
                    {liveAnswer.retrieval_trace?.model || 'Local engine'} · {liveAnswer.as_of_date} · {liveAnswer.jurisdiction?.country || 'India'}
                  </small>
                </div>
                <span className="status">{liveAnswer.support}</span>
              </div>

              {/* Retrieval Trace Metadata */}
              <div className="notice" style={{ fontSize: 12, marginTop: 14 }}>
                <strong>{t('Retrieval Trace:', 'खोज विवरण:')}</strong>{' '}
                <span>
                  Engine: <code>{liveAnswer.retrieval_trace?.engine}</code> · Model: <code>{liveAnswer.retrieval_trace?.model || 'none'}</code> · Verification: <code>{liveAnswer.retrieval_trace?.verification}</code>
                </span>
                <div style={{ marginTop: 4, color: '#888' }}>
                  Pipeline steps: {liveAnswer.retrieval_trace?.steps?.join(' → ')}
                </div>
              </div>

              {/* Sections & Synthesized Claims */}
              {liveAnswer.sections?.map(sec => (
                <div key={sec.id} style={{ marginTop: 20 }}>
                  <h3>{sec.title}</h3>
                  <p style={{ color: '#bbb', fontSize: 14 }}>{sec.reason}</p>

                  <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {sec.claims?.map(claim => (
                      <div key={claim.id} className="panel" style={{ background: '#1c1b18', padding: 14, borderLeft: '3px solid #d4af37' }}>
                        {renderClaimText(claim.text)}
                        <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                          {claim.citation_ids?.map(cid => {
                            const cItem = liveAnswer.citations?.find(c => c.id === cid)
                            return (
                              <button
                                key={cid}
                                type="button"
                                className="button"
                                style={{ fontSize: 12, padding: '3px 8px' }}
                                onClick={() => setSelectedCitation(cItem || { id: cid, provision: cid })}
                              >
                                <BookOpen size={13} />
                                {cItem ? cItem.provision : cid}
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {/* Authoritative Citations List */}
              {liveAnswer.citations?.length > 0 && (
                <div style={{ marginTop: 28 }}>
                  <h3>{t('Authoritative Statutory Evidence', 'प्रामाणिक वैधानिक साक्ष्य')}</h3>
                  <div className="source-grid" style={{ marginTop: 12 }}>
                    {liveAnswer.citations.map(c => (
                      <div key={c.id} className="panel source-card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <span className="tag">{c.review_status}</span>
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
                        <button
                          type="button"
                          className="button"
                          style={{ fontSize: 12, marginTop: 8 }}
                          onClick={() => setSelectedCitation(c)}
                        >
                          {t('Inspect Metadata', 'मेटाडेटा देखें')}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Citation Inspector Modal */}
      {selectedCitation && (
        <Modal
          title={selectedCitation.provision || t('Authoritative statutory citation', 'प्रामाणिक वैधानिक संदर्भ')}
          onClose={() => setSelectedCitation(null)}
        >
          {selectedCitation.excerpt && (
            <blockquote>{selectedCitation.excerpt}</blockquote>
          )}
          <div className="fact-grid">
            {Object.entries(selectedCitation)
              .filter(([k]) => k !== 'excerpt')
              .map(([k, v]) => (
                <div key={k}>
                  <small>{k.replaceAll('_', ' ')}</small>
                  <span>{typeof v === 'object' ? JSON.stringify(v) : (v || t('Unknown / not provided', 'अज्ञात / अनुपलब्ध'))}</span>
                </div>
              ))}
          </div>
          {selectedCitation.url && (
            <div style={{ marginTop: 16 }}>
              <a href={selectedCitation.url} target="_blank" rel="noopener noreferrer" className="button primary">
                <ExternalLink size={15} />
                {t('Open Official Gazette / Publication', 'आधिकारिक राजपत्र / प्रकाशन खोलें')}
              </a>
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}
