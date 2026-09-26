import { Link } from 'react-router-dom'
import { User, LogOut, ShieldCheck, Mail, Database } from 'lucide-react'
import Modal from './Modal'
import { useApp } from '../context'

function getInitials(profile) {
  const name = (profile?.display_name || profile?.email || '').trim()
  if (!name) return '?'
  const clean = name.includes('@') ? name.split('@')[0] : name
  const parts = clean.split(/[\s._-]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return clean.slice(0, 2).toUpperCase()
}

export default function ConnectionModal({isOpen, onClose}) {
  const { connectionStatus, disconnectBackend, profile, language } = useApp()
  if (!isOpen) return null
  const signedIn = connectionStatus === 'connected' && Boolean(profile)
  const hi = language === 'hi'

  const displayName = profile?.display_name || profile?.email?.split('@')[0] || 'User'

  return (
    <Modal title={signedIn ? displayName : (hi ? 'आपका खाता' : 'Your Account')} onClose={onClose}>
      {signedIn ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '12px 14px', background: '#1c1b18', borderRadius: 8, border: '1px solid #4a3d28' }}>
            <div className="avatar" style={{ width: 44, height: 44, fontSize: 16, background: '#302719', color: '#e7d2a5', border: '1px solid #665333', display: 'grid', placeItems: 'center', fontWeight: 600 }}>
              {getInitials(profile)}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <strong style={{ display: 'block', fontSize: 16, color: '#f4ede0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {displayName}
              </strong>
              <small style={{ color: '#a69b84', display: 'flex', alignItems: 'center', gap: 5, marginTop: 3 }}>
                <Mail size={12} /> {profile?.email || 'Authenticated User'}
              </small>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: 13 }}>
            <div style={{ padding: '10px 12px', background: '#151412', borderRadius: 6, border: '1px solid #332b1e' }}>
              <span style={{ color: '#8f836c', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, textTransform: 'uppercase' }}>
                <ShieldCheck size={12} /> {hi ? 'भूमिका' : 'Role'}
              </span>
              <strong style={{ textTransform: 'capitalize', color: '#e2cfab', display: 'block', marginTop: 4 }}>
                {profile?.role || 'User'}
              </strong>
            </div>
            <div style={{ padding: '10px 12px', background: '#151412', borderRadius: 6, border: '1px solid #332b1e' }}>
              <span style={{ color: '#8f836c', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, textTransform: 'uppercase' }}>
                <Database size={12} /> {hi ? 'डेटाबेस' : 'Database'}
              </span>
              <strong style={{ color: '#52c41a', display: 'block', marginTop: 4 }}>
                {hi ? 'सुरक्षित संग्रह' : 'Live Synced'}
              </strong>
            </div>
          </div>

          <p style={{ fontSize: 13, color: '#a69b84', margin: 0, lineHeight: 1.5 }}>
            {hi
              ? 'आपके सभी उत्पाद पासपोर्ट और शोध केस आपके निजी खाते में सुरक्षित हैं।'
              : 'Your cases and Product Passports are saved privately under your account.'}
          </p>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, marginTop: 8, paddingTop: 12, borderTop: '1px solid #332b1e' }}>
            <Link to="/settings" className="button" onClick={onClose}>
              {hi ? 'प्राथमिकताएं' : 'Preferences'}
            </Link>
            <button
              className="button danger"
              style={{ borderColor: '#ff4d4f', color: '#ff7875', display: 'inline-flex', alignItems: 'center', gap: 6 }}
              onClick={async () => {
                await disconnectBackend()
                onClose()
              }}
            >
              <LogOut size={14} />
              {hi ? 'साइन आउट' : 'Sign out'}
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <p>
            {hi
              ? 'केस सहेजने, उत्पाद पासपोर्ट बनाने और वैधानिक मार्गदर्शन प्राप्त करने के लिए साइन इन करें।'
              : 'Sign in to save your cases, create Product Passports, and run verified statutory queries.'}
          </p>
          <Link className="button primary" to="/login" onClick={onClose} style={{ textAlign: 'center', justifyContent: 'center' }}>
            <User size={15} style={{ marginRight: 6 }} />
            {hi ? 'साइन इन / खाता बनाएं' : 'Sign in / Create account'}
          </Link>
        </div>
      )}
    </Modal>
  )
}

