import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, BookOpen, ExternalLink, ShieldCheck, AlertTriangle, RefreshCw, XCircle } from 'lucide-react'
import { useApp } from './context'
import { acceptEvent, contextKey, guidanceEvents, scenarios, sectionTitles } from './mockApi'
import { factsToBackendPassport } from './domain'
import Modal from './components/Modal'

export default function MockGuidance({ item }) {
  const { language, updateCase, backendMode, backendClient, notify } = useApp()
  const hi = language === 'hi'
  const t = (en, hindi) => hi ? hindi : en

  // Mode tab: 'live' or 'mock'
  const [activeTab, setActiveTab] = useState(() => (backendMode === 'live' && backendClient) ? 'live' : 'mock')

  // --- Mock state ---
  const [scenario, setScenario] = useState(item.mockAnswer?.scenario || 'ready')
  const [mockAnswer, setMockAnswer] = useState(() => item.mockAnswer?.contextKey === contextKey(item) ? item.mockAnswer : { sections: [], sources: [] })
  const [mockBusy, setMockBusy] = useState(false)
  const [mockError, setMockError] = useState('')

  // --- Live state ---
  const defaultQuestion = `What are the regulatory classification, patentability, and biological resource conditions for ${item.title || 'this formulation'} under Indian law?`
  const [question, setQuestion] = useState(defaultQuestion)
  const [allowHosted, setAllowHosted] = useState(false)
  const [liveAnswer, setLiveAnswer] = useState(null)
  const [liveBusy, setLiveBusy] = useState(false)
  const [liveError, setLiveError] = useState('')

  // Selected citation for modal inspection
  const [selectedCitation, setSelectedCitation] = useState(null)

  const mockController = useRef(null)
  const liveController = useRef(null)
  const requestId = useRef(0)
  const key = contextKey(item)

  useEffect(() => () => {
    requestId.current++
    mockController.current?.abort()
    liveController.current?.abort()
  }, [key])


  // --- Mock runner ---
  async function runMock() {
    mockController.current?.abort()
    const id = ++requestId.current
    const control = new AbortController()
    mockController.current = control
    setMockAnswer({ sections: [], sources: [] })
    setMockError('')
    setMockBusy(true)

    try {
      for await (const event of guidanceEvents(item, { scenario, signal: control.signal })) {
        if (requestId.current !== id) return
        setMockAnswer(old => acceptEvent(old, event, key))
        if (event.type === 'answer_complete') {
          updateCase(item.id, {
            assessment: { support: event.answer.support },
            mockAnswer: event.answer,
            status: 'Guidance ready',
            versions: [
              ...item.versions,
              {
                id: crypto.randomUUID(),
                at: new Date().toISOString(),
                jurisdiction: item.jurisdiction,
                asOf: item.asOf,
                facts: structuredClone(item.facts),
                answer: event.answer,
                mock: true
              }
            ]
          })
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        setMockError(t('Mock request timed out. Retry or choose another scenario.', 'कृत्रिम अनुरोध का समय समाप्त हुआ। पुनः प्रयास करें।'))
      }
    } finally {
      if (requestId.current === id) setMockBusy(false)
    }
  }

  function cancelMock() {
    requestId.current++
    mockController.current?.abort()
    setMockBusy(false)
    setMockAnswer({ sections: [], sources: [] })
    setMockError(t('Cancelled. No partial answer retained.', 'रद्द किया गया। अधूरा उत्तर हटाया गया।'))
  }

  // --- Live runner ---
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

      let res
      let targetId = item.id

      // 1. If this is an in-memory sample case or not yet on server, create it on backend first
      if (item.sample || !item.live) {
        try {
          const jur = item.jurisdiction === 'IN' ? { layer: 'NATIONAL', country: 'IN', framework: null }
            : item.jurisdiction === 'TREATY' ? { layer: 'TREATY_FRAMEWORK', country: null, framework: 'PCT' }
            : { layer: 'EXPORT_MARKET', country: item.jurisdiction || 'IN', framework: null }
          const created = await backendClient.createCase({
            title: item.title || item.facts?.name || 'Ayurvedic Formulation',
            query_kind: 'PRODUCT_SPECIFIC',
            jurisdiction: jur,
            as_of_date: item.asOf || new Date().toISOString().slice(0, 10),
            consent: { accepted: true, notice_version: 'case-notice-v1' }
          })
          targetId = created.id
          if (item.facts) {
            const passportPayload = factsToBackendPassport(item.facts, item.facts.ingredientRows || [])
            await backendClient.savePassport(targetId, passportPayload, 1).catch(() => {})
          }
          updateCase(item.id, { liveId: created.id, live: true })
        } catch {
          // If creation fails, proceed to try guidance
        }
      }

      // 2. Request guidance with automatic fallback to direct statutory endpoint if 404
      try {
        res = await backendClient.guidance(targetId, payload, idempotencyKey, control.signal)
      } catch (gErr) {
        if (gErr.status === 404) {
          const jur = item.jurisdiction === 'IN' ? { layer: 'NATIONAL', country: 'IN', framework: null }
            : { layer: 'EXPORT_MARKET', country: item.jurisdiction || 'IN', framework: null }
          res = await backendClient.ask({
            question: question.trim(),
            jurisdiction: jur,
            as_of_date: item.asOf || new Date().toISOString().slice(0, 10),
            allow_hosted_processing: allowHosted
          }, control.signal)
        } else {
          throw gErr
        }
      }

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
      {/* Top Tab Bar: Live vs Mock */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 18, borderBottom: '1px solid #333', paddingBottom: 12 }}>
        {backendMode === 'live' && backendClient && (
          <button
            type="button"
            className={`button ${activeTab === 'live' ? 'primary' : ''}`}
            onClick={() => setActiveTab('live')}
          >
            <Sparkles size={16} />
            {t('Live AI Guidance', 'लाइव AI मार्गदर्शन')}
          </button>
        )}
        <button
          type="button"
          className={`button ${activeTab === 'mock' ? 'primary' : ''}`}
          onClick={() => setActiveTab('mock')}
        >
          <FlaskConicalIcon size={16} />
          {t('Offline / Mock Scenarios', 'ऑफ़लाइन / कृत्रिम परिदृश्य')}
        </button>
      </div>

      {activeTab === 'live' && backendMode === 'live' && (
        <div className="live-guidance-container">
          <div className="notice" style={{ borderColor: '#d4af37' }}>
            <ShieldCheck size={18} />
            <div>
              <strong>{t('AYUNEX AI · Authoritative Legal Knowledge & AI Guidance', 'AYUNEX AI · प्रामाणिक वैधानिक ज्ञान एवं AI मार्गदर्शन')}</strong>
              <p style={{ margin: '4px 0 0', fontSize: 13 }}>
                {t(
                  'Grounds responses in verified statutory evidence (Patents Act, Biological Diversity Act, Drug Rules). An automated semantic review verifies each claim before publication.',
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
                        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>{claim.text}</p>
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

      {/* Mock Scenarios Section */}
      {(activeTab === 'mock' || backendMode !== 'live') && (
        <div className="mock-guidance-content">
          <div className="notice">
            <strong>{t('MOCK API · Synthetic evidence, not legal advice.', 'कृत्रिम API · परीक्षण प्रमाण, कानूनी सलाह नहीं।')}</strong>
            <span>{t('Local simulation mode for testing frontend edge cases and scenarios.', 'स्थानीय अनुकरण मोड: फ्रंटएंड परिदृश्यों के परीक्षण हेतु।')}</span>
          </div>

          <div className="toolbar">
            <label htmlFor="mock-scenario">{t('Test scenario', 'परीक्षण स्थिति')}</label>
            <select
              id="mock-scenario"
              value={scenario}
              disabled={mockBusy}
              onChange={e => {
                setScenario(e.target.value)
                setMockAnswer({ sections: [], sources: [] })
                setMockError('')
              }}
            >
              {scenarios.map(s => <option key={s}>{s}</option>)}
            </select>
            <button
              className="button primary"
              disabled={mockBusy || (!item.confirmed && !item.general)}
              onClick={runMock}
            >
              {t('Run mock guidance', 'कृत्रिम मार्गदर्शन चलाएँ')}
            </button>
            {mockBusy && <button className="button" onClick={cancelMock}>{t('Cancel', 'रद्द करें')}</button>}
          </div>

          {!item.confirmed && !item.general && (
            <div className="notice">
              {t('Confirm your Passport facts first.', 'पहले पासपोर्ट के तथ्यों की पुष्टि करें।')}{' '}
              <Link to={`/cases/${item.id}/classification`}>{t('Review facts', 'तथ्य देखें')}</Link>
            </div>
          )}

          {mockBusy && <p role="status">{t('Retrieving test fixtures; only verified mock sections are displayed…', 'परीक्षण प्रमाण प्राप्त हो रहे हैं…')}</p>}
          {mockError && <p className="notice" role="alert">{mockError}</p>}

          {mockAnswer.support && (
            <div className="panel">
              <span className="status">MOCK · {item.jurisdiction} · {item.asOf} · {mockAnswer.support}</span>
              <p>{t('No legal category has been assigned. These states demonstrate the frontend contract.', 'कोई कानूनी श्रेणी निर्धारित नहीं है। ये स्थितियाँ फ्रंटएंड परीक्षण के लिए हैं।')}</p>
              {scenario === 'restricted' && <p>{t('Restricted fixture: permission must be checked by the backend. No access is granted here.', 'प्रतिबंधित प्रमाण: अनुमति की जाँच बैकएंड करेगा।')}</p>}
              {scenario === 'translation_unavailable' && <p role="alert">{t('Translation unavailable. Original test passage remains unchanged.', 'अनुवाद उपलब्ध नहीं है। मूल परीक्षण पाठ दिखाया गया है।')}</p>}
            </div>
          )}

          {mockAnswer.assessments && (
            <div className="assessment-grid">
              {mockAnswer.assessments.map(a => (
                <article className="panel" key={a.domain}>
                  <h3>{a.domain} · MOCK</h3>
                  <p>{a.candidate}</p>
                  <small>{mockAnswer.ruleset}</small>
                  {a.conditions.map(c => (
                    <div className="condition" key={c.name}>{c.name}<span>{c.state}</span></div>
                  ))}
                </article>
              ))}
            </div>
          )}

          <div className="section-list">
            {sectionTitles.map(([title, hindi], i) => {
              const section = mockAnswer.sections?.find(s => s.id === `section-${i}`)
              return (
                <details key={title} open={i === 0}>
                  <summary>
                    {hi ? hindi : title}
                    <span className="status">{item.jurisdiction} · {section?.support || 'MISSING_EVIDENCE'}</span>
                  </summary>
                  <div>
                    {section?.verified ? (
                      <>
                        <p>{hi && scenario !== 'translation_unavailable' ? section.textHi : section.text}</p>
                        {section.citationIds.map(cid => (
                          <button
                            key={cid}
                            className="button"
                            onClick={() => setSelectedCitation(mockAnswer.sources.find(s => s.id === cid))}
                          >
                            {t('Inspect synthetic citation', 'कृत्रिम संदर्भ देखें')} [{cid}]
                          </button>
                        ))}
                      </>
                    ) : (
                      <p>{t('Unresolved. No verified mock section is available.', 'अनिर्णीत। सत्यापित कृत्रिम अनुभाग उपलब्ध नहीं है।')}</p>
                    )}
                  </div>
                </details>
              )
            })}
          </div>
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

function FlaskConicalIcon(props) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={props.size || 24} height={props.size || 24} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M10 2v7.31L4.1 19.34A2 2 0 0 0 5.8 22h12.4a2 2 0 0 0 1.7-2.66L14 9.31V2" />
      <line x1="8.5" x2="15.5" y1="2" y2="2" />
      <line x1="14" x2="10" y1="14" y2="14" />
    </svg>
  )
}
