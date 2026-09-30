import { useState } from 'react'
import { JEVQ, LABELS } from '../content'
import { useSite, useTimers } from '../site'

// Phases: 0 reset · 1 Jev reading · 2 Jev decided · 3 assistant running · 4 reply shown
export function Jev() {
  const { t, reduced, openPanel } = useSite()
  const timers = useTimers()
  const [sel, setSel] = useState(1)
  const [ph, setPh] = useState(4)

  const pick = (i: number) => {
    timers.reset()
    setSel(i)
    if (reduced) { setPh(4); return }
    setPh(0)
    timers.at(() => setPh(1), 30)
    timers.at(() => setPh(2), 480)
    if (JEVQ[i].route === 'jev') timers.at(() => setPh(4), 700)
    else { timers.at(() => setPh(3), 700); timers.at(() => setPh(4), 3200) }
  }

  const q = JEVQ[sel]
  const isJev = q.route === 'jev'
  const top = q.probs.indexOf(Math.max(...q.probs))
  const decided = ph >= 2

  const jevStatus = ph < 1 ? '—' : ph < 2 ? t.jev.reading : `${LABELS[top]} · ${q.probs[top].toFixed(2)} ${isJev ? t.jev.short : t.jev.toAsst}`
  const asstStatus = isJev
    ? (decided ? t.jev.notRun : t.jev.waiting)
    : ph >= 4 ? (q.insufficient ? t.jev.doneNone : t.jev.done) : ph >= 3 ? t.jev.running : t.jev.waiting
  const asstRunning = !isJev && ph >= 3

  return (
    <section id="jev" className="section">
      <div className="wrap">
        <div className="head-row">
          <div>
            <div className="kicker">{t.jev.k}</div>
            <h2 className="h2">{t.jev.title}</h2>
          </div>
          <p className="lead" style={{ maxWidth: '50ch', margin: 0 }}>{t.jev.body}</p>
        </div>

        <div className="label" style={{ marginTop: 48 }}>{t.jev.pick}</div>
        <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,200px),1fr))', gap: 10 }}>
          {JEVQ.map((c, i) => (
            <button key={c.q} type="button" className="q-card" aria-pressed={i === sel} onClick={() => pick(i)}>
              <span>{c.q}</span>
              <span className="mono" style={{ marginTop: 'auto', fontSize: 11, color: 'var(--muted)' }}>{i === sel && decided ? LABELS[top] : `0${i + 1}`}</span>
            </button>
          ))}
        </div>

        <div style={{ marginTop: 20, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,360px),1fr))', gap: 20 }}>
          <div style={{ display: 'grid', gap: 12, alignContent: 'start' }}>
            <div className="lane" style={{ borderColor: (ph === 1 || (isJev && decided)) ? 'var(--ink)' : undefined }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 14 }}><span style={{ fontWeight: 600 }}>{t.jev.jevLane}</span><span className="mono" style={{ fontSize: 11.5, color: 'var(--muted)' }}>~0.4 s · ~$0.00003</span></div>
              <div className="bar"><div style={{ width: ph >= 1 ? '100%' : '0%', transition: ph >= 1 && !reduced ? 'width .42s linear' : 'none' }} /></div>
              <div className="mono" style={{ marginTop: 10, fontSize: 12 }}>{jevStatus}</div>
            </div>
            <div className="lane" style={{ opacity: isJev && decided ? 0.45 : 1, borderColor: asstRunning ? 'var(--ink)' : undefined }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 14 }}><span style={{ fontWeight: 600 }}>{t.jev.asstLane} <span style={{ fontWeight: 400, color: 'var(--muted)' }}>· gpt-5.5</span></span><span className="mono" style={{ fontSize: 11.5, color: 'var(--muted)' }}>~60 s · ~$0.3</span></div>
              <div className="bar"><div style={{ width: asstRunning ? '100%' : '0%', transition: asstRunning && !reduced ? 'width 2.5s linear' : 'none' }} /></div>
              <div className="mono" style={{ marginTop: 10, fontSize: 12 }}>{asstStatus}</div>
            </div>
            <div style={{ border: '1px solid var(--line)', borderRadius: 14, padding: '18px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}><span style={{ fontSize: 13, fontWeight: 600 }}>{t.jev.probs}</span><span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>{t.jev.threshold}</span></div>
              <div style={{ marginTop: 14, display: 'grid', gap: 9 }}>
                {LABELS.map((l, k) => {
                  const fg = k === top && decided ? 'var(--ink)' : 'var(--muted)'
                  return (
                    <div key={l} className="mono" style={{ display: 'grid', gridTemplateColumns: '118px minmax(0,1fr) 36px', gap: 10, alignItems: 'center', fontSize: 11.5 }}>
                      <span style={{ color: fg }}>{l}</span>
                      <span style={{ position: 'relative', height: 8, background: 'var(--bubble)', borderRadius: 2 }}>
                        <span style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: decided ? `${Math.round(q.probs[k] * 100)}%` : '0%', background: k === top ? 'var(--ink)' : 'var(--border)', borderRadius: 2, transition: 'width .5s var(--ease)' }} />
                        <span style={{ position: 'absolute', left: '80%', top: -3, bottom: -3, width: 1, background: 'var(--ink)' }} />
                      </span>
                      <span style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: fg }}>{decided ? q.probs[k].toFixed(2) : '—'}</span>
                    </div>
                  )
                })}
              </div>
              <div style={{ marginTop: 12, fontSize: 12, color: 'var(--muted)' }}>{t.jev.illus}</div>
            </div>
          </div>

          <div className="card" aria-live="polite" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16, minHeight: 320 }}>
            <div className="bubble" style={{ maxWidth: '90%' }}>{q.q}</div>
            <div className="mono" style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', fontSize: 12, opacity: decided ? 1 : 0, transition: 'opacity .3s' }}>
              <span style={{ color: 'var(--muted)' }}>{t.jev.decision}</span>
              <span style={{ border: '1px solid var(--ink)', borderRadius: 4, padding: '2px 7px' }}>{LABELS[top]}</span>
              <span style={{ color: 'var(--body)' }}>{isJev ? t.jev.short : t.jev.toAsst}</span>
            </div>
            {ph >= 4 && (
              <>
                <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.65 }}>{q.reply}</p>
                {q.chip && q.cite && (
                  <div><button type="button" className="chip" onClick={() => openPanel(q.cite!)}><span className="chip-n">1</span><span>{q.chip}</span></button></div>
                )}
                {q.insufficient && <div><span className="no-src">{t.jev.noSources}</span></div>}
              </>
            )}
            <div className="mono" style={{ marginTop: 'auto', fontSize: 11.5, color: 'var(--muted)' }}>{ph >= 4 ? (isJev ? t.jev.tJev : t.jev.tAsst) : ''}</div>
          </div>
        </div>
      </div>
    </section>
  )
}
