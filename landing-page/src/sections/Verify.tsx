import { useRef, useState } from 'react'
import { useScrollFrame, useSite, useTimers } from '../site'

const STEPS = 4

export function Verify() {
  const { t, reduced } = useSite()
  const ref = useRef<HTMLElement>(null)
  const seen = useRef(false)
  const timers = useTimers()
  const [step, setStep] = useState(STEPS + 1)
  const [fail, setFail] = useState(false)

  const run = (withFail: boolean) => {
    timers.reset()
    setFail(withFail)
    if (reduced) { setStep(STEPS + 1); return }
    setStep(0)
    for (let i = 1; i <= STEPS + 1; i++) timers.at(() => setStep(i), 250 + i * 620)
  }

  useScrollFrame(() => {
    const el = ref.current
    if (!el || seen.current || el.getBoundingClientRect().top >= window.innerHeight * 0.55) return
    seen.current = true
    run(false)
  })

  const items = [
    { label: t.verify.i1, detail: '"Gross margin | 75.0% | 72.7% | Up 2.3 pts"' },
    { label: t.verify.i2, detail: '' },
    { label: t.verify.i3, detail: '' },
    { label: fail ? t.verify.i4f : t.verify.i4, detail: fail ? '"…primarily driven by record Gaming demand."' : '"The year over year increase was primarily driven by a higher mix of Data Center revenue."' },
  ]
  const done = step > STEPS
  const withheld = done && fail
  const sentence2 = fail
    ? 'NVIDIA said the year-over-year increase was primarily driven by record Gaming demand.'
    : 'NVIDIA said the year-over-year increase was primarily driven by a higher mix of Data Center revenue.'

  return (
    <section id="verify" ref={ref} className="section alt">
      <div className="wrap cols" style={{ alignItems: 'start' }}>
        <div>
          <div className="kicker">{t.verify.k}</div>
          <h2 className="h2">{t.verify.title}</h2>
          <p className="lead" style={{ maxWidth: '46ch' }}>{t.verify.body}</p>
          <p className="serif" style={{ fontStyle: 'italic', fontSize: 22, margin: '22px 0 0' }}>{t.verify.code}</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 30, alignItems: 'center' }}>
            <div role="group" className="toggle" style={{ borderColor: 'var(--border)', fontSize: 14 }}>
              <button type="button" aria-pressed={!fail} onClick={() => run(false)} style={{ padding: '8px 14px', color: fail ? 'var(--ink)' : undefined }}>{t.verify.real}</button>
              <button type="button" aria-pressed={fail} onClick={() => run(true)} style={{ padding: '8px 14px', color: fail ? undefined : 'var(--ink)' }}>{t.verify.fake}</button>
            </div>
            <button type="button" onClick={() => run(fail)} style={{ border: 0, background: 'transparent', padding: '8px 6px', cursor: 'pointer', fontSize: 14, color: 'var(--body)', textDecoration: 'underline', textUnderlineOffset: 3 }}>↻ {t.verify.again}</button>
          </div>
        </div>

        <div className="card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--line2)', opacity: withheld ? 0.4 : 1, transition: 'opacity .5s' }}>
            <div className="label" style={{ fontSize: 11, marginBottom: 10 }}>{!done ? t.verify.draft : withheld ? t.verify.withheld : t.verify.shown}</div>
            <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, textDecorationLine: withheld ? 'line-through' : 'none', textDecorationThickness: 1 }}>
              NVIDIA's gross margin increased from 72.7% in fiscal 2024 to 75.0% in fiscal 2025, up 2.3 percentage points.<sup className="sup">1</sup> {sentence2}<sup className="sup">2</sup>
            </p>
          </div>
          <ul style={{ listStyle: 'none', margin: 0, padding: '8px 24px' }}>
            {items.map((it, i) => {
              const ok = step > i
              const bad = ok && fail && i === 3
              return (
                <li key={i} style={{ display: 'grid', gridTemplateColumns: '24px minmax(0,1fr)', gap: 14, padding: '14px 0', borderBottom: '1px solid var(--line2)', opacity: ok || step === i ? 1 : 0.4, transition: 'opacity .3s' }}>
                  <span aria-hidden="true" style={{ width: 22, height: 22, borderRadius: 5, border: `1px solid ${ok ? (bad ? 'var(--ink)' : '#E3CF4A') : 'var(--border)'}`, background: bad ? 'var(--ink)' : ok ? 'var(--hl)' : '#fff', color: bad ? 'var(--bg)' : 'var(--ink)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, transition: 'background .25s' }}>{bad ? '✕' : ok ? '✓' : ''}</span>
                  <div>
                    <div style={{ fontSize: 15, textDecorationLine: bad ? 'line-through' : 'none' }}>{it.label}</div>
                    {it.detail && <div className="mono" style={{ marginTop: 4, fontSize: 11.5, color: 'var(--muted)', overflowWrap: 'anywhere' }}>{it.detail}</div>}
                  </div>
                </li>
              )
            })}
          </ul>
          <div aria-live="polite" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '18px 24px', background: done ? 'var(--ink)' : 'var(--alt)', color: done ? 'var(--bg)' : 'var(--body)', transition: 'background .3s, color .3s' }}>
            <span style={{ fontWeight: 500, fontSize: 15 }}>{!done ? t.verify.checking : withheld ? t.verify.withheld : t.verify.shown}</span>
            <span className="mono" style={{ fontSize: 11.5 }}>{!done ? `${Math.min(step, STEPS)} / ${STEPS}` : withheld ? t.verify.oneFail : t.verify.allOk}</span>
          </div>
        </div>
      </div>
    </section>
  )
}
