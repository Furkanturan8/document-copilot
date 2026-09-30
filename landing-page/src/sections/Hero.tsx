import { useEffect, useRef, useState } from 'react'
import { GITHUB_URL, HERO } from '../content'
import { AnswerText, buildSegs, Chip, useSite } from '../site'

const TICK = 40
const CHAR_MS = 32 // question typing
const STREAM_MS = 14 // answer streaming

function heroTimes(qi: number) {
  const q = HERO[qi]
  const ansLen = q.segs.reduce((a, s) => a + s.t.length, 0)
  const typeEnd = q.q.length * CHAR_MS
  const statusStart = typeEnd + 350
  const streamStart = statusStart + 1700
  const chipsAt = streamStart + ansLen * STREAM_MS + 200
  return { typeEnd, statusStart, streamStart, chipsAt, end: chipsAt + 6500, qLen: q.q.length }
}

export function Hero() {
  const { t, reduced, paused, activeCite, openPanel, openDemo } = useSite()
  const [qi, setQi] = useState(0)
  const [heroT, setHeroT] = useState(0)
  const clock = useRef(0)
  const lastKey = useRef('')
  const qiRef = useRef(0)
  const pausedRef = useRef(paused)
  useEffect(() => { pausedRef.current = paused }, [paused])

  const goHero = (i: number) => {
    clock.current = 0
    lastKey.current = ''
    qiRef.current = i
    setQi(i)
    setHeroT(0)
  }

  useEffect(() => {
    if (reduced) return
    const id = window.setInterval(() => {
      if (pausedRef.current || document.hidden) return
      clock.current += TICK
      const tm = heroTimes(qiRef.current)
      if (clock.current >= tm.end) { goHero((qiRef.current + 1) % HERO.length); return }
      const c = clock.current
      const phase = c < tm.statusStart ? 0 : c < tm.streamStart ? 1 : c < tm.chipsAt ? 2 : 3
      // Only re-render when something visible changes (a typed char, a streamed char, a phase).
      const key = [Math.min(tm.qLen, Math.floor(c / CHAR_MS)), phase, phase === 2 ? Math.floor((c - tm.streamStart) / STREAM_MS) : 0].join('|')
      if (key !== lastKey.current) { lastKey.current = key; setHeroT(c) }
    }, TICK)
    return () => clearInterval(id)
  }, [reduced])

  const q = HERO[qi]
  const tm = heroTimes(qi)
  const ht = reduced ? tm.end - 1 : heroT
  const typedN = Math.min(tm.qLen, Math.floor(ht / CHAR_MS))
  const chars = ht >= tm.streamStart ? Math.floor((ht - tm.streamStart) / STREAM_MS) : 0
  const citeOf = (c: number) => q.chips.find((ch) => ch.c === c)?.cite
  const showChips = ht >= tm.chipsAt

  return (
    <section id="top" style={{ maxWidth: 1200, margin: '0 auto', padding: 'clamp(48px,8vw,104px) var(--gutter) clamp(64px,8vw,112px)', boxSizing: 'border-box', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,440px),1fr))', gap: 'clamp(40px,6vw,80px)', alignItems: 'center' }}>
      <div>
        <div className="mono" style={{ fontSize: 12, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--muted)' }}>{t.hero.eyebrow}</div>
        <h1 className="serif" style={{ fontWeight: 400, fontSize: 'clamp(44px,6.2vw,78px)', lineHeight: 0.98, letterSpacing: '-.025em', margin: '22px 0 0', textWrap: 'balance' }}>
          <span style={{ display: 'block' }}>{t.hero.t1}</span>
          <span style={{ display: 'block', fontStyle: 'italic' }}>{t.hero.t2}</span>
        </h1>
        <p style={{ fontSize: 18, lineHeight: 1.6, color: 'var(--body)', maxWidth: '46ch', margin: '28px 0 0', textWrap: 'pretty' }}>{t.hero.sub}</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 34 }}>
          <a className="btn btn-dark" href={GITHUB_URL} target="_blank" rel="noopener">{t.hero.gh} <span aria-hidden="true">↗</span></a>
          <button type="button" className="btn btn-ghost" onClick={openDemo}><span aria-hidden="true" className="tri">▶</span> {t.hero.demo}</button>
        </div>
        <div className="mono" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 18px', marginTop: 40, paddingTop: 20, borderTop: '1px solid var(--line)', fontSize: 12, color: 'var(--muted)' }}>
          {t.hero.meta.map((m) => <span key={m}>{m}</span>)}
        </div>
      </div>

      <div>
        <div className="card" style={{ boxShadow: '0 30px 70px -40px rgba(22,21,15,.35)', overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '1px solid var(--line2)', fontSize: 13 }}>
            <span style={{ fontWeight: 600 }}>Document Copilot</span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>10-K · FY2021–2025</span>
          </div>
          <div aria-live="polite" style={{ minHeight: 'clamp(340px,40vw,380px)', padding: '24px 22px', display: 'flex', flexDirection: 'column', gap: 16 }}>
            {typedN > 0 && (
              <div className="bubble" style={{ fontSize: 15 }}>
                {q.q.slice(0, typedN)}
                {ht < tm.typeEnd + 300 && <span aria-hidden="true" style={{ display: 'inline-block', width: 1.5, height: '1.05em', background: 'var(--ink)', marginLeft: 2, verticalAlign: -2, animation: 'dcBlink 1s steps(1) infinite' }} />}
              </div>
            )}
            {ht >= tm.statusStart && ht < tm.streamStart && (
              <div className="status" style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <span style={{ paddingTop: 5 }}><span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: 99, background: 'var(--ink)', animation: 'dcPulse 1s ease-in-out infinite' }} /></span>
                <span>{q.status}</span>
              </div>
            )}
            {ht >= tm.streamStart && (
              <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.7 }}>
                <AnswerText segs={buildSegs(q, chars, (c) => !!activeCite && citeOf(c) === activeCite)} />
              </p>
            )}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, opacity: showChips ? 1 : 0, transform: showChips ? 'none' : 'translateY(6px)', transition: 'opacity .4s, transform .4s', pointerEvents: showChips ? 'auto' : 'none' }}>
              {q.chips.map((ch) => <Chip key={ch.cite} n={ch.n} label={ch.label} on={activeCite === ch.cite} onClick={() => openPanel(ch.cite)} />)}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px 12px 20px', borderTop: '1px solid var(--line2)' }}>
            <span style={{ flex: 1, fontSize: 14, color: 'var(--faint)' }}>{t.hero.input}</span>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              {HERO.map((_, i) => (
                <button key={i} type="button" onClick={() => goHero(i)} aria-label={`${t.hero.question} ${i + 1}`} aria-current={i === qi}
                  style={{ width: i === qi ? 22 : 8, height: 8, borderRadius: 99, border: 0, padding: 0, background: i === qi ? 'var(--ink)' : '#D6D5CE', cursor: 'pointer', transition: 'width .3s, background .3s' }} />
              ))}
            </div>
          </div>
        </div>
        <div className="mono" style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: '6px 16px', marginTop: 14, fontSize: 11.5, color: 'var(--muted)' }}>
          <span>{t.hero.note}</span>
          <span style={{ color: 'var(--ink)' }}>{t.hero.hint}</span>
        </div>
      </div>
    </section>
  )
}
