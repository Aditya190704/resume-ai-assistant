import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'

const EXAMPLES = [
  { icon: '📝', label: 'Summarize', q: 'Summarize my resume.' },
  { icon: '🎯', label: 'Top skills', q: 'What are my strongest technical skills?' },
  { icon: '🧩', label: 'Projects', q: 'Explain my projects.' },
  { icon: '🛠️', label: 'Technologies', q: 'What technologies have I worked with?' },
  { icon: '🎤', label: 'Interview Qs', q: 'Generate interview questions based on my resume.' },
  { icon: '✍️', label: 'Pro summary', q: 'Create a professional summary.' },
  { icon: '🔍', label: 'Skill gaps', q: 'What skills are missing or unclear?' },
  { icon: '🚀', label: 'Improve', q: 'What areas of my resume could be improved?' },
]
const LOAD_STEPS = ['Reading your resume…', 'Understanding your question…', 'Writing your answer…']
const MAX_HISTORY = 20
const MAX_QUESTION = 2000

// Counts a number up from 0 for the stat cards.
function useCountUp(target, duration = 800) {
  const [n, setN] = useState(0)
  useEffect(() => {
    let raf = 0
    let start = null
    const tick = (t) => {
      if (start === null) start = t
      const p = Math.min((t - start) / duration, 1)
      setN(Math.round(target * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])
  return n
}

function Stat({ icon, label, value, hint, delay }) {
  const isNum = typeof value === 'number'
  const n = useCountUp(isNum ? value : 0)
  return (
    <div className="stat" style={{ animationDelay: `${delay}ms` }}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-text">
        <div className="stat-label">{label}</div>
        <div className="stat-value">{isNum ? n.toLocaleString() : value ?? '—'}</div>
        <div className="stat-hint">{hint}</div>
      </div>
    </div>
  )
}

// Shows the answer. When `animate` is true it reveals the text word by word.
// App gives it a new `key` for every answer, so it always starts fresh.
function Answer({ text, animate }) {
  const parts = text.split(/(\s+)/)
  const total = parts.length
  const [count, setCount] = useState(animate ? 0 : total)

  useEffect(() => {
    if (!animate) return
    let i = 0
    const id = setInterval(() => {
      i += 4
      setCount(i)
      if (i >= total) clearInterval(id)
    }, 30)
    return () => clearInterval(id)
  }, [animate, total])

  return (
    <div className="markdown">
      <ReactMarkdown>{parts.slice(0, count).join('')}</ReactMarkdown>
    </div>
  )
}

// Cycles through the loading steps while we wait for the answer.
function Loader() {
  const [step, setStep] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setStep((s) => Math.min(s + 1, LOAD_STEPS.length - 1)), 2500)
    return () => clearInterval(id)
  }, [])
  return (
    <div className="loader">
      <div className="dots"><span /><span /><span /></div>
      <ul className="steps">
        {LOAD_STEPS.map((s, i) => (
          <li key={s} className={i < step ? 'done' : i === step ? 'active' : ''}>
            <b>{i < step ? '✓' : i === step ? '●' : '○'}</b> {s}
          </li>
        ))}
      </ul>
      <div className="skeleton" style={{ width: '92%' }} />
      <div className="skeleton" style={{ width: '78%' }} />
      <div className="skeleton" style={{ width: '86%' }} />
      <div className="skeleton" style={{ width: '58%' }} />
    </div>
  )
}

function Empty({ onPick }) {
  const tiles = [
    { icon: '🎯', title: 'Find top skills', q: 'What are my strongest technical skills?' },
    { icon: '🧩', title: 'Explain projects', q: 'Explain my projects.' },
    { icon: '🎤', title: 'Interview prep', q: 'Generate interview questions based on my resume.' },
  ]
  return (
    <div className="empty">
      <div className="empty-icon">✨</div>
      <h4>Your answer will appear here</h4>
      <p className="muted">Upload a resume, ask a question and click Generate Response.</p>
      <div className="how">
        <div><span>1</span> Upload</div>
        <i />
        <div><span>2</span> Ask</div>
        <i />
        <div><span>3</span> Get answer</div>
      </div>
      <p className="muted try">Or try one of these:</p>
      <div className="tiles">
        {tiles.map((t) => (
          <button key={t.title} className="tile" onClick={() => onPick(t.q)}>
            <span>{t.icon}</span>
            {t.title}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const [config, setConfig] = useState({
    max_file_size_mb: 10,
    supported_extensions: ['.pdf', '.docx', '.txt'],
  })
  const [file, setFile] = useState(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [answerId, setAnswerId] = useState(0)
  const [fresh, setFresh] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [online, setOnline] = useState(null)
  const [responseTime, setResponseTime] = useState(null)
  const [wordCount, setWordCount] = useState(null)
  const [copied, setCopied] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    fetch('/api/config')
      .then((r) => r.json())
      .then(setConfig)
      .catch(() => {})
  }, [])

  // Live API status
  useEffect(() => {
    let alive = true
    const check = () =>
      fetch('/api/health')
        .then((r) => alive && setOnline(r.ok))
        .catch(() => alive && setOnline(false))
    check()
    const id = setInterval(check, 15000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  // Esc closes the history drawer
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && setDrawerOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  function pickFile(f) {
    if (!f) return
    const okType = config.supported_extensions.some((e) => f.name.toLowerCase().endsWith(e))
    if (!okType) {
      setFile(null)
      setError('Unsupported file type. Please upload a PDF, DOCX or TXT file.')
      return
    }
    if (f.size > config.max_file_size_mb * 1024 * 1024) {
      setFile(null)
      setError(`File is too large. Please upload a file smaller than ${config.max_file_size_mb} MB.`)
      return
    }
    setError('')
    setWordCount(null)
    setFile(f)
  }

  function removeFile(e) {
    e.stopPropagation()
    setFile(null)
    setWordCount(null)
  }

  async function generate() {
    if (loading) return
    setError('')
    setNotice('')
    if (!file) return setError('Please upload your resume first.')
    if (!question.trim()) return setError('Please enter a question about your resume.')

    setLoading(true)
    setAnswer('')
    const t0 = performance.now()
    try {
      const body = new FormData()
      body.append('file', file)
      body.append('question', question.trim())
      const res = await fetch('/api/ask', { method: 'POST', body })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(
          typeof data.detail === 'string' ? data.detail : 'Something went wrong. Please try again.',
        )
      }
      const secs = ((performance.now() - t0) / 1000).toFixed(1)
      setAnswerId((n) => n + 1)
      setAnswer(data.answer)
      setFresh(true)
      setResponseTime(secs)
      if (typeof data.word_count === 'number') setWordCount(data.word_count)
      if (data.truncated) setNotice('Your resume is very long, so only the first part was analysed.')
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      setHistory((h) =>
        [
          { id: Date.now(), question: question.trim(), file: file.name, answer: data.answer, time, secs },
          ...h,
        ].slice(0, MAX_HISTORY),
      )
    } catch (e) {
      setError(
        e instanceof TypeError ? 'Unable to reach the server. Please check your connection.' : e.message,
      )
    } finally {
      setLoading(false)
    }
  }

  function openHistory(item) {
    setAnswerId((n) => n + 1)
    setAnswer(item.answer)
    setQuestion(item.question)
    setResponseTime(item.secs)
    setFresh(false)
    setError('')
    setNotice('')
    setDrawerOpen(false)
  }

  async function copyAnswer() {
    try {
      await navigator.clipboard.writeText(answer)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // clipboard not available, ignore
    }
  }

  function download() {
    const blob = new Blob([answer], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'resume_answer.md'
    a.click()
    URL.revokeObjectURL(url)
  }

  const ext = file ? file.name.split('.').pop().toUpperCase() : null

  return (
    <>
      <div className="bg" aria-hidden="true">
        <span className="blob b1" />
        <span className="blob b2" />
      </div>

      <div className="app">
        {/* ---------- TOP BAR ---------- */}
        <header className="topbar">
          <div className="brand">
            <div className="logo">📄</div>
            <div>
              <h1>Resume AI Assistant</h1>
              <p>Upload your resume and ask questions about it.</p>
            </div>
          </div>
          <div className="top-chips">
            <span className="chip">🔒 Processed in memory</span>
            <span className="chip">⚡ Gemini on Vertex AI</span>
          </div>
          <div className="top-actions">
            <span className={`status ${online === null ? '' : online ? 'on' : 'off'}`}>
              <i />
              {online === null ? 'Checking…' : online ? 'API online' : 'API offline'}
            </span>
            <button className="hist-btn" onClick={() => setDrawerOpen(true)}>
              🕘 History
              {history.length > 0 && <b>{history.length}</b>}
            </button>
          </div>
        </header>

        {/* ---------- STATS ---------- */}
        <section className="stats">
          <Stat icon="💬" label="Questions asked" value={history.length} hint="this session" delay={80} />
          <Stat
            icon="⏱️"
            label="Response time"
            value={responseTime ? `${responseTime}s` : '—'}
            hint="last answer"
            delay={160}
          />
          <Stat
            icon="🧾"
            label="Resume words"
            value={wordCount}
            hint="extracted from file"
            delay={240}
          />
          <Stat
            icon="📎"
            label="File"
            value={ext || '—'}
            hint={file ? `${Math.round(file.size / 1024)} KB` : 'No file yet'}
            delay={320}
          />
        </section>

        {/* ---------- MAIN GRID ---------- */}
        <main className="grid">
          {/* LEFT: output */}
          <section className="card output">
            {loading && <div className="progress" />}
            <div className="card-head">
              <div className="card-title">💡 AI Response</div>
              {answer && !loading && !error ? (
                <div className="head-actions">
                  <span className="badge">✓ Grounded in your resume</span>
                  <button className="icon-btn" onClick={copyAnswer}>
                    {copied ? '✓ Copied' : '📋 Copy'}
                  </button>
                  <button className="icon-btn" onClick={download}>⬇️ Download</button>
                </div>
              ) : null}
            </div>
            <div className="card-body">
              {loading ? (
                <Loader />
              ) : error ? (
                <div className="alert error">⚠️ {error}</div>
              ) : answer ? (
                <>
                  {notice && <div className="alert info">ℹ️ {notice}</div>}
                  <Answer key={answerId} text={answer} animate={fresh} />
                </>
              ) : (
                <Empty onPick={setQuestion} />
              )}
            </div>
            {answer && !loading && !error && (
              <div className="meta">
                <span>⏱ Answered in {responseTime}s</span>
                <span>📄 {file ? file.name : 'From history'}</span>
              </div>
            )}
          </section>

          {/* RIGHT: input */}
          <section className="card input">
            <div className="card-head">
              <div className="card-title">📤 Your Input</div>
              <span className="muted small">Ctrl + Enter to generate</span>
            </div>
            <div className="card-body">
              <div className="step"><span>1</span> Upload resume</div>
              <div
                className={`dropzone ${dragging ? 'drag' : ''} ${file ? 'has-file' : ''}`}
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragging(false)
                  pickFile(e.dataTransfer.files?.[0])
                }}
              >
                <div className="dz-icon">{file ? '✅' : '📁'}</div>
                <div className="dz-text">
                  <strong>{file ? file.name : 'Drag and drop your resume, or click to browse'}</strong>
                  <span>
                    {file
                      ? `${Math.round(file.size / 1024)} KB · click to replace`
                      : `${config.supported_extensions.join(' ').toUpperCase()} · up to ${config.max_file_size_mb} MB`}
                  </span>
                </div>
                {file && (
                  <button className="dz-x" onClick={removeFile} aria-label="Remove file">✕</button>
                )}
                <input
                  ref={inputRef}
                  type="file"
                  hidden
                  accept={config.supported_extensions.join(',')}
                  onChange={(e) => {
                    pickFile(e.target.files?.[0])
                    e.target.value = ''
                  }}
                />
              </div>

              <div className="step"><span>2</span> Pick a quick question</div>
              <div className="pills">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex.label}
                    className={`pill ${question === ex.q ? 'active' : ''}`}
                    onClick={() => setQuestion(ex.q)}
                  >
                    {ex.icon} {ex.label}
                  </button>
                ))}
              </div>

              <div className="step"><span>3</span> Ask your question</div>
              <textarea
                value={question}
                maxLength={MAX_QUESTION}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') generate()
                }}
                rows={3}
                placeholder="e.g. What are my strongest technical skills?"
              />
              <div className="counter">{question.length} / {MAX_QUESTION}</div>
            </div>
            <button className="btn primary" onClick={generate} disabled={loading}>
              {loading ? 'Generating…' : '✨ Generate Response'}
            </button>
          </section>
        </main>

        <footer className="foot">
          🔒 Your resume is not stored. History stays only until you refresh or close this tab.
        </footer>
      </div>

      {/* ---------- HISTORY DRAWER ---------- */}
      <div className={`backdrop ${drawerOpen ? 'open' : ''}`} onClick={() => setDrawerOpen(false)} />
      <aside className={`drawer ${drawerOpen ? 'open' : ''}`} aria-hidden={!drawerOpen}>
        <div className="drawer-head">
          <strong>🕘 History</strong>
          <button className="icon-btn" onClick={() => setDrawerOpen(false)}>✕</button>
        </div>
        <div className="drawer-body">
          {history.length === 0 ? (
            <p className="muted">Your questions from this session will appear here.</p>
          ) : (
            history.map((h) => (
              <button key={h.id} className="hist-card" onClick={() => openHistory(h)}>
                <div className="hc-top">
                  <span className="time">{h.time}</span>
                  <span className="hc-file">{h.file}</span>
                </div>
                <div className="hc-q">{h.question}</div>
              </button>
            ))
          )}
        </div>
        {history.length > 0 && (
          <button className="btn ghost" onClick={() => setHistory([])}>🗑️ Clear history</button>
        )}
      </aside>
    </>
  )
}