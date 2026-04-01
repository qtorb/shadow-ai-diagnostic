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
  critical: { bg: '#fff1f0', border: '#ffa39e', text: '#cf1322', label: 'Crítico', dot: '#f5222d' },
  high:     { bg: '#fff7e6', border: '#ffd591', text: '#d46b08', label: 'Alto',    dot: '#fa8c16' },
  medium:   { bg: '#fffbe6', border: '#ffe58f', text: '#ad6800', label: 'Medio',   dot: '#faad14' },
  low:      { bg: '#f6ffed', border: '#b7eb8f', text: '#389e0d', label: 'Bajo',    dot: '#52c41a' },
  info:     { bg: '#f5f5f5', border: '#d9d9d9', text: '#595959', label: 'Info',    dot: '#8c8c8c' },
}

const SAMPLE_FINDINGS = [
  { severity: 'high',   title: 'HSTS no configurado',                    detail: 'Sin HSTS los navegadores no fuerzan HTTPS en visitas posteriores, permitiendo ataques de downgrade.', recommendation: 'Añade: Strict-Transport-Security: max-age=31536000; includeSubDomains' },
  { severity: 'high',   title: 'Content-Security-Policy ausente',        detail: 'Sin CSP el sitio no controla qué scripts externos pueden ejecutarse, incluyendo widgets de IA no autorizados.', recommendation: 'Implementa una política CSP que restrinja orígenes de scripts.' },
  { severity: 'medium', title: 'X-Frame-Options no configurado',         detail: 'El sitio puede ser embebido en iframes de terceros.', recommendation: 'X-Frame-Options: DENY o SAMEORIGIN' },
  { severity: 'low',    title: 'Server header revela versión: nginx/1.24', detail: 'El servidor expone su software y versión exacta.', recommendation: 'Configura el servidor para ocultar o generalizar el header Server.' },
]

const SAMPLE_CATEGORIES = [
  { label: 'Cabeceras HTTP',    score: 5,  max: 33 },
  { label: 'Seguridad de email', score: 20, max: 20 },
  { label: 'SSL / TLS',         score: 15, max: 15 },
  { label: 'Superficie IA',     score: 32, max: 32 },
]

// ─── Componentes base ──────────────────────────────────────────────────────

function ScoreGauge({ score, riskLevel, riskColor, size = 'normal' }) {
  const r = size === 'small' ? 44 : 64
  const cx = size === 'small' ? 58 : 84
  const cy = size === 'small' ? 58 : 84
  const w = size === 'small' ? 116 : 168
  const h = size === 'small' ? 70 : 100
  const pct = score / 100
  const x = cx + r * Math.cos(Math.PI + pct * Math.PI)
  const y = cy + r * Math.sin(Math.PI + pct * Math.PI)
  const largeArc = pct > 0.5 ? 1 : 0
  const pathBg = `M ${cx - r} ${cy} A ${r} ${r} 0 1 1 ${cx + r} ${cy}`
  const pathFg = `M ${cx - r} ${cy} A ${r} ${r} 0 ${largeArc} 1 ${x} ${y}`
  const fsScore = size === 'small' ? 26 : 36
  const fsSub = size === 'small' ? 10 : 12
  const fsSubY = size === 'small' ? 12 : 17

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
        <path d={pathBg} fill="none" stroke="#e8e8e8" strokeWidth={size === 'small' ? 9 : 12} strokeLinecap="round" />
        {score > 0 && (
          <path d={pathFg} fill="none" stroke={riskColor} strokeWidth={size === 'small' ? 9 : 12} strokeLinecap="round" />
        )}
        <text x={cx} y={cy - 4} textAnchor="middle" fill="#1a1a1a"
          style={{ fontSize: fsScore, fontWeight: 700, fontFamily: 'IBM Plex Mono, monospace' }}>
          {score}
        </text>
        <text x={cx} y={cy + fsSubY} textAnchor="middle" fill="#8c8c8c"
          style={{ fontSize: fsSub, fontFamily: 'IBM Plex Mono, monospace' }}>
          / 100
        </text>
      </svg>
      <span style={{ fontSize: size === 'small' ? 12 : 15, fontWeight: 700, color: riskColor }}>
        Riesgo {riskLevel}
      </span>
    </div>
  )
}

function CategoryBar({ label, score, max, muted = false }) {
  const pct = Math.round((score / max) * 100)
  const color = muted ? '#d1d5db' : (pct >= 75 ? '#52c41a' : pct >= 50 ? '#faad14' : pct >= 25 ? '#fa8c16' : '#f5222d')
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
        <span style={{ color: muted ? '#9ca3af' : '#374151' }}>{label}</span>
        <span style={{ color: muted ? '#9ca3af' : '#111827', fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace" }}>
          {score}<span style={{ color: '#9ca3af', fontWeight: 400 }}>/{max}</span>
        </span>
      </div>
      <div style={{ background: '#e5e7eb', borderRadius: 4, height: 6, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 4, transition: 'width 0.9s ease' }} />
      </div>
    </div>
  )
}

function FindingCard({ finding, muted = false }) {
  const [open, setOpen] = useState(false)
  const s = SEV[finding.severity] || SEV.info

  return (
    <div style={{ border: `1px solid ${open ? s.border : '#e5e7eb'}`, borderRadius: 7,
      overflow: 'hidden', transition: 'border-color 0.15s',
      background: muted ? '#f9fafb' : '#fff',
      opacity: muted ? 0.75 : 1 }}>
      <button
        onClick={() => !muted && setOpen(o => !o)}
        style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 15px', background: open ? s.bg : 'transparent',
          border: 'none', cursor: muted ? 'default' : 'pointer', textAlign: 'left' }}
      >
        <span style={{ width: 7, height: 7, borderRadius: '50%',
          background: muted ? '#d1d5db' : s.dot, flexShrink: 0 }} />
        <span style={{ fontSize: 11, fontWeight: 700,
          color: muted ? '#9ca3af' : '#fff',
          background: muted ? '#e5e7eb' : s.border,
          padding: '1px 7px', borderRadius: 3,
          whiteSpace: 'nowrap', flexShrink: 0 }}>
          {s.label}
        </span>
        <span style={{ flex: 1, fontSize: 13, color: muted ? '#6b7280' : '#1f2937', fontWeight: 500 }}>
          {finding.title}
        </span>
        {!muted && <span style={{ fontSize: 11, color: '#9ca3af', flexShrink: 0 }}>{open ? '▲' : '▼'}</span>}
      </button>
      {open && !muted && (
        <div style={{ padding: '11px 16px 13px', background: s.bg, borderTop: `1px solid ${s.border}` }}>
          {finding.detail && (
            <p style={{ fontSize: 13, color: '#374151', margin: '0 0 9px', lineHeight: 1.65 }}>{finding.detail}</p>
          )}
          {finding.recommendation && (
            <p style={{ fontSize: 13, color: '#1d4ed8', margin: 0, lineHeight: 1.65 }}>→ {finding.recommendation}</p>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Preview estático del output ──────────────────────────────────────────

function SamplePreview() {
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12,
      padding: '28px 32px', boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
      position: 'relative', overflow: 'hidden' }}>

      {/* Badge "Ejemplo de informe" */}
      <div style={{ position: 'absolute', top: 16, right: 16,
        background: '#f0f4ff', border: '1px solid #c7d7fe',
        color: '#4361ee', fontSize: 11, fontWeight: 600,
        padding: '3px 10px', borderRadius: 20, letterSpacing: '0.04em' }}>
        EJEMPLO DE INFORME
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 20, marginBottom: 20 }}>
        <ScoreGauge score={72} riskLevel="Moderado" riskColor="#d46b08" size="small" />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 9, justifyContent: 'center' }}>
          {SAMPLE_CATEGORIES.map(c => (
            <CategoryBar key={c.label} label={c.label} score={c.score} max={c.max} muted={false} />
          ))}
        </div>
      </div>

      {/* Resumen ejecutivo de muestra */}
      <div style={{ background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 7,
        padding: '10px 14px', marginBottom: 14, fontSize: 13, color: '#7c5200', lineHeight: 1.6 }}>
        <strong>4 hallazgos detectados</strong> — 2 de severidad Alta, 1 Media, 1 Baja.
        Prioridad: implementar HSTS y Content-Security-Policy.
      </div>

      {/* Hallazgos de muestra — los dos primeros visibles, el resto desenfocados */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        {SAMPLE_FINDINGS.slice(0, 2).map((f, i) => (
          <FindingCard key={i} finding={f} />
        ))}
        <div style={{ filter: 'blur(3px)', pointerEvents: 'none', userSelect: 'none' }}>
          {SAMPLE_FINDINGS.slice(2).map((f, i) => (
            <div key={i} style={{ marginTop: 5 }}>
              <FindingCard finding={f} muted />
            </div>
          ))}
        </div>
      </div>

      {/* Overlay de "Analiza tu dominio" */}
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 90,
        background: 'linear-gradient(transparent, rgba(255,255,255,0.97))',
        display: 'flex', alignItems: 'flex-end', justifyContent: 'center', paddingBottom: 16 }}>
        <span style={{ fontSize: 13, color: '#6b7280', fontStyle: 'italic' }}>
          Analiza tu dominio para ver tu informe real →
        </span>
      </div>
    </div>
  )
}

// ─── Resumen ejecutivo (resultados reales) ─────────────────────────────────

function ExecutiveSummary({ findings, riskLevel, riskColor }) {
  const counts = { critical: 0, high: 0, medium: 0, low: 0 }
  findings.forEach(f => { if (counts[f.severity] !== undefined) counts[f.severity]++ })

  const topFindings = findings
    .filter(f => f.severity === 'critical' || f.severity === 'high')
    .slice(0, 2)
    .map(f => f.title)

  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  const urgent = counts.critical + counts.high

  const bgColor = riskLevel === 'Crítico' ? '#fff1f0' :
                  riskLevel === 'Alto'    ? '#fff7e6' :
                  riskLevel === 'Moderado'? '#fffbe6' : '#f6ffed'
  const bdColor = riskLevel === 'Crítico' ? '#ffa39e' :
                  riskLevel === 'Alto'    ? '#ffd591' :
                  riskLevel === 'Moderado'? '#ffe58f' : '#b7eb8f'

  return (
    <div style={{ background: bgColor, border: `1px solid ${bdColor}`,
      borderLeft: `4px solid ${riskColor}`, borderRadius: 8,
      padding: '14px 18px', marginBottom: 4 }}>
      <p style={{ fontSize: 14, fontWeight: 600, color: '#1f2937', margin: '0 0 5px' }}>
        {total} {total === 1 ? 'hallazgo detectado' : 'hallazgos detectados'} — Riesgo {riskLevel}
      </p>
      <p style={{ fontSize: 13, color: '#374151', margin: 0, lineHeight: 1.65 }}>
        {urgent > 0
          ? <>Atención prioritaria: <strong>{topFindings.join(' y ')}</strong>. {counts.medium > 0 ? `${counts.medium} hallazgo${counts.medium > 1 ? 's' : ''} de severidad Media requieren revisión.` : ''}</>
          : 'No se detectaron hallazgos críticos ni altos. Revisa los hallazgos de severidad Media y Baja para mejorar la postura de seguridad.'
        }
      </p>
    </div>
  )
}

// ─── Print / export ────────────────────────────────────────────────────────

function printReport(domain, results) {
  const score = results.score
  const findings = score.findings
  const date = new Date().toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' })
  const sevBadge = s => ({ critical:'background:#f5222d;color:#fff', high:'background:#fa8c16;color:#fff', medium:'background:#faad14;color:#fff', low:'background:#52c41a;color:#fff', info:'background:#8c8c8c;color:#fff' }[s] || '')
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
    h1{font-size:22px;margin-bottom:4px}h2{font-size:15px;margin:28px 0 12px;color:#333;border-bottom:2px solid #eee;padding-bottom:6px}
    table{width:100%;border-collapse:collapse;margin-bottom:16px}td,th{text-align:left;padding:8px 12px;border-bottom:1px solid #eee}
    .score{font-size:60px;font-weight:700;color:${score.risk_color};line-height:1}
    .risk{font-size:17px;color:${score.risk_color};font-weight:600;margin-top:4px}
    .narrative{background:#f9fafb;border-left:4px solid ${score.risk_color};padding:18px;border-radius:4px;font-size:14px;line-height:1.8;color:#374151}
    .upsell{background:#eff6ff;border:1px solid #93c5fd;border-radius:6px;padding:16px;margin-top:32px;font-size:13px}
    @media print{.no-print{display:none}}</style></head><body>
    <p style="font-size:11px;color:#9ca3af;margin-bottom:4px">RosmarOps — Shadow AI Diagnostic · ${date}</p>
    <h1>Diagnóstico Shadow AI: ${domain}</h1>
    <div style="display:flex;align-items:flex-end;gap:24px;margin:24px 0">
      <div><div class="score">${score.total}</div><div class="risk">Riesgo ${score.risk_level}</div></div>
      <table style="max-width:320px"><thead><tr><th>Categoría</th><th>Puntos</th><th>%</th></tr></thead>
      <tbody>${catHtml}</tbody></table>
    </div>
    <h2>Diagnóstico</h2><div class="narrative">${results.narrative.replace(/\n/g, '<br>')}</div>
    <h2>Hallazgos (${findings.length})</h2>${findingsHtml}
    <div class="upsell"><strong>¿Diagnóstico completo?</strong><br>
    Cuestionario de IA interna + revisión de proveedores + informe de recomendaciones priorizado.<br>
    <strong>→ <a href="https://rosmarops.com/contacto">Agenda una revisión gratuita de 30 min</a></strong></div>
  </body></html>`)
  win.document.close()
  setTimeout(() => win.print(), 500)
}

// ─── Componente principal ──────────────────────────────────────────────────

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
  const sans = "Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"

  // ─── Render ──────────────────────────────────────────────────────────────
  return (
    <div style={{ fontFamily: sans, background: '#f3f4f6', color: '#111827', minHeight: '100vh' }}>

      {/* Header */}
      <header style={{ background: '#0d1117', borderBottom: '1px solid #21262d', padding: '14px 32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, maxWidth: 860, margin: '0 auto' }}>
          <span style={{ fontSize: 17, fontWeight: 700, color: '#539bf5', fontFamily: mono }}>⬡ RosmarOps</span>
          <span style={{ fontSize: 11, color: '#768390', letterSpacing: '0.14em', textTransform: 'uppercase',
            borderLeft: '1px solid #373e47', paddingLeft: 14, fontFamily: mono }}>
            Shadow AI Diagnostic
          </span>
        </div>
      </header>

      <main style={{ maxWidth: 860, margin: '0 auto', padding: '0 32px 60px' }}>

        {/* ── HERO ── */}
        <div style={{ background: '#fff', borderRadius: '0 0 16px 16px',
          padding: '44px 48px 40px', marginBottom: 28,
          boxShadow: '0 4px 20px rgba(0,0,0,0.07)',
          borderTop: '3px solid #2563eb' }}>

          {/* Titular */}
          <h1 style={{ fontSize: 28, fontWeight: 700, color: '#0f172a',
            margin: '0 0 12px', lineHeight: 1.25, letterSpacing: '-0.02em' }}>
            Tu dominio analizado.<br />
            <span style={{ color: '#2563eb' }}>Tu exposición a Shadow AI, en claro.</span>
          </h1>

          {/* Subtítulo */}
          <p style={{ fontSize: 16, color: '#475569', margin: '0 0 24px',
            lineHeight: 1.7, maxWidth: 580 }}>
            Análisis pasivo y automatizado en menos de 30 segundos. Sin acceso a sistemas internos.
            Sin tráfico intrusivo. Solo superficie pública.
          </p>

          {/* 3 beneficios */}
          <div style={{ display: 'flex', gap: 20, marginBottom: 28, flexWrap: 'wrap' }}>
            {[
              { icon: '⚡', title: 'Resultado inmediato', sub: 'Sin instalación ni registro' },
              { icon: '🛡️', title: '100% pasivo',         sub: 'Sin tocar tu servidor' },
              { icon: '📄', title: 'Informe descargable', sub: 'Con recomendaciones' },
            ].map(b => (
              <div key={b.title} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 20 }}>{b.icon}</span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#1e293b' }}>{b.title}</div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>{b.sub}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Formulario prominente */}
          <div style={{ display: 'flex', gap: 10, maxWidth: 520, marginBottom: 16 }}>
            <input
              ref={inputRef}
              style={{ flex: 1, background: '#f8fafc', border: '1.5px solid #cbd5e1',
                color: '#0f172a', padding: '12px 16px', borderRadius: 8,
                fontSize: 15, fontFamily: mono, outline: 'none',
                transition: 'border-color 0.15s, box-shadow 0.15s',
                boxSizing: 'border-box' }}
              placeholder="empresa.com"
              value={domain}
              onChange={e => setDomain(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && status !== 'analyzing' && analyze()}
              onFocus={e => { e.target.style.borderColor = '#2563eb'; e.target.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.12)' }}
              onBlur={e => { e.target.style.borderColor = '#cbd5e1'; e.target.style.boxShadow = 'none' }}
              disabled={status === 'analyzing'}
            />
            <button
              onClick={analyze}
              disabled={status === 'analyzing'}
              style={{ padding: '12px 26px', borderRadius: 8, fontSize: 14, fontWeight: 600,
                fontFamily: sans, border: 'none', cursor: 'pointer', whiteSpace: 'nowrap',
                background: status === 'analyzing' ? '#e2e8f0' : '#2563eb',
                color: status === 'analyzing' ? '#94a3b8' : '#fff',
                boxShadow: status === 'analyzing' ? 'none' : '0 2px 8px rgba(37,99,235,0.3)',
                transition: 'all 0.15s' }}
            >
              {status === 'analyzing' ? '⏳ Analizando...' : 'Analizar mi dominio →'}
            </button>
          </div>

          {/* Trust signals */}
          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            {[
              '✓ Solo lectura de superficie pública',
              '✓ Sin autenticación ni credenciales',
              '✓ Sin tráfico activo al servidor',
              '✓ Sin acceso a sistemas internos',
            ].map(t => (
              <span key={t} style={{ fontSize: 12, color: '#64748b', display: 'flex', alignItems: 'center', gap: 4 }}>
                {t}
              </span>
            ))}
          </div>
        </div>

        {/* ── PROGRESS ── */}
        {status === 'analyzing' && (
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
            padding: '20px 24px', marginBottom: 24, maxWidth: 440,
            boxShadow: '0 1px 4px rgba(0,0,0,0.07)' }}>
            {CHECKS.map(c => {
              const done = doneChecks.includes(c.id)
              const active = !done && currentCheck && CHECKS.find(ch => currentCheck.includes(ch.label))?.id === c.id
              return (
                <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 10,
                  padding: '7px 0', opacity: done ? 1 : active ? 1 : 0.32, transition: 'opacity 0.3s' }}>
                  <span style={{ fontSize: 13, color: done ? '#16a34a' : active ? '#2563eb' : '#9ca3af', minWidth: 18 }}>
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

        {/* ── ERROR ── */}
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

        {/* ── RESULTADOS ── */}
        {status === 'done' && results && (() => {
          const sc = results.score
          return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

              {/* Score + categorías + acciones */}
              <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 16, alignItems: 'start' }}>
                <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
                  padding: '24px 28px', display: 'flex', flexDirection: 'column',
                  alignItems: 'center', gap: 6, boxShadow: '0 1px 4px rgba(0,0,0,0.07)' }}>
                  <ScoreGauge score={sc.total} riskLevel={sc.risk_level} riskColor={sc.risk_color} />
                  <span style={{ fontSize: 12, color: '#9ca3af', fontFamily: mono, marginTop: 2 }}>{results.domain}</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
                    padding: '18px 22px', boxShadow: '0 1px 4px rgba(0,0,0,0.07)' }}>
                    <p style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase',
                      letterSpacing: '0.1em', margin: '0 0 14px', fontWeight: 600 }}>
                      Por categoría
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {Object.values(sc.categories).map(cat => (
                        <CategoryBar key={cat.label} label={cat.label} score={cat.score} max={cat.max} />
                      ))}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      onClick={() => { setStatus('idle'); setDomain(''); setResults(null) }}
                      style={{ flex: 1, padding: '9px 14px', borderRadius: 7, fontSize: 13,
                        fontWeight: 500, border: '1px solid #d1d5db', background: '#fff',
                        color: '#374151', cursor: 'pointer' }}>
                      ↩ Nuevo análisis
                    </button>
                    <button
                      onClick={() => printReport(results.domain, results)}
                      style={{ flex: 2, padding: '9px 14px', borderRadius: 7, fontSize: 13,
                        fontWeight: 600, border: 'none', background: '#2563eb',
                        color: '#fff', cursor: 'pointer',
                        boxShadow: '0 2px 8px rgba(37,99,235,0.25)' }}>
                      📄 Exportar informe
                    </button>
                  </div>
                </div>
              </div>

              {/* ── RESUMEN EJECUTIVO (quick win 4) ── */}
              <ExecutiveSummary
                findings={sc.findings}
                riskLevel={sc.risk_level}
                riskColor={sc.risk_color}
              />

              {/* Narrativa */}
              {results.narrative && (
                <div style={{ background: '#fff', borderRadius: 10,
                  borderLeft: `4px solid ${sc.risk_color}`,
                  border: `1px solid #e5e7eb`,
                  borderLeftWidth: 4, borderLeftColor: sc.risk_color,
                  padding: '22px 28px', boxShadow: '0 1px 4px rgba(0,0,0,0.07)' }}>
                  <p style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase',
                    letterSpacing: '0.1em', margin: '0 0 14px', fontWeight: 600 }}>
                    🧠 Diagnóstico
                  </p>
                  <div style={{ fontSize: 15, color: '#1f2937', lineHeight: 1.85 }}>
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
                    {sc.findings.map((f, i) => <FindingCard key={i} finding={f} />)}
                  </div>
                </div>
              )}

              {/* Upsell */}
              <div style={{ background: '#fff', border: '1px solid #bfdbfe',
                borderRadius: 10, padding: '22px 26px',
                boxShadow: '0 1px 4px rgba(0,0,0,0.07)' }}>
                <p style={{ fontSize: 15, fontWeight: 700, color: '#1e3a5f', margin: '0 0 6px' }}>
                  ¿Quieres el diagnóstico completo?
                </p>
                <p style={{ fontSize: 13, color: '#475569', margin: '0 0 6px', lineHeight: 1.7 }}>
                  Este análisis cubre la superficie pública. El diagnóstico completo incluye:
                </p>
                <div style={{ display: 'flex', gap: 20, marginBottom: 16, flexWrap: 'wrap' }}>
                  {['Cuestionario de IA interna', 'Revisión de proveedores SaaS', 'Informe de riesgos priorizado', 'Llamada de 30 min'].map(i => (
                    <span key={i} style={{ fontSize: 13, color: '#1d4ed8', display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span style={{ color: '#2563eb' }}>→</span> {i}
                    </span>
                  ))}
                </div>
                <a href="https://rosmarops.com/contacto" target="_blank" rel="noreferrer"
                  style={{ display: 'inline-block', padding: '10px 22px', borderRadius: 7,
                    fontSize: 14, fontWeight: 600, background: '#2563eb', color: '#fff',
                    textDecoration: 'none', boxShadow: '0 2px 8px rgba(37,99,235,0.25)' }}>
                  Agenda una revisión gratuita →
                </a>
              </div>

            </div>
          )
        })()}

        {/* ── CONTENIDO EDUCATIVO (solo en idle/error) ── */}
        {(status === 'idle' || status === 'error') && (
          <>
            {/* Preview del output */}
            <div style={{ marginBottom: 28 }}>
              <p style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase',
                letterSpacing: '0.1em', margin: '0 0 12px', fontWeight: 600 }}>
                Qué obtienes en el informe
              </p>
              <SamplePreview />
            </div>

            {/* 4 áreas de análisis — compactas */}
            <div style={{ marginBottom: 28 }}>
              <p style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase',
                letterSpacing: '0.1em', margin: '0 0 12px', fontWeight: 600 }}>
                Qué analiza esta herramienta
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { icon: '🔒', title: 'Cabeceras HTTP de seguridad', text: 'HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy. Cada header ausente es un vector de exposición.' },
                  { icon: '✉️', title: 'Protección del dominio de email', text: 'SPF, DMARC y su configuración. Un dominio sin estos registros puede ser suplantado para enviar emails fraudulentos.' },
                  { icon: '🔐', title: 'Certificado SSL / TLS',         text: 'Validez, versión de TLS, días hasta expiración y suite de cifrado. TLS 1.0 y 1.1 son obsoletos con vulnerabilidades conocidas.' },
                  { icon: '🤖', title: 'Superficie de IA expuesta',     text: 'Detección pasiva de chatbots, asistentes y endpoints IA embebidos en la capa pública del sitio. Cada widget no auditado es un riesgo.' },
                ].map(({ icon, title, text }) => (
                  <div key={title} style={{ background: '#fff', border: '1px solid #e5e7eb',
                    borderRadius: 10, padding: '18px 20px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                    <p style={{ fontSize: 18, margin: '0 0 8px' }}>{icon}</p>
                    <p style={{ fontSize: 13, fontWeight: 600, color: '#111827', margin: '0 0 6px' }}>{title}</p>
                    <p style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.65, margin: 0 }}>{text}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Qué es Shadow AI — al final, comprimido */}
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
              padding: '22px 26px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <p style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase',
                letterSpacing: '0.1em', margin: '0 0 12px', fontWeight: 600 }}>
                Qué es Shadow AI
              </p>
              <p style={{ fontSize: 14, color: '#1f2937', lineHeight: 1.8, margin: '0 0 10px' }}>
                Shadow AI es el uso de herramientas de inteligencia artificial —ChatGPT, Copilot, Gemini,
                asistentes embebidos en SaaS— por parte de empleados sin que el equipo de IT o seguridad
                tenga conocimiento ni control sobre ello. Más del 60% de los trabajadores del conocimiento
                usan IA generativa en su trabajo diario, y la mayoría lo hace con herramientas no aprobadas.
              </p>
              <p style={{ fontSize: 14, color: '#1f2937', lineHeight: 1.8, margin: 0 }}>
                El riesgo no es la IA en sí, sino la ausencia de visibilidad. Datos sensibles, documentos
                internos o código propietario pueden estar fluyendo hacia modelos externos sin que ningún
                sistema de seguridad lo registre ni lo bloquee.
              </p>
            </div>
          </>
        )}

      </main>
    </div>
  )
}
