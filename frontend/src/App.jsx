import { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ClipboardCheck,
  CloudRain,
  Droplets,
  Eye,
  Gauge,
  Leaf,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  Sprout,
  Sun,
  ThermometerSun,
  TimerReset,
  Wind,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { askFarmGuard, getDashboard } from './api'

const metricConfig = {
  temperature_c: { label: 'Temperature', unit: '°C', icon: ThermometerSun },
  humidity_pct: { label: 'Humidity', unit: '%', icon: Droplets },
  rainfall_today_mm: { label: 'Rain total signal', unit: ' mm', icon: CloudRain },
  heat_index_c: { label: 'Heat index', unit: '°C', icon: ThermometerSun },
  wbgt_c: { label: 'WBGT', unit: '°C', icon: Gauge },
  wind_speed_ms: { label: 'Wind speed', unit: ' m/s', icon: Wind },
  pressure_hpa: { label: 'Air pressure', unit: ' hPa', icon: Activity },
  uv_raw: { label: 'Ultraviolet', unit: ' raw', icon: Sun },
  soil_moisture_pct: { label: 'Soil moisture', unit: '%', icon: Leaf },
  rain_signal_24h_mm: { label: '24h rain signal', unit: ' mm', icon: CloudRain },
  wbgt_peak_24h_c: { label: '24h peak WBGT', unit: '°C', icon: Gauge },
}

const timelineIcons = {
  conditions: Wind,
  heat: ThermometerSun,
  rain: CloudRain,
  humidity: Droplets,
}

function formatTime(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatClockTime(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

function formatDate(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
}

function riskClass(level = '') {
  return `risk-${level.toLowerCase()}`
}

function driverByKey(assessment, keys) {
  const wanted = Array.isArray(keys) ? keys : [keys]
  return assessment?.drivers?.find((d) => wanted.includes(d.key)) || null
}

function MetricCard({ field, value, label, unit, icon }) {
  const base = metricConfig[field] || {}
  const cfg = {
    ...base,
    ...(label ? { label } : {}),
    ...(unit !== undefined ? { unit } : {}),
    ...(icon ? { icon } : {}),
  }
  if (value === null || value === undefined) return null
  const Icon = cfg.icon || Activity

  return (
    <div className="metric-card glass-card">
      <div className="metric-icon"><Icon size={19} /></div>
      <div>
        <div className="eyebrow">{cfg.label}</div>
        <div className="metric-value">
          {Number(value).toFixed(1)}<span>{cfg.unit}</span>
        </div>
      </div>
    </div>
  )
}

function RiskGauge({ score, level }) {
  const angle = Math.max(0, Math.min(100, score)) * 3.6
  return (
    <div className="gauge-wrap">
      <div className="gauge" style={{ '--angle': `${angle}deg` }}>
        <div className="gauge-inner"><strong>{Math.round(score)}</strong><span>/100</span></div>
      </div>
      <span className={`risk-pill ${riskClass(level)}`}>{level}</span>
    </div>
  )
}

function FieldActionModule({ assessment }) {
  const checks = [
    { icon: Sprout, text: 'Check crop leaf stress' },
    { icon: Droplets, text: 'Confirm field moisture manually' },
    { icon: Eye, text: 'Inspect irrigation need' },
    { icon: TimerReset, text: 'Recheck next morning' },
  ]

  return (
    <div className="action-module">
      <div className="action-module-head">
        <div className="action-main-icon"><ClipboardCheck size={19} /></div>
        <div>
          <span className="eyebrow">Recommended field action</span>
          <strong>{assessment.action}</strong>
        </div>
      </div>
      <div className="action-checks">
        {checks.map(({ icon: Icon, text }) => (
          <div className="action-check" key={text}>
            <span><Icon size={15} /></span>
            <p>{text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function RecentConditions({ events = [] }) {
  return (
    <article className="glass-card timeline-card">
      <div className="section-head compact">
        <div>
          <div className="eyebrow">Latest 24 hours</div>
          <h2>Recent conditions</h2>
        </div>
        <Activity size={22} />
      </div>

      <div className="timeline-list">
        {events.length ? events.map((event, index) => {
          const Icon = timelineIcons[event.kind] || Activity
          return (
            <div className="timeline-event" key={`${event.title}-${event.timestamp}-${index}`}>
              <div className="timeline-rail">
                <div className={`timeline-icon timeline-${event.kind || 'conditions'}`}><Icon size={15} /></div>
                {index < events.length - 1 && <div className="timeline-line" />}
              </div>
              <div className="timeline-copy">
                <div className="timeline-top">
                  <strong>{event.title}</strong>
                  <time>{formatClockTime(event.timestamp)}</time>
                </div>
                <p>{event.detail}</p>
              </div>
            </div>
          )
        }) : (
          <div className="timeline-empty"><ShieldCheck size={18} /> No notable condition changes detected in this window.</div>
        )}
      </div>

      <div className="timeline-note">Events are generated from observed Conduit readings and do not change the risk score.</div>
    </article>
  )
}

function App() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [question, setQuestion] = useState('Why is the agricultural weather risk at this level?')
  const [chat, setChat] = useState([])
  const [asking, setAsking] = useState(false)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      setData(await getDashboard())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const chartData = useMemo(
    () => !data ? [] : data.history.map((row) => ({
      ...row,
      t: new Date(row.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }),
    })),
    [data],
  )

  const submitQuestion = async (event) => {
    event?.preventDefault()
    const q = question.trim()
    if (!q || asking) return
    setAsking(true)
    setChat((prev) => [...prev, { role: 'user', text: q }])
    setQuestion('')
    try {
      const result = await askFarmGuard(q)
      setChat((prev) => [...prev, { role: 'assistant', text: result.answer, provider: result.provider }])
    } catch (e) {
      setChat((prev) => [...prev, { role: 'assistant', text: `I couldn't answer: ${e.message}` }])
    } finally {
      setAsking(false)
    }
  }

  if (loading) return <div className="screen-center"><RefreshCw className="spin" /> Loading FarmGuard…</div>
  if (error) return <div className="screen-center error-state"><AlertTriangle /><h2>Backend connection failed</h2><p>{error}</p><button onClick={load}>Try again</button></div>

  const { latest, assessment, source, data_quality, recent_conditions = [] } = data
  const rainDriver = driverByKey(assessment, ['rainfall_today_mm', 'rainfall_instant_mm'])
  const wbgtDriver = driverByKey(assessment, 'wbgt_c')
  const summaryMetrics = [
    { field: 'temperature_c', value: latest.temperature_c, label: 'Latest temperature' },
    { field: 'humidity_pct', value: latest.humidity_pct, label: 'Latest humidity' },
    { field: 'rain_signal_24h_mm', value: rainDriver?.value },
    { field: 'wbgt_peak_24h_c', value: wbgtDriver?.value },
    { field: 'wind_speed_ms', value: latest.wind_speed_ms },
    {
      field: latest.uv_index != null ? 'uv_index' : 'uv_raw',
      value: latest.uv_index ?? latest.uv_raw,
      label: latest.uv_index != null ? 'UV index' : 'Ultraviolet',
      unit: latest.uv_index != null ? '' : ' raw',
    },
  ].filter((m) => m.value !== null && m.value !== undefined)

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><Leaf size={22} /></div>
          <div><strong>Conduit FarmGuard</strong><span>From environmental data to agricultural action</span></div>
        </div>
        <div className="top-actions">
          <div className={`source-chip ${source.mode !== 'sample' ? 'live' : ''}`}><span className="source-dot" /> {source.label}</div>
          <button className="icon-button" onClick={load} aria-label="Refresh dashboard"><RefreshCw size={17} /></button>
        </div>
      </header>

      {source.mode === 'sample'
        ? <div className="demo-banner"><AlertTriangle size={16} /> Demo mode: switch to the real Conduit export before submission.</div>
        : <div className="real-banner"><ShieldCheck size={16} /> Real JKUAT Conduit export loaded • {data_quality.readings_used.toLocaleString()} readings • {formatDate(data_quality.coverage_start)}–{formatDate(data_quality.coverage_end)}</div>}

      <section className="hero-grid">
        <article className="glass-card risk-card">
          <div className="section-head">
            <div><div className="eyebrow">Agricultural weather stress • latest 24 hours</div><h1>{assessment.level.charAt(0) + assessment.level.slice(1).toLowerCase()} agricultural weather stress</h1></div>
            <ShieldCheck size={26} />
          </div>
          <div className="risk-layout">
            <RiskGauge score={assessment.score} level={assessment.level} />
            <div className="recommendation">
              <h3>Recommended next step</h3>
              <p>{assessment.recommendation}</p>
              <FieldActionModule assessment={assessment} />
              <small>{assessment.caveat}</small>
            </div>
          </div>
        </article>

        <article className="glass-card snapshot-card">
          <div className="section-head compact">
            <div><div className="eyebrow">Latest Conduit reading</div><h2>Environmental snapshot</h2></div>
            <Activity size={22} />
          </div>
          <div className="snapshot-meta"><span>{formatTime(latest.timestamp)}</span><span>{data_quality.readings_used.toLocaleString()} readings analyzed</span></div>
          <div className="mini-quality">{assessment.has_soil_moisture ? 'Soil moisture available' : 'Weather-station mode • no soil-moisture field in this export'}</div>
        </article>
      </section>

      <section className="metrics-grid">{summaryMetrics.map((m) => <MetricCard key={m.field} {...m} />)}</section>

      <section className="content-grid">
        <article className="glass-card chart-card">
          <div className="section-head compact"><div><div className="eyebrow">24-hour trend • {chartData.length} readings</div><h2>Heat & moisture signals</h2></div><Gauge size={22} /></div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={290}>
              <LineChart data={chartData} margin={{ top: 12, right: 10, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,.08)" />
                <XAxis dataKey="t" tick={{ fill: '#8ea59b', fontSize: 11 }} minTickGap={28} />
                <YAxis tick={{ fill: '#8ea59b', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#0d1d17', border: '1px solid #234237', borderRadius: 12 }} />
                <Legend />
                {latest.temperature_c != null && <Line type="monotone" dataKey="temperature_c" name="Temp °C" stroke="currentColor" strokeWidth={2} dot={false} />}
                {latest.wbgt_c != null && <Line type="monotone" dataKey="wbgt_c" name="WBGT °C" stroke="currentColor" strokeWidth={1.8} strokeDasharray="5 4" dot={false} />}
                {latest.humidity_pct != null && <Line type="monotone" dataKey="humidity_pct" name="Humidity %" stroke="currentColor" strokeWidth={1.5} opacity={0.6} dot={false} />}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="glass-card drivers-card">
          <div className="section-head compact"><div><div className="eyebrow">Explainability</div><h2>Why this score?</h2></div><Sparkles size={22} /></div>
          <div className="driver-list">
            {assessment.drivers.map((d) => (
              <div className="driver" key={d.key}>
                <div className="driver-top"><span>{d.label}</span><strong>+{Math.round(d.contribution)}</strong></div>
                <div className="driver-track"><div style={{ width: `${Math.min(100, d.risk)}%` }} /></div>
                <div className="driver-bottom"><span>{d.value}{d.unit}</span><span>{Math.round(d.risk)} risk</span></div>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="content-grid lower-grid">
        <article className="glass-card rainfall-card">
          <div className="section-head compact"><div><div className="eyebrow">Precipitation • JKUAT Conduit rain gauge</div><h2>24-hour rainfall pattern</h2></div><CloudRain size={22} /></div>
          <div className="chart-wrap small">
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData} margin={{ top: 12, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,.08)" />
                <XAxis dataKey="t" tick={{ fill: '#8ea59b', fontSize: 11 }} minTickGap={28} />
                <YAxis tick={{ fill: '#8ea59b', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#0d1d17', border: '1px solid #234237', borderRadius: 12 }} />
                <Area type="monotone" dataKey="rainfall_today_mm" name="Rain total signal (mm)" stroke="currentColor" fill="currentColor" fillOpacity={0.15} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="anomaly-box">
            {assessment.anomalies.length
              ? assessment.anomalies.map((a) => <p key={a.field}><AlertTriangle size={14} /> {a.message}</p>)
              : <p><ShieldCheck size={14} /> No strong 2σ anomalies in the latest weather reading.</p>}
          </div>
        </article>

        <RecentConditions events={recent_conditions} />
      </section>

      <section className="assistant-row">
        <article className="glass-card assistant-card assistant-wide">
          <div className="section-head compact"><div><div className="eyebrow">AI explanation layer</div><h2>Ask FarmGuard</h2></div><Bot size={22} /></div>
          <div className="chat-window">
            {chat.length === 0 && <div className="assistant-intro"><Bot size={23} /><p>Ask which weather signal matters most, why the score changed, or what field check FarmGuard recommends.</p></div>}
            {chat.map((m, idx) => <div className={`chat-bubble ${m.role}`} key={idx}><p>{m.text}</p>{m.provider && <small>{m.provider === 'gemini' ? 'Gemini explanation' : 'Local fallback explanation'}</small>}</div>)}
            {asking && <div className="chat-bubble assistant typing">Analyzing current signals…</div>}
          </div>
          <form className="chat-form" onSubmit={submitQuestion}>
            <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Why is the weather stress at this level?" />
            <button disabled={asking || !question.trim()} aria-label="Ask FarmGuard"><Send size={17} /></button>
          </form>
        </article>
      </section>

      <footer><span>Conduit FarmGuard • Hack The Weather 2026 prototype</span><span>Data → Insight → Decision → Impact</span></footer>
    </main>
  )
}

export default App
