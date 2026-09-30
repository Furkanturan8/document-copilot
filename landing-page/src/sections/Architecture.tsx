import type { CSSProperties } from 'react'
import { GITHUB_URL, type ArchSide } from '../content'
import { useSite } from '../site'

const via: CSSProperties = { position: 'absolute', left: 'calc(50% + 10px)', top: '50%', transform: 'translateY(-50%)', fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--muted)', whiteSpace: 'nowrap', background: '#FCFCFA', padding: '2px 5px', borderRadius: 4 }
const arrowDown = <span style={{ width: 0, height: 0, borderLeft: '5px solid transparent', borderRight: '5px solid transparent', borderTop: '7px solid var(--ink)' }} />
const arrowUp = <span style={{ width: 0, height: 0, borderLeft: '5px solid transparent', borderRight: '5px solid transparent', borderBottom: '7px solid var(--ink)' }} />

function SideBox({ x }: { x: ArchSide }) {
  const bs = x.dashed ? 'dashed' : 'solid'
  return (
    <div style={{ padding: '14px 14px 16px', borderRadius: 12, border: `1px ${bs} ${x.dashed ? 'var(--dash)' : 'var(--line)'}`, background: x.dashed ? '#FCFCFA' : '#fff', display: 'grid', gap: 4 }}>
      <div className="serif" style={{ fontSize: 19, lineHeight: 1.15 }}>{x.name}</div>
      <div className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>{x.tech}</div>
      <div style={{ marginTop: 4, fontSize: 12.5, lineHeight: 1.45, color: 'var(--body)', textWrap: 'pretty' }}>{x.d}</div>
    </div>
  )
}

function GuardTag({ label }: { label: string }) {
  return <span className="mono" style={{ background: 'var(--hl)', color: 'var(--ink)', borderRadius: 999, padding: '2px 8px', fontSize: 10, letterSpacing: '.05em', textTransform: 'uppercase' }}>{label}</span>
}

export function Architecture() {
  const { t, mobile, reduced } = useSite()
  const A = t.arch
  const nodes = A.nodes.map((nd) => ({
    ...nd,
    bg: nd.end ? 'var(--ink)' : '#fff', fg: nd.end ? 'var(--bg)' : 'var(--ink)',
    mute: nd.end ? '#C9C8C0' : 'var(--muted)', border: nd.end ? 'var(--ink)' : 'var(--line)',
  }))

  return (
    <section id="architecture" className="section">
      <div className="wrap">
        <div className="head-row">
          <div>
            <div className="kicker">{A.k}</div>
            <h2 className="h2">{A.title}</h2>
          </div>
          <div>
            <p className="lead" style={{ maxWidth: '50ch', margin: 0 }}>{A.body}</p>
            <a href={`${GITHUB_URL}/blob/main/docs/architecture.md`} target="_blank" rel="noopener" style={{ display: 'inline-block', marginTop: 14, fontSize: 15 }}>docs/architecture.md ↗</a>
          </div>
        </div>

        {!mobile ? (
          <div className="card" style={{ marginTop: 48, borderRadius: 22, overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto', backgroundColor: '#FCFCFA', backgroundImage: 'radial-gradient(#DEDDD5 1px, transparent 1.3px)', backgroundSize: '18px 18px' }}>
              <div style={{ minWidth: 1040, boxSizing: 'border-box', padding: '40px 36px 36px', display: 'grid', gridTemplateColumns: 'repeat(6,minmax(0,1fr))', columnGap: 34 }}>
                {nodes.map((n, i) => (
                  <div key={n.n} style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: 4, padding: '16px 16px 18px', borderRadius: 14, border: `1px solid ${n.border}`, background: n.bg, color: n.fg, boxShadow: '0 14px 34px -26px rgba(22,21,15,.55)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6, minHeight: 20 }}>
                      <span className="mono" style={{ fontSize: 11, color: n.mute }}>{n.n}</span>
                      {n.guard && <GuardTag label={A.guard} />}
                    </div>
                    <div className="serif" style={{ fontSize: 23, lineHeight: 1.1, marginTop: 8 }}>{n.name}</div>
                    <div className="mono" style={{ fontSize: 11, color: n.mute }}>{n.tech}</div>
                    <div style={{ marginTop: 8, fontSize: 13, lineHeight: 1.45, color: n.mute, textWrap: 'pretty' }}>{n.d}</div>
                    {i < nodes.length - 1 && (
                      <span aria-hidden="true" style={{ position: 'absolute', left: '100%', top: '50%', width: 34, height: 10, marginTop: -5, display: 'flex', alignItems: 'center', padding: '0 3px', boxSizing: 'border-box' }}>
                        <span style={{ position: 'relative', flex: 1, height: 1.5, background: 'var(--ink)' }}>
                          <span style={{ position: 'absolute', top: -2.5, left: 0, width: 6, height: 6, borderRadius: 99, background: 'var(--hl)', boxShadow: '0 0 0 1px var(--ink)', opacity: 0, animation: reduced ? 'none' : `dcFlow 2.6s ${i * 0.45}s linear infinite` }} />
                        </span>
                        <span style={{ width: 0, height: 0, borderTop: '5px solid transparent', borderBottom: '5px solid transparent', borderLeft: '7px solid var(--ink)' }} />
                      </span>
                    )}
                  </div>
                ))}
                {A.side.map((x, i) => (
                  <div key={`sc${i}`} aria-hidden="true" style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center', height: 72, padding: '4px 0', boxSizing: 'border-box' }}>
                    {x && <>{x.both && arrowUp}<span style={{ flex: 1, width: 0, borderLeft: `1.5px ${x.dashed ? 'dashed' : 'solid'} var(--ink)` }} />{arrowDown}<span style={via}>{x.via}</span></>}
                  </div>
                ))}
                {A.side.map((x, i) => <div key={`s${i}`}>{x && <SideBox x={x} />}</div>)}
                {A.sub.map((x, i) => (
                  <div key={`uc${i}`} aria-hidden="true" style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center', height: 56, padding: '4px 0', boxSizing: 'border-box' }}>
                    {x && <>{arrowUp}<span style={{ flex: 1, width: 0, borderLeft: '1.5px solid var(--ink)' }} /><span style={via}>{x.via}</span></>}
                  </div>
                ))}
                {A.sub.map((x, i) => <div key={`u${i}`}>{x && <SideBox x={x} />}</div>)}
              </div>
            </div>
            <div className="mono" style={{ display: 'flex', flexWrap: 'wrap', gap: '10px 28px', padding: '16px 36px', borderTop: '1px solid var(--line2)', fontSize: 11.5, color: 'var(--body)' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><span style={{ width: 22, borderTop: '1.5px solid var(--ink)' }} />{A.legend.path}</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><span style={{ width: 22, borderTop: '1.5px dashed var(--ink)' }} />{A.legend.branch}</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><span style={{ width: 14, height: 10, borderRadius: 99, background: 'var(--hl)' }} />{A.legend.guard}</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><span style={{ width: 12, height: 12, borderRadius: 3, background: 'var(--ink)' }} />{A.legend.out}</span>
            </div>
          </div>
        ) : (
          <div style={{ marginTop: 36 }}>
            {nodes.map((n, i) => {
              const side = A.side[i]
              const sub = A.sub[i]
              return (
                <div key={n.n}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: 16, borderRadius: 14, border: `1px solid ${n.border}`, background: n.bg, color: n.fg }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
                      <span className="mono" style={{ fontSize: 11, color: n.mute }}>{n.n}</span>
                      {n.guard && <GuardTag label={A.guard} />}
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: '4px 10px', marginTop: 4 }}>
                      <span className="serif" style={{ fontSize: 22, lineHeight: 1.1 }}>{n.name}</span>
                      <span className="mono" style={{ fontSize: 11, color: n.mute }}>{n.tech}</span>
                    </div>
                    <div style={{ marginTop: 4, fontSize: 13.5, lineHeight: 1.45, color: n.mute }}>{n.d}</div>
                  </div>
                  {side && (
                    <div style={{ marginLeft: 20, padding: '12px 0 4px 18px', borderLeft: `1.5px ${side.dashed ? 'dashed' : 'solid'} var(--ink)`, display: 'grid', gap: 8 }}>
                      <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>↳ {side.via}</span>
                      <SideBox x={side} />
                      {sub && <><span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>↑ {sub.via}</span><SideBox x={sub} /></>}
                    </div>
                  )}
                  {i < nodes.length - 1 && (
                    <div aria-hidden="true" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', height: 34, padding: '3px 0', boxSizing: 'border-box' }}>
                      <span style={{ flex: 1, width: 0, borderLeft: '1.5px solid var(--ink)' }} />{arrowDown}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </section>
  )
}
