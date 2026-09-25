import { useState, useEffect, useRef } from 'react'
import { Mic, MicOff, Check, AlertCircle } from 'lucide-react'
import Modal from './Modal'

const SpeechRecognition = typeof window !== 'undefined' ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null

export default function VoiceInputModal({ isOpen, onClose, onConfirm, initialLanguage = 'en', fieldLabel = 'field' }) {
  const [lang, setLang] = useState(initialLanguage === 'hi' ? 'hi-IN' : 'en-IN')
  const [isListening, setIsListening] = useState(false)
  const [editedText, setEditedText] = useState('')
  const [error, setError] = useState(() => !SpeechRecognition ? (initialLanguage === 'hi'
    ? 'आपके ब्राउज़र में आवाज़ पहचान (Web Speech API) उपलब्ध नहीं है। कृपया मैन्युअल रूप से टाइप करें।'
    : 'Web Speech API is not supported in this browser. Please type directly.') : '')
  const recognitionRef = useRef(null)

  const isHindi = lang.startsWith('hi')

  useEffect(() => {
    if (!SpeechRecognition) return

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = lang

    recognition.onresult = (event) => {
      let finalTranscript = ''
      let interimTranscript = ''
      for (let i = 0; i < event.results.length; i++) {
        const item = event.results[i]
        if (item.isFinal) {
          finalTranscript += item[0].transcript + ' '
        } else {
          interimTranscript += item[0].transcript
        }
      }
      const combined = (finalTranscript + interimTranscript).trim()
      setEditedText(combined)
    }

    recognition.onerror = (e) => {
      if (e.error !== 'no-speech') {
        setError(isHindi ? `आवाज़ पहचान त्रुटि: ${e.error}` : `Voice recognition error: ${e.error}`)
      }
      setIsListening(false)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognitionRef.current = recognition

    return () => {
      try {
        recognition.stop()
      } catch (err) {
        void err
      }
    }
  }, [lang, isHindi])

  if (!isOpen) return null

  function toggleListening() {
    setError('')
    if (!recognitionRef.current) return
    if (isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
    } else {
      try {
        recognitionRef.current.lang = lang
        recognitionRef.current.start()
        setIsListening(true)
      } catch (err) {
        setError(err.message)
      }
    }
  }

  function handleApply() {
    if (recognitionRef.current && isListening) {
      try {
        recognitionRef.current.stop()
      } catch (err) {
        void err
      }
    }
    onConfirm(editedText.trim())
    onClose()
  }

  return (
    <Modal
      title={isHindi ? `बोलकर दर्ज करें: ${fieldLabel}` : `Voice input: ${fieldLabel}`}
      onClose={() => {
        if (recognitionRef.current && isListening) {
          try {
            recognitionRef.current.stop()
          } catch (err) {
            void err
          }
        }
        onClose()
      }}
    >
      <div className="voice-modal-content">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <label htmlFor="voice-lang-select" style={{ fontSize: 13, color: '#a0a0a0' }}>
              {isHindi ? 'भाषा:' : 'Language:'}
            </label>
            <select
              id="voice-lang-select"
              value={lang}
              disabled={isListening}
              onChange={(e) => setLang(e.target.value)}
              style={{ padding: '4px 8px', fontSize: 13, borderRadius: 6, background: '#1c1b18', color: '#f3ede2', border: '1px solid #333' }}
            >
              <option value="en-IN">English (India)</option>
              <option value="hi-IN">हिन्दी (Hindi)</option>
              <option value="en-US">English (US)</option>
            </select>
          </div>
          <span style={{ fontSize: 12, color: isListening ? '#d4af37' : '#777', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: isListening ? '#d4af37' : '#555', display: 'inline-block' }} />
            {isListening ? (isHindi ? 'सुन रहा है…' : 'Listening…') : (isHindi ? 'तैयार' : 'Ready')}
          </span>
        </div>

        {error && (
          <div className="notice" style={{ marginBottom: 14, borderColor: '#ff4d4f', color: '#ff7875' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '16px 0 20px' }}>
          <button
            type="button"
            className={`button ${isListening ? 'danger' : 'primary'}`}
            onClick={toggleListening}
            disabled={!SpeechRecognition}
            style={{ borderRadius: '50%', width: 56, height: 56, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: isListening ? '0 0 16px rgba(212,175,55,0.4)' : 'none' }}
            aria-label={isListening ? 'Stop listening' : 'Start listening'}
          >
            {isListening ? <MicOff size={26} /> : <Mic size={26} />}
          </button>
          <small style={{ marginTop: 10, color: '#aaa', fontSize: 12 }}>
            {isListening
              ? (isHindi ? 'रुकने के लिए क्लिक करें' : 'Click to stop recording')
              : (isHindi ? 'शुरू करने के लिए क्लिक करें' : 'Click microphone to speak')}
          </small>
        </div>

        <div className="field">
          <label htmlFor="transcription-review">
            <strong>{isHindi ? 'प्रतिलेखन समीक्षा एवं संपादन (सत्यापन आवश्यक):' : 'Review & confirm transcription (verification required):'}</strong>
          </label>
          <p style={{ fontSize: 12, color: '#8c8c8c', margin: '4px 0 8px' }}>
            {isHindi
              ? 'वानस्पतिक नाम, मात्रा, और नकारात्मक शब्द (नहीं/बिना) सहेजने से पहले जांच लें।'
              : 'Please check botanical names, quantities, and negation before applying.'}
          </p>
          <textarea
            id="transcription-review"
            rows={4}
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            placeholder={isHindi ? 'बोले गए शब्द यहाँ दिखेंगे। आप इन्हें संपादित भी कर सकते हैं।' : 'Spoken words will appear here. You can edit them freely.'}
            style={{ width: '100%', minHeight: 90 }}
          />
        </div>

        <div className="form-actions" style={{ marginTop: 18, display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button
            type="button"
            className="button"
            onClick={onClose}
          >
            {isHindi ? 'रद्द करें' : 'Cancel'}
          </button>
          <button
            type="button"
            className="button primary"
            disabled={!editedText.trim()}
            onClick={handleApply}
          >
            <Check size={16} />
            {isHindi ? 'तथ्य की पुष्टि करें' : 'Confirm & apply fact'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
