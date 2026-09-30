import { INSUFFICIENT } from '../content'
import { useSite } from '../site'

export function Limits() {
  const { t } = useSite()
  return (
    <section id="limits" className="section alt">
      <div className="wrap cols" style={{ alignItems: 'center' }}>
        <div>
          <div className="kicker">{t.unknown.k}</div>
          <h2 className="h2">{t.unknown.title}</h2>
          <p className="lead" style={{ maxWidth: '46ch' }}>{t.unknown.body}</p>
        </div>
        <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="bubble" style={{ maxWidth: '90%' }}>What were Apple's quarterly results for Q3 fiscal 2024?</div>
          <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.65 }}>{INSUFFICIENT}</p>
          <div><span className="no-src">{t.unknown.noSources}</span></div>
        </div>
      </div>
    </section>
  )
}
