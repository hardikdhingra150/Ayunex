import { useState } from 'react'
import { Server, ShieldCheck, AlertCircle } from 'lucide-react'
import Modal from './Modal'
import { useApp } from '../context'
import { fetchSession } from '../backendClient'

const DEV_TOKEN = '-o7JRlGIO4I9t4q2xvreNNSiDL_3uyTZ9b-95rp9WXo'

export default function ConnectionModal({ isOpen, onClose }) {
  const { language, backendMode, backendToken, backendRole, connectionStatus, connectBackend, disconnectBackend } = useApp()
  const hi = language === 'hi'
  const t = (en, hindi) => hi ? hindi : en

  const [token, setToken] = useState(backendToken || '')
  const [role, setRole] = useState(backendRole || 'user')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (!isOpen) return null

  async function handleConnect(e) {
    e.preventDefault()
    setError('')
    if (!token.trim()) {
      setError(t('Please enter a development token.', 'कृपया डेवलपर टोकन दर्ज करें।'))
      return
    }
    setBusy(true)
    const res = await connectBackend(token.trim(), role)
    setBusy(false)
    if (res.ok) {
      onClose()
    } else {
      setError(res.error)
    }
  }

  function handleDisconnect() {
    disconnectBackend()
    onClose()
  }

  const isConnected = backendMode === 'live' && connectionStatus === 'connected'

  return (
    <Modal
      title={t('Backend Connection & Identity', 'बैकएंड कनेक्शन और पहचान')}
      onClose={onClose}
    >
      <div className="connection-modal-content">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: '#131b23', borderRadius: 8, marginBottom: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Server size={20} color={isConnected ? '#56d364' : '#888'} />
            <div>
              <strong style={{ display: 'block', fontSize: 14 }}>
                {isConnected ? t('Live FastAPI Backend', 'लाइव FastAPI बैकएंड') : t('Offline Session Mode', 'ऑफ़लाइन सत्र मोड')}
              </strong>
              <small style={{ color: '#8c8c8c' }}>http://127.0.0.1:8000</small>
            </div>
          </div>
          <span className={`backend-pill ${isConnected ? 'live' : 'mock'}`}>
            <span className="dot" />
            {isConnected ? t('CONNECTED', 'सक्रिय') : t('DISCONNECTED', 'निष्क्रिय')}
          </span>
        </div>

        {error && (
          <div className="notice" style={{ borderColor: '#ff4d4f', color: '#ff7875', marginBottom: 14 }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleConnect}>
          <div className="field">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <label htmlFor="dev-token-input">{t('Development Bearer Token', 'डेवलपर बियरर टोकन')}</label>
              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  type="button"
                  className="text-link"
                  style={{ background: 'none', fontSize: 12, padding: 0 }}
                  onClick={async () => {
                    try {
                      setBusy(true)
                      const res = await fetchSession(role)
                      if (res?.token) {
                        setToken(res.token)
                        await connectBackend(res.token, role)
                        onClose()
                      }
                    } catch (err) {
                      setError(err.message || 'Failed to auto-provision session')
                    } finally {
                      setBusy(false)
                    }
                  }}
                >
                  {t('Auto-Provision Session', 'स्वचालित सत्र टोकन प्राप्त करें')}
                </button>
                <span style={{ color: '#444' }}>·</span>
                <button
                  type="button"
                  className="text-link"
                  style={{ background: 'none', fontSize: 12, padding: 0 }}
                  onClick={() => setToken(DEV_TOKEN)}
                >
                  {t('Fill backend/.dev-token', 'स्थानीय dev-token भरें')}
                </button>
              </div>
            </div>
            <input
              id="dev-token-input"
              type="password"
              autoComplete="off"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste backend/.dev-token or use Auto-Provision"
              disabled={busy}
              style={{ fontFamily: 'monospace', fontSize: 13 }}
            />
            <small style={{ color: '#888' }}>
              {t('Token is kept strictly in session memory. Never stored in local storage.', 'टोकन केवल सत्र स्मृति में रहता है। स्थानीय संग्रह में नहीं।')}
            </small>
          </div>

          <div className="field" style={{ marginTop: 14 }}>
            <label htmlFor="dev-role-select">{t('Identity Role', 'पहचान भूमिका')}</label>
            <select
              id="dev-role-select"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              disabled={busy}
            >
              <option value="user">{t('Innovator / User (Normal case workflow)', 'अन्वेषक / उपयोगकर्ता (सामान्य केस कार्यप्रवाह)')}</option>
              <option value="facilitator">{t('Human Facilitator (Review & queue workflow)', 'मानव विशेषज्ञ (समीक्षा एवं कतार कार्यप्रवाह)')}</option>
              <option value="curator">{t('Corpus Curator (Statutory approvals & audit)', 'ज्ञान क्यूरेटर (वैधानिक अनुमोदन और ऑडिट)')}</option>
              <option value="administrator">{t('Administrator (Full audit & permissions)', 'प्रशासक (पूर्ण ऑडिट और अनुमतियाँ)')}</option>
            </select>
          </div>

          <div className="notice" style={{ marginTop: 16 }}>
            <ShieldCheck size={16} />
            <span>
              {t(
                'Live mode connects Product Passports, classification runs, and evidence retrieval to the local FastAPI server. You can switch back to session-only mode anytime.',
                'लाइव मोड उत्पाद पासपोर्ट, वर्गीकरण और प्रमाण खोज को स्थानीय सर्वर से जोड़ता है। आप कभी भी सत्र मोड पर लौट सकते हैं।'
              )}
            </span>
          </div>

          <div className="form-actions" style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
            {isConnected && (
              <button
                type="button"
                className="button danger"
                onClick={handleDisconnect}
                disabled={busy}
              >
                {t('Disconnect / Mock Mode', 'अलग करें / सत्र मोड')}
              </button>
            )}
            <button
              type="button"
              className="button"
              onClick={onClose}
              disabled={busy}
            >
              {t('Close', 'बंद करें')}
            </button>
            <button
              type="submit"
              className="button primary"
              disabled={busy || !token.trim()}
            >
              {busy ? t('Connecting…', 'जुड़ रहा है…') : isConnected ? t('Update Connection', 'अपडेट करें') : t('Connect to Backend', 'बैकएंड से जुड़ें')}
            </button>
          </div>
        </form>
      </div>
    </Modal>
  )
}
