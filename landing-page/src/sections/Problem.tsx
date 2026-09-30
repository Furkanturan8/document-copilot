import { useRef, useState } from 'react'
import { FYS, TICKERS } from '../content'
import { clamp01, useScrollFrame, useSite } from '../site'

export function Problem() {
  const { t, reduced } = useSite()
  const ref = useRef<HTMLElement>(null)
  const [progress, setProgress] = useState(0)

  useScrollFrame(() => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const v = clamp01((window.innerHeight * 0.8 - r.top) / (r.height * 0.75))
    setProgress((p) => (Math.abs(v - p) > 0.01 || ((v === 1 || v === 0) && p !== v) ? v : p))
  })

  const P = reduced ? 1 : progress
  const readN = Math.min(25, Math.max(0, Math.floor(((P - 0.05) / 0.5) * 25)))
  const collapsed = P > 0.62

  return (
    <section id="problem" ref={ref} className="section">
      <div className="wrap cols" style={{ ['--min' as string]: '420px', alignItems: 'center' }}>
        <div>
          <div className="kicker">{t.problem.k}</div>
          <h2 className="h2">{t.problem.title}</h2>
          <p className="lead" style={{ maxWidth: '48ch' }}>{t.problem.body}</p>
          <ol style={{ listStyle: 'none', padding: 0, margin: '26px 0 0', maxWidth: 420 }}>
            {t.problem.steps.map((l, i) => (
              <li key={l} style={{ display: 'flex', gap: 16, padding: '11px 0', borderBottom: '1px solid var(--line)', fontSize: 15 }}>
                <span className="mono" style={{ fontSize: 12, color: 'var(--muted)', paddingTop: 2 }}>0{i + 1}</span><span>{l}</span>
              </li>
            ))}
          </ol>
          <blockquote className="serif" style={{ margin: '30px 0 0', fontStyle: 'italic', fontSize: 22, lineHeight: 1.35, maxWidth: '30ch', textWrap: 'pretty' }}>“{t.problem.quote}”</blockquote>
        </div>

        <div>
          <div className="mono" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', fontSize: 12, color: 'var(--muted)', marginBottom: 14 }}>
            <span>5 × 5 = 25 Form 10-K</span>
            <span style={{ color: 'var(--ink)' }}>{readN} / 25 {t.problem.counter}</span>
          </div>
          <div aria-hidden="true" style={{ display: 'grid', gap: 8 }}>
            {TICKERS.map((tk, r) => (
              <div key={tk} style={{ display: 'grid', gridTemplateColumns: '52px repeat(5,minmax(0,1fr))', gap: 8, alignItems: 'center' }}>
                <span className="mono" style={{ fontSize: 11.5 }}>{tk}</span>
                {FYS.map((fy, c) => (
                  <div key={fy} style={{ aspectRatio: '3/3.6', border: '1px solid #D9D8D0', borderRadius: 3, background: r * 5 + c < readN ? '#E9E7DD' : '#fff', opacity: collapsed ? 0.28 : 1, transform: collapsed ? 'scale(.94)' : 'none', transition: 'background .35s, opacity .5s, transform .5s', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: 6 }}>
                    <span style={{ display: 'grid', gap: 3 }}>
                      <span style={{ height: 2, background: '#D9D8D0', width: '80%' }} /><span style={{ height: 2, background: '#D9D8D0', width: '60%' }} /><span style={{ height: 2, background: '#D9D8D0', width: '70%' }} />
                    </span>
                    <span className="mono" style={{ fontSize: 9.5, color: 'var(--muted)' }}>{fy}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
          <div className="card" style={{ marginTop: 22, borderRadius: 14, padding: '20px 22px', boxShadow: '0 20px 50px -34px rgba(22,21,15,.4)', opacity: collapsed ? 1 : 0, transform: collapsed ? 'none' : 'translateY(14px)', transition: 'opacity .6s, transform .6s var(--ease)' }}>
            <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.6 }}>NVIDIA's gross margin increased from 72.7% in fiscal 2024 to 75.0% in fiscal 2025.<sup className="sup">1</sup></p>
            <div className="chip" style={{ marginTop: 12, cursor: 'default', padding: '5px 11px 5px 5px' }}><span className="chip-n">1</span>NVDA · 10-K · 2025-02-26 · p.38</div>
          </div>
          <div className="mono" style={{ marginTop: 12, fontSize: 12, color: 'var(--muted)', opacity: collapsed ? 1 : 0, transition: 'opacity .6s' }}>{t.problem.compress}</div>
        </div>
      </div>
    </section>
  )
}
