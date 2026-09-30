import { useEffect, useRef, useState } from 'react'
import { HERO } from '../content'
import { AnswerText, buildSegs, Chip, useScrollFrame, useSite, useTimers } from '../site'

const Q = HERO[0]
const bar = (w: string) => <span style={{ height: 5, borderRadius: 2, background: '#ECEBE4', width: w }} />
const cellBar = (w: string, right = true) => <span style={{ display: 'block', height: 5, width: w, marginLeft: right ? 'auto' : undefined, background: '#ECEBE4', borderRadius: 2 }} />

function FillerRow({ first }: { first: string }) {
  return (
    <tr aria-hidden="true" style={{ borderBottom: '1px solid #ECEBE4' }}>
      <td style={{ padding: '10px 0' }}>{cellBar(first, false)}</td>
      <td style={{ padding: '10px 0 10px 10px' }}>{cellBar('70%')}</td>
      <td style={{ padding: '10px 0 10px 10px' }}>{cellBar('70%')}</td>
      <td style={{ padding: '10px 0 10px 10px' }}>{cellBar('50%')}</td>
    </tr>
  )
}

// True one frame after mount, so a freshly swapped-in passage animates its highlight in.
function useAfterMount() {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const id = requestAnimationFrame(() => requestAnimationFrame(() => setReady(true)))
    return () => cancelAnimationFrame(id)
  }, [])
  return ready
}

function P38Table({ active }: { active: boolean }) {
  const on = useAfterMount() && active
  const hlCell = (text: string, delay: number) => (
    <span className={'hl cell' + (on ? ' on' : '')} style={{ transitionDelay: `${delay}s` }}>{text}</span>
  )
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 22, fontSize: 14.5, fontVariantNumeric: 'tabular-nums' }}>
      <thead>
        <tr style={{ borderBottom: '1px solid var(--ink)' }}>
          <th style={{ padding: '6px 0' }} />
          {['Jan 26, 2025', 'Jan 28, 2024', 'Change'].map((h) => <th key={h} style={{ textAlign: 'right', fontWeight: 500, padding: '6px 0 6px 10px', fontSize: 12 }}>{h}</th>)}
        </tr>
      </thead>
      <tbody>
        <FillerRow first="60%" />
        <tr style={{ borderBottom: '1px solid #ECEBE4' }}>
          <td style={{ padding: '10px 0' }}>Gross margin</td>
          <td style={{ padding: '10px 0 10px 10px', textAlign: 'right' }}>{hlCell('75.0%', 0.15)}</td>
          <td style={{ padding: '10px 0 10px 10px', textAlign: 'right' }}>{hlCell('72.7%', 0.3)}</td>
          <td style={{ padding: '10px 0 10px 10px', textAlign: 'right' }}>{hlCell('Up 2.3 pts', 0.45)}</td>
        </tr>
        <FillerRow first="48%" />
      </tbody>
    </table>
  )
}

function P42Text() {
  const on = useAfterMount()
  return (
    <p style={{ margin: '22px 0 0', fontSize: 16, lineHeight: 1.65 }}>
      <span style={{ color: 'var(--faint)' }}>Gross margins increased to 75.0% in fiscal year 2025 from 72.7% in fiscal year 2024. </span>
      <span className={'hl cell' + (on ? ' on' : '')} style={{ padding: '1px 0', transitionDuration: '.9s', transitionDelay: '.1s' }}>The year over year increase was primarily driven by a higher mix of Data Center revenue.</span>
    </p>
  )
}

export function OpenSource() {
  const { t } = useSite()
  const ref = useRef<HTMLElement>(null)
  const seen = useRef(false)
  const timers = useTimers()
  const [claim, setClaim] = useState(0)

  // First time the section reaches the upper part of the viewport, open claim 1 on its own.
  useScrollFrame(() => {
    const el = ref.current
    if (!el || seen.current || el.getBoundingClientRect().top >= window.innerHeight * 0.45) return
    seen.current = true
    timers.at(() => setClaim((c) => c || 1), 450)
  })

  return (
    <section id="source" ref={ref} className="section">
      <div className="wrap">
        <div style={{ maxWidth: 760 }}>
          <div className="kicker">{t.open.k}</div>
          <h2 className="h2" style={{ fontSize: 'clamp(40px,5.4vw,70px)', lineHeight: 1, letterSpacing: '-.025em' }}>{t.open.title}</h2>
          <p className="lead" style={{ maxWidth: '54ch' }}>{t.open.body}</p>
        </div>
        <div className="cols" style={{ marginTop: 'clamp(40px,5vw,64px)', ['--min' as string]: '400px', ['--gap' as string]: 'clamp(20px,3vw,32px)', alignItems: 'stretch' }}>
          <div className="card" style={{ padding: 'clamp(22px,3vw,32px)', display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div className="label">{t.open.answer}</div>
            <div className="bubble" style={{ maxWidth: '90%' }}>{Q.q}</div>
            <p style={{ margin: 0, fontSize: 'clamp(17px,1.6vw,19px)', lineHeight: 1.75 }}>
              <AnswerText slow segs={buildSegs(Q, Infinity, (c) => claim === c)} onPick={setClaim} />
            </p>
            <div style={{ marginTop: 'auto', paddingTop: 16, borderTop: '1px solid var(--line2)' }}>
              <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 10 }}>{t.open.hint}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {Q.chips.map((ch) => <Chip key={ch.cite} n={ch.n} label={ch.label} on={claim === ch.c} onClick={() => setClaim(ch.c)} onFocus={() => setClaim(ch.c)} />)}
              </div>
            </div>
          </div>

          <div aria-live="polite" style={{ position: 'relative', background: '#FFFEFB', border: '1px solid var(--line3)', borderRadius: 4, boxShadow: '0 1px 0 #E4E3DC, 0 6px 0 -3px #FFFEFB, 0 6px 0 -2px #DEDDD5, 0 34px 70px -40px rgba(22,21,15,.45)', padding: 'clamp(22px,3.4vw,40px)', fontFamily: 'var(--serif)', display: 'flex', flexDirection: 'column' }}>
            <div className="mono" style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 10.5, letterSpacing: '.04em', color: 'var(--muted)', textTransform: 'uppercase', paddingBottom: 12, borderBottom: '1px solid var(--ink)' }}>
              <span>NVIDIA Corporation · Form 10-K · FY ended Jan 26, 2025</span>
              <span style={{ color: 'var(--ink)', whiteSpace: 'nowrap' }}>{claim === 2 ? 'p.42–43' : 'p.38'}</span>
            </div>
            <div style={{ fontWeight: 500, fontSize: 15, lineHeight: 1.35, marginTop: 16 }}>Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations</div>
            <div aria-hidden="true" style={{ display: 'grid', gap: 7, marginTop: 16 }}>{bar('100%')}{bar('94%')}{bar('97%')}{bar('62%')}</div>
            {claim !== 2 ? <P38Table active={claim === 1} /> : <P42Text />}
            <div aria-hidden="true" style={{ display: 'grid', gap: 7, marginTop: 22 }}>{bar('98%')}{bar('91%')}{bar('44%')}</div>
            <div style={{ marginTop: 'auto', paddingTop: 24, display: 'flex', gap: 10, alignItems: 'flex-start', fontFamily: 'var(--sans)', fontSize: 13, lineHeight: 1.5, color: 'var(--body)', opacity: claim ? 1 : 0, transition: 'opacity .4s .6s' }}>
              <span className="check-dot">✓</span>
              <span>{t.panel.verified}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
