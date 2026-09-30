import { useRef, useState } from 'react'
import { clamp01, useScrollFrame, useSite } from '../site'

// Scroll progress at which each of the five steps lights up.
const THRESHOLDS = [0.04, 0.24, 0.44, 0.64, 0.82]

export function Flow() {
  const { t, reduced, mobile } = useSite()
  const ref = useRef<HTMLElement>(null)
  const [progress, setProgress] = useState(0)

  useScrollFrame(() => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const v = clamp01(-r.top / Math.max(1, r.height - window.innerHeight))
    setProgress((p) => (Math.abs(v - p) > 0.005 || ((v === 1 || v === 0) && p !== v) ? v : p))
  })

  // On mobile and with reduced motion the section is a plain static list.
  const staticFlow = reduced || mobile
  const F = staticFlow ? 1 : progress
  const activeN = THRESHOLDS.filter((x) => F >= x).length
  const done = Math.max(0, activeN - 1) / 4

  return (
    <section id="how" ref={ref} className="section alt" style={{ height: staticFlow ? 'auto' : '300vh' }}>
      <div style={{ position: staticFlow ? 'relative' : 'sticky', top: 0, minHeight: staticFlow ? 0 : '100vh', display: 'flex', alignItems: 'center' }}>
        <div className="cols" style={{ maxWidth: 1200, width: '100%', margin: '0 auto', padding: 'clamp(64px,8vw,96px) var(--gutter)', boxSizing: 'border-box', ['--min' as string]: '380px', alignItems: 'start' }}>
          <div>
            <div className="kicker">{t.flow.k}</div>
            <h2 className="h2">{t.flow.title}</h2>
            <p className="lead" style={{ maxWidth: '40ch' }}>{t.flow.body}</p>
            <div className="mono" style={{ marginTop: 28, fontSize: 12, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ flex: '0 0 120px', height: 2, background: 'var(--line3)', position: 'relative', overflow: 'hidden' }}>
                <span style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(activeN / 5) * 100}%`, background: 'var(--ink)' }} />
              </span>
              <span>{Math.max(1, activeN)} / 5 {t.flow.of}</span>
            </div>
          </div>
          <ol style={{ listStyle: 'none', margin: 0, padding: 0, position: 'relative' }}>
            <span aria-hidden="true" style={{ position: 'absolute', left: 13, top: 14, bottom: 14, width: 1, background: 'var(--line3)' }} />
            <span aria-hidden="true" style={{ position: 'absolute', left: 13, top: 14, width: 1, height: `calc(${done * 100}% - ${done * 28}px)`, background: 'var(--ink)', transition: 'height .3s' }} />
            {t.flow.steps.map((st, i) => {
              const on = i < activeN
              return (
                <li key={st.n} style={{ position: 'relative', display: 'grid', gridTemplateColumns: '28px minmax(0,1fr)', gap: 20, padding: '0 0 26px', opacity: on ? 1 : 0.25, transform: on ? 'none' : 'translateY(8px)', transition: 'opacity .45s, transform .45s' }}>
                  <span className="mono" style={{ width: 27, height: 27, borderRadius: 99, border: '1px solid var(--ink)', background: on ? 'var(--ink)' : 'var(--alt)', color: on ? 'var(--bg)' : 'var(--ink)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10.5, position: 'relative', transition: 'background .3s, color .3s' }}>{st.n}</span>
                  <div style={{ paddingTop: 1 }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: '4px 12px' }}>
                      <span className="serif" style={{ fontSize: 25, lineHeight: 1.1 }}>{st.name}</span>
                      <span className="mono" style={{ fontSize: 11.5, color: 'var(--muted)' }}>{st.tech}</span>
                    </div>
                    <p style={{ margin: '6px 0 0', fontSize: 15.5, lineHeight: 1.5, color: '#2E2D28', maxWidth: '46ch' }}>“{st.plain}”</p>
                    {st.branch && <div className="mono" style={{ display: 'inline-block', marginTop: 10, border: '1px dashed var(--dash)', borderRadius: 6, padding: '5px 10px', fontSize: 11.5, color: 'var(--body)' }}>↳ {st.branch}</div>}
                  </div>
                </li>
              )
            })}
          </ol>
        </div>
      </div>
    </section>
  )
}
