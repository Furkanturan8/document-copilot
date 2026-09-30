import { useSite } from '../site'

export function Proof() {
  const { t } = useSite()
  return (
    <section id="proof" className="section alt">
      <div className="wrap">
        <div className="head-row">
          <div>
            <div className="kicker">{t.proof.k}</div>
            <h2 className="h2">{t.proof.title}</h2>
          </div>
          <p className="lead" style={{ maxWidth: '50ch', margin: 0 }}>{t.proof.body}</p>
        </div>

        <div style={{ marginTop: 48, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,240px),1fr))', borderTop: '1px solid var(--ink)' }}>
          {t.proof.big.map((b) => (
            <div key={b.v} style={{ padding: '26px 24px 28px 0', borderBottom: '1px solid var(--line3)' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px 14px' }}>
                <span className="serif" style={{ fontSize: 'clamp(48px,6vw,76px)', lineHeight: 1, letterSpacing: '-.02em', fontVariantNumeric: 'tabular-nums' }}>{b.v}</span>
                <span className="mono" style={{ background: 'var(--hl)', borderRadius: 999, padding: '5px 11px', fontSize: 12, whiteSpace: 'nowrap' }}>{b.tag}</span>
              </div>
              <div style={{ marginTop: 12, fontSize: 15, lineHeight: 1.45, color: 'var(--body)', maxWidth: '28ch' }}>{b.l}</div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 40, overflowX: 'auto' }}>
          <table style={{ width: '100%', minWidth: 620, borderCollapse: 'collapse', fontSize: 14.5 }}>
            <thead>
              <tr className="mono" style={{ borderBottom: '1px solid var(--ink)', fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--muted)' }}>
                <th style={{ textAlign: 'left', fontWeight: 400, padding: '10px 16px 10px 0' }}>{t.proof.h1}</th>
                <th style={{ textAlign: 'right', fontWeight: 400, padding: '10px 24px 10px 0' }}>{t.proof.h2}</th>
                <th style={{ textAlign: 'left', fontWeight: 400, padding: '10px 0' }}>{t.proof.h3}</th>
              </tr>
            </thead>
            <tbody>
              {t.proof.rows.map((r) => (
                <tr key={r.m} style={{ borderBottom: '1px solid var(--line3)' }}>
                  <td style={{ padding: '14px 16px 14px 0', verticalAlign: 'top' }}>{r.m}</td>
                  <td className="mono" style={{ padding: '14px 24px 14px 0', textAlign: 'right', whiteSpace: 'nowrap', fontSize: 14, fontVariantNumeric: 'tabular-nums', verticalAlign: 'top' }}>{r.v}</td>
                  <td style={{ padding: '14px 0', color: 'var(--body)', verticalAlign: 'top' }}>{r.c}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ marginTop: 48 }}>
          <div className="label">{t.proof.checkedT}</div>
          <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,260px),1fr))', gap: 12 }}>
            {t.proof.checked.map((c) => (
              <div key={c.l} style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 12, padding: '18px 20px', display: 'flex', gap: 14, alignItems: 'flex-start' }}>
                <span className="check-dot" style={{ width: 20, height: 20, borderRadius: 5, fontSize: 12 }}>✓</span>
                <div>
                  <div style={{ fontSize: 13.5, color: 'var(--body)' }}>{c.l}</div>
                  <div className="mono" style={{ marginTop: 4, fontSize: 17, fontVariantNumeric: 'tabular-nums' }}>{c.v}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
