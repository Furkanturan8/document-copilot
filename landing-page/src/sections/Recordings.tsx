import { useEffect, useRef, useState } from 'react'
import { useSite } from '../site'

const STILL_TICK = 250
const fmt = (ms: number) => `0:${String(Math.floor(ms / 1000)).padStart(2, '0')}`

export function Recordings() {
  const { t, reduced, mobile, paused: sitePaused } = useSite()
  const items = t.media.items
  const stageRef = useRef<HTMLDivElement>(null)
  const videos = useRef<(HTMLVideoElement | null)[]>([])
  const [mi, setMi] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [userPaused, setUserPaused] = useState(reduced)
  const [inView, setInView] = useState(false)

  const cur = items[mi]
  const running = inView && !userPaused && !sitePaused

  const go = (i: number) => {
    setMi((i + items.length) % items.length)
    setElapsed(0)
  }

  useEffect(() => {
    const el = stageRef.current
    if (!el) return
    const io = new IntersectionObserver(([e]) => setInView(e.isIntersecting), { threshold: 0.35 })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  // Only the active video plays; it restarts from 0 whenever it becomes active.
  useEffect(() => {
    videos.current.forEach((v, i) => {
      if (!v) return
      if (i !== mi) { v.pause(); v.currentTime = 0 }
    })
  }, [mi])

  useEffect(() => {
    const v = videos.current[mi]
    if (!v) return
    if (running) v.play().catch(() => setUserPaused(true))
    else v.pause()
  }, [mi, running])

  // Screenshots have no media clock, so they advance on a timer.
  useEffect(() => {
    if (!running || cur.video) return
    const id = window.setInterval(() => setElapsed((e) => e + STILL_TICK), STILL_TICK)
    return () => clearInterval(id)
  }, [running, cur])

  useEffect(() => {
    if (!cur.video && elapsed >= cur.dur) {
      setMi((m) => (m + 1) % items.length)
      setElapsed(0)
    }
  }, [elapsed, cur, items.length])

  const shown = Math.min(elapsed, cur.dur)

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
          <div ref={stageRef} className="stage">
            {items.map((m, i) => {
              const active = i === mi
              const common = {
                'aria-hidden': !active,
                style: { opacity: active ? 1 : 0, transform: active ? 'scale(1)' : 'scale(1.02)', transition: 'opacity .6s ease, transform .9s var(--ease)', pointerEvents: active ? 'auto' : 'none' } as const,
              }
              return m.video ? (
                <video key={m.file} {...common} ref={(el) => { videos.current[i] = el }} src={m.src} poster={m.poster} muted playsInline preload={active ? 'auto' : 'metadata'}
                  aria-label={`${m.title}. ${m.cap}`}
                  onTimeUpdate={(e) => active && setElapsed(e.currentTarget.currentTime * 1000)}
                  onEnded={() => active && go(i + 1)} />
              ) : (
                <img key={m.file} {...common} src={m.src} alt={`${m.title}. ${m.cap}`} loading="lazy" />
              )
            })}
            <div className="mono" style={{ position: 'absolute', top: 14, left: 14, right: 14, display: 'flex', justifyContent: 'space-between', gap: 12, pointerEvents: 'none', fontSize: 11.5 }}>
              <span className="pill-tag">{cur.video ? t.media.video : t.media.still} · {fmt(cur.dur)}</span>
              <span className="pill-tag" style={{ fontVariantNumeric: 'tabular-nums' }}>{String(mi + 1).padStart(2, '0')} / {String(items.length).padStart(2, '0')}</span>
            </div>
          </div>

          <div role="tablist" style={{ marginTop: 18, display: 'grid', gridTemplateColumns: 'repeat(6,minmax(0,1fr))', gap: 8 }}>
            {items.map((m, i) => (
              <button key={m.file} type="button" role="tab" aria-selected={i === mi} aria-label={m.title} onClick={() => go(i)}
                style={{ border: 0, background: 'transparent', padding: '8px 0 4px', cursor: 'pointer', textAlign: 'left', display: 'grid', gap: 9, minWidth: 0 }}>
                <span style={{ position: 'relative', display: 'block', height: 3, borderRadius: 99, background: 'var(--line)', overflow: 'hidden' }}>
                  <span style={{ position: 'absolute', left: 0, top: 0, bottom: 0, borderRadius: 99, background: 'var(--ink)', width: i < mi ? '100%' : i === mi ? `${(shown / cur.dur) * 100}%` : '0%', transition: i === mi && elapsed > 0 && !reduced ? 'width .25s linear' : 'none' }} />
                </span>
                <span className="mono" style={{ display: mobile ? 'none' : 'block', fontSize: 11, color: i === mi ? 'var(--ink)' : 'var(--faint)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', transition: 'color .3s' }}>{m.title}</span>
              </button>
            ))}
          </div>

          <div style={{ marginTop: 20, display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px 32px' }}>
            <div style={{ flex: '1 1 380px', minWidth: 0 }}>
              <div className="mono" style={{ fontSize: 11.5, color: 'var(--muted)' }}>{cur.file}</div>
              <p className="serif" style={{ margin: '6px 0 0', fontSize: 'clamp(20px,2vw,24px)', lineHeight: 1.3, maxWidth: '46ch', textWrap: 'pretty' }}>{cur.cap}</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span className="mono" style={{ fontSize: 12, color: 'var(--muted)', fontVariantNumeric: 'tabular-nums', textAlign: 'right', display: 'grid', gap: 3 }}>
                <span style={{ color: 'var(--ink)' }}>{fmt(shown)} / {fmt(cur.dur)}</span>
                <span>{Math.ceil((cur.dur - shown) / 1000)} {t.media.left}</span>
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
