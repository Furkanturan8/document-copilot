import { useEffect, useRef, useState } from 'react'
import { AppReplay } from '../AppReplay'
import { PLANS, REPLAYS } from '../replays'
import { useSite } from '../site'

// The replay is laid out at a fixed size and scaled to the stage, so it looks like one screen.
const CANVAS = { desk: { w: 1000, ratio: 1440 / 702 }, mob: { w: 400, ratio: 3 / 4 } }
const fmt = (ms: number) => `0:${String(Math.floor(ms / 1000)).padStart(2, '0')}`

export function Recordings() {
  const { t, reduced, mobile, paused: sitePaused, openDemo } = useSite()
  const items = t.media.items
  const stageRef = useRef<HTMLDivElement>(null)
  const [stageW, setStageW] = useState(0)
  const [inView, setInView] = useState(false)
  const [mi, setMi] = useState(0)
  // With reduced motion each slide starts on its finished state.
  const startOf = (i: number) => (reduced ? PLANS[i].dur : 0)
  const [elapsed, setElapsed] = useState(() => startOf(0))
  const [userPaused, setUserPaused] = useState(reduced)

  const dur = PLANS[mi].dur
  const running = inView && !userPaused && !sitePaused
  const canvas = mobile ? CANVAS.mob : CANVAS.desk

  const go = (i: number) => {
    const n = (i + items.length) % items.length
    setMi(n)
    setElapsed(startOf(n))
  }

  useEffect(() => {
    const el = stageRef.current
    if (!el) return
    const io = new IntersectionObserver(([e]) => setInView(e.isIntersecting), { threshold: 0.35 })
    const ro = new ResizeObserver(([e]) => setStageW(e.contentRect.width))
    io.observe(el)
    ro.observe(el)
    return () => { io.disconnect(); ro.disconnect() }
  }, [])

  // Frame clock: advances only while the stage is visible and nothing covers the page.
  useEffect(() => {
    if (!running) return
    let raf = 0
    let last = performance.now()
    const loop = (now: number) => {
      const dt = Math.min(100, now - last)
      last = now
      setElapsed((e) => e + dt)
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [running])

  useEffect(() => {
    if (running && elapsed >= dur) {
      setMi((m) => (m + 1) % items.length)
      setElapsed(0)
    }
  }, [running, elapsed, dur, items.length])

  const shown = Math.min(elapsed, dur)
  const cur = items[mi]

  return (
    <section id="recordings" className="section">
      <div className="wrap">
        <div className="head-row">
          <div>
            <div className="kicker">{t.media.k}</div>
            <h2 className="h2">{t.media.title}</h2>
          </div>
          <p className="lead" style={{ maxWidth: '50ch', margin: 0 }}>{t.media.body}</p>
        </div>

        <div style={{ marginTop: 48 }}>
          <div ref={stageRef} className="stage" style={{ aspectRatio: String(canvas.ratio), background: '#fff' }}>
            <span className="sr-only" aria-live="polite">{cur.title}. {cur.cap}</span>
            {REPLAYS.map((r, i) => {
              const active = i === mi
              return (
                <div key={i} aria-hidden="true" style={{ position: 'absolute', inset: 0, opacity: active ? 1 : 0, transition: 'opacity .6s ease', pointerEvents: 'none' }}>
                  {stageW > 0 && (
                    <div style={{ position: 'absolute', inset: 0, transform: `scale(${stageW / canvas.w})`, transformOrigin: '0 0', width: canvas.w, height: canvas.w / canvas.ratio }}>
                      <div style={{ position: 'relative', width: canvas.w, height: canvas.w / canvas.ratio }}>
                        <AppReplay replay={r} plan={PLANS[i]} t={active ? elapsed : 0} compact={mobile} />
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          <div role="tablist" style={{ marginTop: 18, display: 'grid', gridTemplateColumns: 'repeat(6,minmax(0,1fr))', gap: 8 }}>
            {items.map((m, i) => (
              <button key={m.file} type="button" role="tab" aria-selected={i === mi} aria-label={m.title} onClick={() => go(i)}
                style={{ border: 0, background: 'transparent', padding: '8px 0 4px', cursor: 'pointer', textAlign: 'left', display: 'grid', gap: 9, minWidth: 0 }}>
                <span style={{ position: 'relative', display: 'block', height: 3, borderRadius: 99, background: 'var(--line)', overflow: 'hidden' }}>
                  <span style={{ position: 'absolute', left: 0, top: 0, bottom: 0, borderRadius: 99, background: 'var(--ink)', width: i < mi ? '100%' : i === mi ? `${(shown / dur) * 100}%` : '0%' }} />
                </span>
                <span className="mono" style={{ display: mobile ? 'none' : 'block', fontSize: 11, color: i === mi ? 'var(--ink)' : 'var(--faint)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', transition: 'color .3s' }}>{m.title}</span>
              </button>
            ))}
          </div>

          <div style={{ marginTop: 20, display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px 32px' }}>
            <div style={{ flex: '1 1 380px', minWidth: 0 }}>
              <div className="mono" style={{ fontSize: 11.5, color: 'var(--muted)' }}>
                {String(mi + 1).padStart(2, '0')} / {String(items.length).padStart(2, '0')} · {t.media.replay} · {t.media.from} {cur.file} · <button type="button" onClick={openDemo} className="mono" style={{ border: 0, background: 'none', padding: 0, cursor: 'pointer', fontSize: 11.5, color: 'var(--ink)', textDecoration: 'underline', textUnderlineOffset: 3 }}>{t.media.watch} ↗</button>
              </div>
              <p className="serif" style={{ margin: '6px 0 0', fontSize: 'clamp(20px,2vw,24px)', lineHeight: 1.3, maxWidth: '46ch', textWrap: 'pretty' }}>{cur.cap}</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span className="mono" style={{ fontSize: 12, color: 'var(--muted)', fontVariantNumeric: 'tabular-nums', textAlign: 'right', display: 'grid', gap: 3 }}>
                <span style={{ color: 'var(--ink)' }}>{fmt(shown)} / {fmt(dur)}</span>
                <span>{Math.ceil((dur - shown) / 1000)} {t.media.left}</span>
              </span>
              <div style={{ display: 'flex', gap: 6 }}>
                <button type="button" className="round-btn" aria-label={t.media.prev} onClick={() => go(mi - 1)}>←</button>
                <button type="button" className="round-btn dark" aria-label={userPaused ? t.media.play : t.media.pause} onClick={() => setUserPaused((p) => !p)}>{userPaused ? '▶' : '❚❚'}</button>
                <button type="button" className="round-btn" aria-label={t.media.next} onClick={() => go(mi + 1)}>→</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
