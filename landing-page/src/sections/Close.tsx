import { GITHUB_URL } from '../content'
import { useSite } from '../site'

export function Roadmap() {
  const { t } = useSite()
  return (
    <section id="roadmap" className="section alt">
      <div className="wrap">
        <div className="kicker">{t.road.k}</div>
        <h2 className="h2">{t.road.title}</h2>
        <div style={{ marginTop: 48, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,340px),1fr))', gap: 20 }}>
          <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 16, padding: '24px 26px' }}>
            <div className="mono" style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, letterSpacing: '.06em', textTransform: 'uppercase' }}><span>{t.road.builtT}</span><span style={{ color: 'var(--muted)' }}>v1</span></div>
            <ul style={{ listStyle: 'none', margin: '16px 0 0', padding: 0 }}>
              {t.road.built.map((b) => (
                <li key={b} style={{ display: 'flex', gap: 12, padding: '11px 0', borderTop: '1px solid var(--line2)', fontSize: 15, lineHeight: 1.45 }}>
                  <span aria-hidden="true" style={{ flex: '0 0 auto', width: 16, height: 16, marginTop: 2, borderRadius: 4, background: 'var(--ink)', color: 'var(--bg)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10 }}>✓</span><span>{b}</span>
                </li>
              ))}
            </ul>
          </div>
          <div style={{ border: '1px dashed var(--dash)', borderRadius: 16, padding: '24px 26px' }}>
            <div className="mono" style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, letterSpacing: '.06em', textTransform: 'uppercase' }}><span>{t.road.nextT}</span><span style={{ color: 'var(--muted)' }}>{t.road.proposed}</span></div>
            <ul style={{ listStyle: 'none', margin: '16px 0 0', padding: 0 }}>
              {t.road.next.map((b) => (
                <li key={b} style={{ display: 'flex', gap: 12, padding: '11px 0', borderTop: '1px solid var(--line)', fontSize: 15, lineHeight: 1.45 }}>
                  <span aria-hidden="true" style={{ flex: '0 0 auto', width: 16, height: 16, marginTop: 2, borderRadius: 4, border: '1px solid var(--dash)', boxSizing: 'border-box' }} /><span>{b}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

export function Close() {
  const { t, openDemo } = useSite()
  const footT = { fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--bg)', marginBottom: 8 } as const
  return (
    <footer id="contact" style={{ background: 'var(--ink)', color: 'var(--bg)' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: 'clamp(88px,12vw,160px) var(--gutter) 56px', boxSizing: 'border-box' }}>
        <h2 className="serif" style={{ fontWeight: 400, fontSize: 'clamp(44px,7vw,96px)', lineHeight: 0.98, letterSpacing: '-.03em', margin: 0, maxWidth: '14ch' }}>
          <span style={{ display: 'block' }}>{t.close.t1}</span>
          <span style={{ display: 'block', fontStyle: 'italic' }}>{t.close.t2}</span>
        </h2>
        <p style={{ fontSize: 17, lineHeight: 1.6, color: '#C9C8C0', maxWidth: '48ch', margin: '28px 0 0' }}>{t.close.body}</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 34 }}>
          <a className="btn btn-light" href={GITHUB_URL} target="_blank" rel="noopener">{t.hero.gh} <span aria-hidden="true">↗</span></a>
          <button type="button" className="btn btn-ghost-dark" onClick={openDemo}><span aria-hidden="true" className="tri">▶</span> {t.hero.demo}</button>
        </div>
        <div style={{ marginTop: 'clamp(64px,9vw,120px)', paddingTop: 24, borderTop: '1px solid #34332D', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,260px),1fr))', gap: '20px 40px', fontSize: 13.5, lineHeight: 1.55, color: '#B3B2A9' }}>
          <div><div style={footT}>{t.foot.contactT}</div><a href="https://github.com/Furkanturan8" target="_blank" rel="noopener" style={{ color: 'var(--bg)' }}>github.com/Furkanturan8</a></div>
          <div><div style={footT}>{t.foot.demoT}</div>{t.foot.a}</div>
          <div><div style={footT}>{t.foot.adviceT}</div>{t.foot.b}</div>
        </div>
      </div>
    </footer>
  )
}
