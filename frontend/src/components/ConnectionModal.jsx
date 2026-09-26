import { Link } from 'react-router-dom'
import Modal from './Modal'
import { useApp } from '../context'

export default function ConnectionModal({isOpen,onClose}) {
 const {connectionStatus,disconnectBackend}=useApp()
 if(!isOpen)return null
 const signedIn=connectionStatus==='connected'
 return <Modal title="Your account" onClose={onClose}><p>{signedIn?'Your work is linked to your private account.':'Sign in to save cases and ask source-grounded questions. Demo cases are not saved to an account.'}</p><p>Your AI provider credentials stay on the server. No developer key is required.</p>{signedIn?<button className="button" onClick={async()=>{await disconnectBackend();onClose()}}>Sign out</button>:<Link className="button primary" to="/login" onClick={onClose}>Sign in / Create account</Link>}</Modal>
}
