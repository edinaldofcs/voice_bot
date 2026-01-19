import { useState, useEffect, useRef } from 'react'
import './index.css'

function App() {
  const [status, setStatus] = useState('disconnected')
  const [messages, setMessages] = useState([])
  const [currentAiMessage, setCurrentAiMessage] = useState("")
  const [isCallActive, setIsCallActive] = useState(false)
  const [mode, setMode] = useState('tree') // Default para o modo mais rápido

  const ws = useRef(null)
  const mediaRecorder = useRef(null)
  const audioChunks = useRef([])
  const messagesEndRef = useRef(null)

  const audioQueue = useRef([])
  const isPlaying = useRef(false)
  const currentAudioSource = useRef(null)

  const statusRef = useRef(status)

  // VAD Refs
  const audioContext = useRef(null)
  const analyser = useRef(null)
  const silenceTimer = useRef(null)
  const streamRef = useRef(null)

  const SILENCE_THRESHOLD = 0.015
  const SILENCE_DURATION = 500

  useEffect(() => {
    statusRef.current = status
  }, [status])

  useEffect(() => {
    connectWebSocket()
    return () => {
      if (ws.current) ws.current.close()
      stopVAD()
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, currentAiMessage])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const connectWebSocket = () => {
    ws.current = new WebSocket('ws://localhost:8000/ws')

    ws.current.onopen = () => {
      setStatus('idle')
      ws.current.send(JSON.stringify({ type: 'set_mode', mode: mode }))
    }

    ws.current.onclose = () => {
      setStatus('disconnected')
      setIsCallActive(false)
      setTimeout(connectWebSocket, 3000)
    }

    ws.current.onmessage = async (event) => {
      if (event.data instanceof Blob) {
        audioQueue.current.push(event.data)
        processAudioQueue()
      } else {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'user_transcript') {
            addMessage('user', data.content)
            setCurrentAiMessage("")
          } else if (data.type === 'ai_text_chunk') {
            setCurrentAiMessage(prev => prev + " " + data.content)
          } else if (data.type === 'ai_text_complete') {
            addMessage('ai', data.content)
            setCurrentAiMessage("")
            if (!isPlaying.current && audioQueue.current.length === 0) {
              setStatus('idle')
            }
          }
        } catch (e) {
          console.error("Error parsing JSON:", e)
        }
      }
    }
  }

  const handleModeChange = (newMode) => {
    if (isCallActive) return
    setMode(newMode)
    setMessages([])
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'set_mode', mode: newMode }))
    }
  }

  const stopCurrentAudio = () => {
    if (currentAudioSource.current) {
      currentAudioSource.current.pause()
      currentAudioSource.current.src = ""
      currentAudioSource.current = null
    }
    audioQueue.current = []
    isPlaying.current = false
  }

  const processAudioQueue = async () => {
    if (isPlaying.current || audioQueue.current.length === 0) return

    isPlaying.current = true
    setStatus('playing')

    const audioBlob = audioQueue.current.shift()
    const audioUrl = URL.createObjectURL(audioBlob)
    const audio = new Audio(audioUrl)
    currentAudioSource.current = audio

    audio.onended = () => {
      isPlaying.current = false
      currentAudioSource.current = null
      if (audioQueue.current.length === 0) {
        setStatus('idle')
      } else {
        processAudioQueue()
      }
    }

    try {
      await audio.play()
    } catch (e) {
      isPlaying.current = false
      setStatus('idle')
    }
  }

  const addMessage = (role, text) => {
    setMessages(prev => [...prev, { role, text }])
  }

  const startVAD = (stream) => {
    if (audioContext.current) stopVAD()

    audioContext.current = new (window.AudioContext || window.webkitAudioContext)()
    const source = audioContext.current.createMediaStreamSource(stream)
    analyser.current = audioContext.current.createAnalyser()
    analyser.current.fftSize = 512
    source.connect(analyser.current)

    const dataArray = new Uint8Array(analyser.current.frequencyBinCount)

    const checkAudio = () => {
      if (!analyser.current) return
      analyser.current.getByteTimeDomainData(dataArray)

      let sum = 0
      for (let i = 0; i < dataArray.length; i++) {
        const v = (dataArray[i] - 128) / 128
        sum += v * v
      }
      const rms = Math.sqrt(sum / dataArray.length)

      if (rms > SILENCE_THRESHOLD && (statusRef.current === 'playing' || statusRef.current === 'processing')) {
        stopCurrentAudio()
        setStatus('idle')
      }

      if (rms < SILENCE_THRESHOLD) {
        if (!silenceTimer.current) {
          silenceTimer.current = setTimeout(() => {
            if (statusRef.current === 'recording') {
              sendAudioAndRestart();
            }
          }, SILENCE_DURATION)
        }
      } else {
        if (silenceTimer.current) {
          clearTimeout(silenceTimer.current)
          silenceTimer.current = null
        }
      }
      requestAnimationFrame(checkAudio)
    }
    checkAudio()
  }

  const sendAudioAndRestart = () => {
    if (mediaRecorder.current && mediaRecorder.current.state === 'recording') {
      mediaRecorder.current.stop()
    }
  }

  const stopVAD = () => {
    if (audioContext.current) {
      if (audioContext.current.state !== 'closed') audioContext.current.close()
    }
    audioContext.current = null
    analyser.current = null
    if (silenceTimer.current) clearTimeout(silenceTimer.current)
    silenceTimer.current = null
  }

  const startRecording = async () => {
    if (statusRef.current === 'recording' || !isCallActive) return

    try {
      if (!streamRef.current) {
        streamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true })
      }

      mediaRecorder.current = new MediaRecorder(streamRef.current)
      audioChunks.current = []

      mediaRecorder.current.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunks.current.push(event.data)
      }

      mediaRecorder.current.onstop = () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' })
        if (audioBlob.size > 2000 && ws.current && ws.current.readyState === WebSocket.OPEN) {
          ws.current.send(audioBlob)
          setStatus('processing')
        } else {
          if (isCallActive) setStatus('idle')
        }
      }

      mediaRecorder.current.start()
      setStatus('recording')
      if (!analyser.current) startVAD(streamRef.current)
    } catch (err) {
      setIsCallActive(false)
    }
  }

  const startCall = () => {
    setIsCallActive(true)
    setMessages([])
    setStatus('idle')
  }

  const endCall = () => {
    setIsCallActive(false)
    stopCurrentAudio()
    if (mediaRecorder.current) mediaRecorder.current.stop()
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    stopVAD()
    setStatus('idle')
  }

  useEffect(() => {
    if (isCallActive && status === 'idle') {
      startRecording()
    }
  }, [status, isCallActive])

  return (
    <div className="app-container">
      <header className="header">
        <h1>Voz Realtime AI</h1>
        <div className="tabs">
          <button
            className={`tab ${mode === 'ai' ? 'active' : ''}`}
            onClick={() => handleModeChange('ai')}
            disabled={isCallActive}
          >
            IA Generativa
          </button>
          <button
            className={`tab ${mode === 'tree' ? 'active' : ''}`}
            onClick={() => handleModeChange('tree')}
            disabled={isCallActive}
          >
            Fluxo de Árvore
          </button>
        </div>
      </header>

      <main className="chat-area">
        {messages.length === 0 && !currentAiMessage && (
          <div style={{ textAlign: 'center', marginTop: '40px', color: 'var(--text-muted)' }}>
            <p>Selecione o modo e inicie a chamada para começar.</p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <strong>{msg.role === 'user' ? 'Você' : 'Atendente'}</strong>
            {msg.text}
          </div>
        ))}
        {currentAiMessage && (
          <div className="message ai">
            <strong>Atendente</strong>
            {currentAiMessage}
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      <footer className="controls">
        <div className="status-badge">
          <div className={`status-dot ${isCallActive ? 'active' : ''}`}></div>
          {status === 'disconnected' ? 'Offline' :
            status === 'recording' ? 'Ouvindo...' :
              status === 'playing' ? 'IA Falando...' :
                status === 'processing' ? 'Processando...' : 'Pronto'}
        </div>

        <div className={`visualizer ${status === 'recording' ? 'recording' : ''}`}>
          {[...Array(10)].map((_, i) => <div key={i} className="bar"></div>)}
        </div>

        {!isCallActive ? (
          <button className="call-button start" onClick={startCall}>
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M6.62,10.79C8.06,13.62 10.38,15.94 13.21,17.38L15.41,15.18C15.69,14.9 16.08,14.82 16.43,14.93C17.55,15.3 18.75,15.5 20,15.5A1,1 0 0,1 21,16.5V20A1,1 0 0,1 20,21A17,17 0 0,1 3,4A1,1 0 0,1 4,3H7.5A1,1 0 0,1 8.5,4C8.5,5.25 8.7,6.45 9.07,7.57C9.18,7.92 9.1,8.31 8.82,8.59L6.62,10.79Z" />
            </svg>
          </button>
        ) : (
          <button className="call-button end" onClick={endCall}>
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M6.62,10.79C8.06,13.62 10.38,15.94 13.21,17.38L15.41,15.18C15.69,14.9 16.08,14.82 16.43,14.93C17.55,15.3 18.75,15.5 20,15.5A1,1 0 0,1 21,16.5V20A1,1 0 0,1 20,21A17,17 0 0,1 3,4A1,1 0 0,1 4,3H7.5A1,1 0 0,1 8.5,4C8.5,5.25 8.7,6.45 9.07,7.57C9.18,7.92 9.1,8.31 8.82,8.59L6.62,10.79Z" />
            </svg>
          </button>
        )}
      </footer>
    </div>
  )
}

export default App
