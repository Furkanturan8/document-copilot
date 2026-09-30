import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { CITES, DEMO_REELS, type CiteId } from './content'
import { useSite } from './site'

// Keeps Tab / Shift+Tab inside a dialog.
function trapTab(e: KeyboardEvent<HTMLElement>) {
  if (e.key !== 'Tab') return
  const els = e.currentTarget.querySelectorAll<HTMLElement>('button, a[href], video[controls]')
  if (!els.length) return
  const first = els[0]
  const last = els[els.length - 1]
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}

export function SourcePanel({ open, cite, onClose }: { open: boolean; cite: CiteId; onClose: () => void }) {
  const { t, reduced } = useSite()
  const closeRef = useRef<HTMLButtonElement>(null)
  const [hlOn, setHlOn] = useState(false)

  // The highlight sweeps in once the panel has slid open.
  useEffect(() => {
    setHlOn(false)
    if (!open) return
    const hl = window.setTimeout(() => setHlOn(true), reduced ? 0 : 380)
    const focus = window.setTimeout(() => closeRef.current?.focus({ preventScroll: true }), 60)
    return () => { clearTimeout(hl); clearTimeout(focus) }
  }, [open, cite, reduced])

  const C = CITES[cite]
  const on = open && hlOn

  return (
    <>
      <div className="scrim" onClick={onClose} style={{ opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none' }} />
      <aside role="dialog" aria-modal="true" aria-label={t.panel.source} aria-hidden={!open} className={'panel' + (open ? ' open' : '')} onKeyDown={trapTab}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <span className="label" style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><span className="chip-n" style={{ color: 'var(--ink)', borderColor: 'var(--ink)' }}>{C.n}</span>{t.panel.source}</span>
          <button ref={closeRef} type="button" className="icon-btn" onClick={onClose} aria-label={t.panel.close}>✕</button>
        </div>
        <div style={{ marginTop: 22, display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
          <span className="serif" style={{ fontSize: 28, lineHeight: 1.1 }}>{C.company}</span>
          <span className="mono" style={{ fontSize: 12, color: 'var(--muted)' }}>{C.ticker}</span>
        </div>
        <dl className="meta-grid">
          <div><dt>{t.panel.form}</dt><dd>Form {C.form}</dd></div>
          <div><dt>{t.panel.fy}</dt><dd>{C.fy}</dd></div>
          <div><dt>{t.panel.filed}</dt><dd style={{ fontVariantNumeric: 'tabular-nums' }}>{C.filed}</dd></div>
          <div><dt>{t.panel.page}</dt><dd>{C.page}</dd></div>
          <div style={{ gridColumn: '1 / -1' }}><dt>{t.panel.section}</dt><dd>{C.section}</dd></div>
        </dl>
        <div className="label" style={{ marginTop: 26, fontSize: 10.5 }}>{t.panel.passage}</div>
        <div className="serif" style={{ marginTop: 10, background: '#FFFEFB', border: '1px solid var(--line)', borderRadius: 6, padding: 18 }}>
          {C.table && (
            <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: C.table.head.length > 4 ? 12.5 : 15, fontVariantNumeric: 'tabular-nums' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--ink)' }}>
                  {C.table.head.map((h, i) => <th key={i} style={{ textAlign: i ? 'right' : 'left', fontWeight: 500, fontSize: 12, padding: '5px 0 5px 6px' }}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {C.table.rows.map((r, ri) => (
                  <tr key={ri}>
                    {r.map((v, i) => (
                      <td key={i} style={{ textAlign: i ? 'right' : 'left', padding: '10px 0 10px 6px', whiteSpace: i ? 'nowrap' : 'normal' }}>
                        <span className={'hl cell' + (on && C.table!.hl.includes(i) ? ' on' : '')}>{v}</span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
          {C.parts && (
            <p style={{ margin: 0, fontSize: 17, lineHeight: 1.6 }}>
              {C.parts.map((p, i) => <span key={i} className={'hl cell' + (on && p.h ? ' on' : '')} style={{ padding: 0, transitionDuration: '.8s' }}>{p.t}</span>)}
            </p>
          )}
        </div>
        <div style={{ marginTop: 18, display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 13.5, lineHeight: 1.5, color: 'var(--body)' }}>
          <span className="check-dot">✓</span>
          <span style={{ fontStyle: 'italic' }}>{t.panel.verified}</span>
        </div>
        <div className="mono" style={{ marginTop: 22, paddingTop: 16, borderTop: '1px solid var(--line2)', fontSize: 11, color: 'var(--muted)' }}>{t.panel.demoNote}</div>
      </aside>
    </>
  )
}

// Plays the three recordings back to back.
export function DemoModal({ onClose }: { onClose: () => void }) {
  const { t } = useSite()
  const [reel, setReel] = useState(0)
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => { closeRef.current?.focus({ preventScroll: true }) }, [])

  return (
    <div role="dialog" aria-modal="true" aria-label={t.media.demo} onClick={onClose} onKeyDown={trapTab}
      style={{ position: 'fixed', inset: 0, zIndex: 70, background: 'rgba(22,21,15,.82)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'clamp(16px,4vw,48px)' }}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: 'min(1080px,100%)', background: 'var(--bg)', borderRadius: 16, overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 14px 12px 20px', borderBottom: '1px solid var(--line)' }}>
          <span className="mono" style={{ fontSize: 12, color: 'var(--muted)' }}>{t.media.demo} · {reel + 1} / {DEMO_REELS.length}</span>
          <button ref={closeRef} type="button" className="icon-btn" onClick={onClose} aria-label={t.panel.close}>✕</button>
        </div>
        <div style={{ position: 'relative', aspectRatio: '1440 / 702', background: '#fff' }}>
          <video key={reel} src={DEMO_REELS[reel]} poster={DEMO_REELS[reel].replace('.mp4', '.jpg')} autoPlay muted playsInline controls
            onEnded={() => setReel((r) => (r + 1) % DEMO_REELS.length)}
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} />
        </div>
        <p style={{ margin: 0, padding: '14px 20px', fontSize: 13.5, lineHeight: 1.5, color: 'var(--body)' }}>{t.media.demoText}</p>
      </div>
    </div>
  )
}
