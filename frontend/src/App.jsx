import { useState, useRef } from 'react'

const API = '/api'

const CHECKS = [
  { id: 'http',      label: 'Cabeceras HTTP',     icon: '🔒' },
  { id: 'email',     label: 'Seguridad de email', icon: '✉️' },
  { id: 'ssl',       label: 'SSL / TLS',          icon: '🔐' },
  { id: 'ai',        label: 'Superficie IA',      icon: '🤖' },
  { id: 'narrative', label: 'Diagnóstico Claude', icon: '🧠' },
]

const SEV = {
  critical: { bg: '#fff1f0', border: '#ffa39e', text: '#cf1322', label: 'Crítico',  dot: '#f5222d' },
  high:     { bg: '#fff7e6', border: '#ffd591', text: '#d46b08', label: 'Alto',     dot: '#fa8c16' },
  medium:   { bg: '#fffbe6', border: '#ffe58f', text: '#ad6800', label: 'Medio',    dot: '#faad14' },
  low:      { bg: '#f6ffed', border: '#b7eb8f', text: '#389e0d', label: 'Bajo',     dot: '#52c41a' },
  info:     { bg: '#f5f5f5', border: '#d9d9d9', text: '#595959', label: 'Info',     dot: '#8c8c8c' },
}

const RISK_COLORS = {
  Crítico:   '#cf1322',
  Alto:      '#d46b08',
  Moderado:  '#ad6800',
  Bajo:      '#389e0d',
}

function ScoreGauge({ score, riskLevel, riskColor }) {
  const pct = score / 100
  const r = 64, cx = 84, cy = 84
  const x = cx + r * Math.cos(Math.PI + pct * Math.PI)
  const y = cy + r * Math.sin(Math.PI + pct * Math.PI)
  const largeArc = pct > 0.5 ? 1 : 0
  const pathBg = `M ${cx - r} ${cy} A ${r} ${r} 0 1 1 ${cx + r} ${cy}`
  const pathFg = `M ${cx - r} ${cy} A ${r} ${r} 0 ${largeArc} 1 ${x} ${y}`

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <svg width={168} height={100} viewBox="0 0 168 100">
        <path d={pathBg} fill="none" stroke="#e8e8e8" strokeWidth={12} strokeLinecap="round" />
        {score > 0 && (
          <path d={pathFg} fill="none" stroke={riskColor} strokeWidth={12} strokeLinecap="round" />
        )}
        <text x={cx} y={cy - 4} textAnchor="middle" fill="#1a1a1a"
          style={{ fontSize: 36, fontWeight: 700, fontFamily: 'IBM Plex Mono, monospace' }}>
          {score}
        </text>
        <text x={cx} y={cy + 15} textAnchor="middle" fill="#8c8c8c"
          style={{ fontSize: 12, fontFamily: 'IBM Plex Mono, monospace' }}>
          / 100
        </text>
      </svg>
      <span style={{ fontSize: 15, fontWeight: 700, color: riskColor }}>
        Riesgo {riskLevel}
      </span>
    </div>
  )
}

function CategoryBar({ label, score, max }) {
  const pct = Math.round((score / max) * 100)
  const color = pct >= 75 ? '#52c41a' : pct >= 50 ? '#faad14' : pct >= 25 ? '#fa8c16' : '#f5222d'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
        <span style={{ color: '#374151' }}>{label}</span>
        <span style={{ color: '#111827', fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace" }}>
          {score}<span style={{ color: '#9ca3af', fontWeight: 400 }}>/{max}</span>
        </span>
      </div>
      <div style={{ background: '#e5e7eb', borderRadius: 4, height: 7, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 4, transition: 'width 0.9s ease' }} />
      </div>
    </div>
  )
}

function FindingCard({ finding }) {
  const [open, setOpen] = useState(false)
  const s = SEV[finding.severity] || SEV.info

  return (
    <div style={{ border: `1px solid ${open ? s.border : '#e5e7eb'}`, borderRadius: 8,
      overflow: 'hidden', transition: 'border-color 0.15s', background: '#fff' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 10,
          padding: '11px 16px', background: open ? s.bg : '#fff',
          border: 'none', cursor: 'pointer', textAlign: 'left', transition: 'background 0.15s' }}
      >
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: s.dot, flexShrink: 0 }} />
        <span style={{ fontSize: 11, fontWeight: 700, color: s.text, background: s.bg,
          border: `1px solid ${s.border}`, padding: '1px 8px', borderRadius: 4,
          whiteSpace: 'nowrap', letterSpacing: '0.03em', flexShrink: 0 }}>
          {s.label}
        </span>
        <span style={{ flex: 1, fontSize: 13.5, color: '#1f2937', fontWeight: 500 }}>
          {finding.title}
        </span>
        <span style={{ fontSize: 11, color: '#9ca3af', flexShrink: 0 }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div style={{ padding: '12px 18px 14px', background: s.bg,
          borderTop: `1px solid ${s.border}` }}>
          {finding.detail && (
            <p style={{ fontSize: 13, color: '#374151', margin: '0 0 10px', lineHeight: 1.7 }}>
              {finding.detail}
            </p>
          )}
          {finding.recommendation && (
            <p style={{ fontSize: 13, color: '#1d4ed8', margin: 0, lineHeight: 1.7 }}>
              → {finding.recommendation}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function printReport(domain, results) {
  const score = results.score
  const findings = score.findings
  const date = new Date().toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' })
  const sevBadge = s => ({
    critical: 'background:#f5222d;color:#fff',
    high:     'background:#fa8c16;color:#fff',
    medium:   'background:#faad14;color:#fff',
    low:      'background:#52c41a;color:#fff',
    info:     'background:#8c8c8c;color:#fff',
  }[s] || '')
  const findingsHtml = findings.map(f => `
    <div style="border:1px solid #e5e7eb;border-radius:4px;margin-bottom:8px;padding:12px">
      <span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:3px;${sevBadge(f.severity)}">${SEV[f.severity]?.label || f.severity}</span>
      <strong style="margin-left:10px;font-size:13px">${f.title}</strong>
      ${f.detail ? `<p style="margin:8px 0 4px;font-size:12px;color:#555">${f.detail}</p>` : ''}
      ${f.recommendation ? `<p style="margin:0;font-size:12px;color:#1d4ed8">→ ${f.recommendation}</p>` : ''}
    </div>`).join('')
  const cats = score.categories
  const catHtml = Object.values(cats).map(c =>
    `<tr><td>${c.label}</td><td><strong>${c.score}/${c.max}</strong></td><td>${Math.round(c.score/c.max*100)}%</td></tr>`
  ).join('')
  const win = window.open('', '_blank')
  win.document.write(`<!DOCTYPE html><html><head><title>Shadow AI Diagnostic — ${domain}</title>
    <style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:800px;margin:0 auto;padding:40px;color:#222}
    h1{font-size:24px;margin-bottom:4px}h2{font-size:16px;margin:28px 0 12px;color:#333;border-bottom:2px solid #eee;padding-bottom:6px}
    table{width:100%;border-collapse:collapse;margin-bottom:16px}td,th{text-align:left;padding:8px 12px;border-bottom:1px solid #eee}
    .score{font-size:64px;font-weight:700;color:${score.risk_color};line-height:1}
    .risk{font-size:18px;color:${score.risk_color};font-weight:600;margin-top:4px}
    .narrative{background:#f9fafb;border-left:3px solid ${score.risk_color};padding:18px;border-radius:4px;font-size:14px;line-height:1.8;color:#374151}
    .upsell{background:#eff6ff;border:1px solid #93c5fd;border-radius:6px;padding:16px;margin-top:32px;font-size:13px}
    @media print{.no-print{display:none}}</style></head><body>
    <p style="font-size:12px;color:#9ca3af;margin-bottom:4px">RosmarOps — Shadow AI Diagnostic · ${date}</p>
    <h1>Informe de diagnóstico: ${domain}</h1>
    <div style="display:flex;align-items:flex-end;gap:24px;margin:24px 0">
      <div><div class="score">${score.total}</div><div class="risk">Riesgo ${score.risk_level}</div></div>
      <table style="max-width:320px"><thead><tr><th>Categoría</th><th>Puntos</th><th>%</th></tr></thead>
      <tbody>${catHtml}</tbody></table>
    </div>
    <h2>Diagnóstico</h2><div class="narrative">${results.narrative.replace(/\n/g, '<br>')}</div>
    <h2>Hallazgos (${findings.length})</h2>${findingsHtml}
    <div class="upsell"><strong>¿Quieres el diagnóstico completo?</strong><br>
    El análisis automatizado cubre la superficie pública. El diagnóstico completo incluye un cuestionario de uso interno de IA, revisión de proveedores y un informe de recomendaciones priorizado.<br>
    <strong>→ <a href="https://rosmarops.com/contacto">Agenda una revisión gratuita de 30 min</a></strong></div>
  </body></html>`)
  win.document.close()
  setTimeout(() => win.print(), 500)
}

export default function ShadowAIDiagnostic() {
  const [domain, setDomain] = useState('')
  const [status, setStatus] = useState('idle')
  const [currentCheck, setCurrentCheck] = useState('')
  const [doneChecks, setDoneChecks] = useState([])
  const [results, setResults] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const inputRef = useRef(null)

  async function analyze() {
    const d = domain.trim().replace(/^https?:\/\//, '').split('/')[0]
    if (!d || !d.includes('.')) return alert('Introduce un dominio válido (ej: empresa.com)')
    setStatus('analyzing')
    setDoneChecks([])
    setResults(null)
    setErrorMsg('')
    try {
      const res = await fetch(`${API}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: d }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (!line.trim()) continue
          try {
            const event = JSON.parse(line)
            if (event.type === 'progress') setCurrentCheck(event.label)
            else if (event.type === 'check_done') setDoneChecks(prev => [...prev, event.check])
            else if (event.type === 'result') { setResults(event.data); setStatus('done') }
          } catch (e) {}
        }
      }
    } catch (err) {
      setErrorMsg(err.message)
      setStatus('error')
    }
  }

  const mono = "'IBM Plex Mono','Courier New',monospace"
  const sans = "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"

  return (
    <div style={{ fontFamily: sans, background: '#f3f4f6', color: '#111827', minHeight: '100vh' }}>

      {/* Header — oscuro, branding RosmarOps */}
      <header style={{ background: '#0d1117', borderBottom: '1px solid #21262d',
        padding: '15px 32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, maxWidth: 860, margin: '0 auto' }}>
          <span style={{ fontSize: 18, fontWeight: 700, color: '#539bf5', fontFamily: mono }}>⬡ RosmarOps</span>
          <span style={{ fontSize: 11, color: '#768390', letterSpacing: '0.14em',
            textTransform: 'uppercase', borderLeft: '1px solid #373e47', paddingLeft: 14,
            fontFamily: mono }}>
            Shadow AI Diagnostic
          </span>
        </div>
      </header>

      <main style={{ maxWidth: 860, margin: '0 auto', padding: '40px 32px' }}>

        {/* Intro — solo en idle */}
        {status === 'idle' && (
          <div style={{ marginBottom: 36 }}>
            <h1 style={{ fontSize: 26, fontWeight: 700, color: '#111827',
              margin: '0 0 12px', lineHeight: 1.3, fontFamily: sans }}>
              ¿Cuánta superficie IA expone tu organización?
            </h1>
            <p style={{ fontSize: 16, color: '#4b5563', margin: '0 0 32px', lineHeight: 1.75, maxWidth: 600 }}>
              Análisis pasivo y automatizado del dominio público: cabeceras de seguridad, protección
              de email, SSL/TLS y detección de asistentes IA embebidos. Resultado en menos de 30 segundos.
            </p>

            {/* Bloque explicativo Shadow AI */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 32, maxWidth: 760 }}>

              <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
                padding: '20px 22px', boxShadow: '0 1px 3px rgba(0,0,0,0.06)', gridColumn: '1 / -1' }}>
                <p style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase',
                  letterSpacing: '0.1em', margin: '0 0 10px', fontWeight: 600 }}>
                  Qué es Shadow AI
                </p>
                <p style={{ fontSize: 14, color: '#1f2937', lineHeight: 1.8, margin: '0 0 10px' }}>
                  Shadow AI es el uso de herramientas de inteligencia artificial —ChatGPT, Copilot, Gemini,
                  asistentes embebidos en SaaS— por parte de empleados sin que el equipo de IT o seguridad
                  tenga conocimiento ni control sobre ello. No es un fenómeno marginal: según estudios recientes,
                  más del 60% de los trabajadores del conocimiento usan IA generativa en su trabajo diario,
                  y la mayoría lo hace con herramientas no aprobadas por su organización.
                </p>
                <p style={{ fontSize: 14, color: '#1f2937', lineHeight: 1.8, margin: 0 }}>
                  El riesgo no es la IA en sí, sino la ausencia de visibilidad. Datos sensibles de clientes,
                  documentos internos o fragmentos de código propietario pueden estar fluyendo hacia modelos
                  externos sin que ningún sistema de seguridad lo registre ni lo bloquee.
                </p>
              </div>

              {[
                {
                  icon: '🔍',
                  title: 'Exposición sin rastro',
                  text: 'Los empleados pegan contenido confidencial en chatbots públicos. Los proveedores pueden usar esas conversaciones para entrenar modelos. Ningún DLP tradicional lo detecta.',
                },
                {
                  icon: '🪝',
                  title: 'Superficie de ataque ampliada',
                  text: 'Los asistentes IA embebidos en el sitio web son vectores de prompt injection y data leakage. Un widget mal configurado puede revelar instrucciones del sistema o datos internos.',
                },
                {
                  icon: '📋',
                  title: 'Cumplimiento en riesgo',
                  text: 'GDPR, ISO 27001 y NIS2 exigen control sobre los flujos de datos personales. El uso no auditado de IA externa puede generar incumplimientos sin que nadie en la organización lo sepa.',
                },
                {
                  icon: '🛡️',
                  title: 'Qué analiza esta herramienta',
                  text: 'Cabeceras HTTP de seguridad, protección del dominio de email (SPF/DMARC), configuración SSL/TLS y detección pasiva de asistentes IA embebidos en la capa pública del sitio.',
                },
              ].map(({ icon, title, text }) => (
                <div key={title} style={{ background: '#fff', border: '1px solid #e5e7eb',
                  borderRadius: 10, padding: '18px 20px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
                  <p style={{ fontSize: 20, margin: '0 0 8px' }}>{icon}</p>
                  <p style={{ fontSize: 13, fontWeight: 600, color: '#111827', margin: '0 0 6px' }}>{title}</p>
                  <p style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.7, margin: 0 }}>{text}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        {status !== 'done' && (
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
            padding: '24px 28px', marginBottom: 24, maxWidth: 540,
            boxShadow: '0 1px 3px rgba(0,0,0,0.07)' }}>
            <label style={{ display: 'block', fontSize: 13, color: '#374151',
              fontWeight: 600, marginBottom: 8 }}>
              Dominio a analizar
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                ref={inputRef}
                style={{ flex: 1, background: '#f9fafb', border: '1px solid #d1d5db',
                  color: '#111827', padding: '10px 14px', borderRadius: 6,
                  fontSize: 15, fontFamily: mono, outline: 'none',
                  transition: 'border-color 0.15s, box-shadow 0.15s' }}
                placeholder="empresa.com"
                value={domain}
                onChange={e => setDomain(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && status === 'idle' && analyze()}
                onFocus={e => { e.target.style.borderColor = '#3b82f6'; e.target.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.15)' }}
                onBlur={e => { e.target.style.borderColor = '#d1d5db'; e.target.style.boxShadow = 'none' }}
                disabled={status === 'analyzing'}
              />
              <button
                onClick={analyze}
                disabled={status === 'analyzing'}
                style={{ padding: '10px 22px', borderRadius: 6, fontSize: 14, fontWeight: 600,
                  fontFamily: sans, border: 'none', cursor: 'pointer',
                  background: status === 'analyzing' ? '#e5e7eb' : '#16a34a',
                  color: status === 'analyzing' ? '#9ca3af' : '#fff',
                  whiteSpace: 'nowrap', transition: 'background 0.15s' }}
              >
                {status === 'analyzing' ? '⏳ Analizando...' : '⚡ Analizar'}
              </button>
            </div>
            <p style={{ fontSize: 12, color: '#9ca3af', margin: '8px 0 0' }}>
              Solo reconocimiento pasivo. No se envía tráfico activo ni intrusivo al dominio.
            </p>
          </div>
        )}

        {/* Progress */}
        {status === 'analyzing' && (
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
            padding: '20px 24px', marginBottom: 24, maxWidth: 440,
            boxShadow: '0 1px 3px rgba(0,0,0,0.07)' }}>
            {CHECKS.map(c => {
              const done = doneChecks.includes(c.id)
              const active = !done && currentCheck &&
                CHECKS.find(ch => currentCheck.includes(ch.label))?.id === c.id
              return (
                <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 10,
                  padding: '7px 0', opacity: done ? 1 : active ? 1 : 0.35,
                  transition: 'opacity 0.3s' }}>
                  <span style={{ fontSize: 14, color: done ? '#16a34a' : active ? '#2563eb' : '#9ca3af',
                    minWidth: 18, textAlign: 'center' }}>
                    {done ? '✓' : active ? '◌' : '○'}
                  </span>
                  <span style={{ fontSize: 13, color: done ? '#111827' : active ? '#1d4ed8' : '#6b7280' }}>
                    {c.icon} {c.label}
                  </span>
                </div>
              )
            })}
            {currentCheck && (
              <p style={{ fontSize: 12, color: '#6b7280', margin: '12px 0 0',
                borderTop: '1px solid #f3f4f6', paddingTop: 10 }}>
                {currentCheck}
              </p>
            )}
          </div>
        )}

        {/* Error */}
        {status === 'error' && (
          <div style={{ background: '#fff1f0', border: '1px solid #ffa39e', color: '#cf1322',
            padding: '12px 16px', borderRadius: 8, fontSize: 13, marginBottom: 24, maxWidth: 500 }}>
            ❌ {errorMsg}
            <button onClick={() => setStatus('idle')}
              style={{ marginLeft: 16, background: 'none', border: 'none', color: '#cf1322',
                fontSize: 12, cursor: 'pointer', textDecoration: 'underline' }}>
              Reintentar
            </button>
          </div>
        )}

        {/* Results */}
        {status === 'done' && results && (() => {
          const sc = results.score
          return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>

              {/* Fila superior */}
              <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 16, alignItems: 'start' }}>

                {/* Score */}
                <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
                  padding: '24px 28px', display: 'flex', flexDirection: 'column',
                  alignItems: 'center', gap: 6,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.07)' }}>
                  <ScoreGauge score={sc.total} riskLevel={sc.risk_level} riskColor={sc.risk_color} />
                  <span style={{ fontSize: 12, color: '#9ca3af', fontFamily: mono }}>{results.domain}</span>
                </div>

                {/* Categorías + acciones */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
                    padding: '18px 22px', boxShadow: '0 1px 3px rgba(0,0,0,0.07)' }}>
                    <p style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase',
                      letterSpacing: '0.1em', margin: '0 0 14px', fontWeight: 600 }}>
                      Por categoría
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 13 }}>
                      {Object.values(sc.categories).map(cat => (
                        <CategoryBar key={cat.label} label={cat.label} score={cat.score} max={cat.max} />
                      ))}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      onClick={() => { setStatus('idle'); setDomain(''); setResults(null) }}
                      style={{ flex: 1, padding: '9px 14px', borderRadius: 6, fontSize: 13,
                        fontWeight: 500, border: '1px solid #d1d5db', background: '#fff',
                        color: '#374151', cursor: 'pointer' }}>
                      ↩ Nuevo análisis
                    </button>
                    <button
                      onClick={() => printReport(results.domain, results)}
                      style={{ flex: 2, padding: '9px 14px', borderRadius: 6, fontSize: 13,
                        fontWeight: 600, border: 'none', background: '#2563eb',
                        color: '#fff', cursor: 'pointer' }}>
                      📄 Exportar informe
                    </button>
                  </div>
                </div>
              </div>

              {/* Narrativa */}
              {results.narrative && (
                <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
                  padding: '22px 28px', boxShadow: '0 1px 3px rgba(0,0,0,0.07)' }}>
                  <p style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase',
                    letterSpacing: '0.1em', margin: '0 0 14px', fontWeight: 600 }}>
                    🧠 Diagnóstico
                  </p>
                  <div style={{ fontSize: 15, color: '#1f2937', lineHeight: 1.8 }}>
                    {results.narrative.split('\n').filter(Boolean).map((p, i) => (
                      <p key={i} style={{ margin: '0 0 14px' }}>{p}</p>
                    ))}
                  </div>
                </div>
              )}

              {/* Hallazgos */}
              {sc.findings.length > 0 && (
                <div>
                  <p style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase',
                    letterSpacing: '0.1em', margin: '0 0 10px', fontWeight: 600 }}>
                    Hallazgos ({sc.findings.length})
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                    {sc.findings.map((f, i) => (
                      <FindingCard key={i} finding={f} />
                    ))}
                  </div>
                </div>
              )}

              {/* Upsell */}
              <div style={{ background: '#eff6ff', border: '1px solid #93c5fd',
                borderRadius: 10, padding: '20px 24px' }}>
                <p style={{ fontSize: 15, fontWeight: 600, color: '#1e3a5f', margin: '0 0 8px' }}>
                  ¿Quieres el diagnóstico completo?
                </p>
                <p style={{ fontSize: 14, color: '#374151', margin: '0 0 16px', lineHeight: 1.7 }}>
                  Este análisis cubre la superficie pública. El diagnóstico completo incluye un cuestionario
                  de uso interno de IA, revisión de proveedores y un informe de recomendaciones priorizado.
                </p>
                <a href="https://rosmarops.com/contacto" target="_blank" rel="noreferrer"
                  style={{ display: 'inline-block', padding: '9px 20px', borderRadius: 6,
                    fontSize: 14, fontWeight: 600, background: '#1d4ed8',
                    color: '#fff', textDecoration: 'none' }}>
                  Agenda una revisión gratuita de 30 min →
                </a>
              </div>

            </div>
          )
        })()}

      </main>
    </div>
  )
}
