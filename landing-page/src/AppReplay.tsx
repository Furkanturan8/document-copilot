import { Fragment, useLayoutEffect, useRef, type JSX } from 'react'
import { CITES } from './content'
import { TYPE_MS, STREAM_MS, type Replay, type ReplayPlan, type Turn } from './replays'

// A static rebuild of the app's chat screen, driven entirely by the elapsed time `t`.

const HISTORY = ["What's Apple's revenue?", "What was Apple's total net sales in fiscal 2024?", 'Should I buy NVIDIA stock now?', "How did NVIDIA's gross margin change from fiscal 2024 to fiscal 2025?"]

const Logo = () => (
  <span className="rp-logo">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /><circle cx="11.5" cy="14.5" r="2.5" /><path d="m13.3 16.3 1.7 1.7" /></svg>
  </span>
)
const SidebarIcon = () => <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#525252" strokeWidth="1.8"><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M9 3v18" /></svg>
const CopyIcon = () => <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#737373" strokeWidth="2"><rect x="9" y="9" width="12" height="12" rx="2" /><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1" /></svg>
const Dot = () => <span className="rp-dot" />

function answerParts(tu: Turn, chars: number) {
  const out: (string | JSX.Element)[] = []
  let from = 0
  for (const mk of tu.marks ?? []) {
    if (chars < mk.at) break
    out.push(tu.answer.slice(from, mk.at), <sup key={mk.at} className="rp-sup">{mk.m}</sup>)
    from = mk.at
  }
  out.push(tu.answer.slice(from, chars))
  return out
}

export function AppReplay({ replay, plan, t, compact }: { replay: Replay; plan: ReplayPlan; t: number; compact: boolean }) {
  const viewRef = useRef<HTMLDivElement>(null)
  const colRef = useRef<HTMLDivElement>(null)

  const sentTurns = replay.turns.filter((_, i) => t >= plan.turns[i].sent)
  const title = sentTurns.length ? sentTurns[0].q : 'New chat'
  const typing = replay.turns.findIndex((_, i) => t >= plan.turns[i].typeStart && t < plan.turns[i].sent)
  const typed = typing >= 0 ? replay.turns[typing].q.slice(0, Math.floor((t - plan.turns[typing].typeStart) / TYPE_MS)) : ''
  const pressed = plan.pressAt !== undefined && t >= plan.pressAt
  const panelOpen = plan.panelAt !== undefined && t >= plan.panelAt
  const cite = replay.panel && CITES[replay.panel.cite]

  // Keep the newest message in view, like the app's stick-to-bottom scroll.
  useLayoutEffect(() => {
    const view = viewRef.current
    const col = colRef.current
    if (!view || !col) return
    const offset = Math.max(0, col.scrollHeight - view.clientHeight)
    col.style.transform = offset ? `translateY(-${offset}px)` : 'none'
  })

  return (
    <div className="rp">
      {!compact && (
        <aside className="rp-side">
          <div className="rp-brand"><Logo /><span><b>Document Copilot</b><br /><small>SEC filing assistant</small></span></div>
          <div className="rp-new">＋ New chat</div>
          <div className="rp-label">Today</div>
          {[title, ...HISTORY.filter((h) => h !== title)].slice(0, 5).map((h, i) => <div key={h} className={'rp-item' + (i === 0 ? ' on' : '')}>{h}</div>)}
        </aside>
      )}
      <div className="rp-main">
        <div className="rp-head"><SidebarIcon /><span>{title}</span></div>
        <div className="rp-msgs" ref={viewRef}>
          <div className="rp-col" ref={colRef}>
            {replay.turns.map((tu, i) => {
              const p = plan.turns[i]
              if (t < p.sent) return null
              const chars = Math.max(0, Math.floor((t - p.answerStart) / STREAM_MS))
              const extras = t >= p.extrasAt
              return (
                <Fragment key={i}>
                  <div className="rp-q">{tu.q}</div>
                  {t < p.answerStart && (tu.status ? <div className="rp-status">{tu.status}</div> : <div className="rp-status"><Dot /></div>)}
                  {t >= p.answerStart && <div className="rp-a">{answerParts(tu, chars)}</div>}
                  {extras && tu.chips && (
                    <div className="rp-chips">
                      {tu.chips.map((c, k) => <span key={c} className={'rp-chip' + (pressed && replay.panel?.chip === k && i === replay.turns.length - 1 ? ' on' : '')}><b>{k + 1}</b>{c}</span>)}
                    </div>
                  )}
                  {extras && tu.noSources && <div className="rp-nosrc">No filing passages are cited in this answer.</div>}
                  {extras && <div><CopyIcon /></div>}
                </Fragment>
              )
            })}
          </div>
        </div>
        <div className="rp-input">
          {typed ? <span>{typed}<span className="rp-caret" /></span> : <span className="ph">Ask about the filings…</span>}
          <span className="rp-send"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5"><path d="M12 19V5M5 12l7-7 7 7" /></svg></span>
        </div>
        <div className="rp-foot">Answers are grounded in SEC filings. Check the cited passages before relying on them.</div>
      </div>

      {cite && (
        <>
          <div className="rp-dim" style={{ opacity: panelOpen ? 1 : 0 }} />
          <div className="rp-panel" style={{ transform: panelOpen ? 'none' : 'translateX(105%)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="rp-badge">{cite.n}</span><span style={{ fontSize: 14, fontWeight: 500 }}>{cite.company}</span><span style={{ marginLeft: 'auto', color: '#525252' }}>✕</span>
            </div>
            <div className="rp-tags">
              {[cite.ticker, cite.form, cite.fy.replace('FY', 'FY '), `Filed ${cite.filed}`, `Page ${cite.page.replace('p.', '')}`, cite.section].map((x) => <span key={x} className="rp-tag">{x}</span>)}
            </div>
            <div className="rp-plabel">CITED PASSAGE</div>
            <div className="rp-passage">
              {cite.table ? `| ${cite.table.rows[0].join(' | ')} |` : cite.parts?.map((x) => x.t).join('')}
            </div>
            <div className="rp-note">Quoted verbatim from the filing and checked against the retrieved passage before the answer was shown.</div>
          </div>
        </>
      )}
    </div>
  )
}
