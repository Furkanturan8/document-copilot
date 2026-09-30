import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { GITHUB_URL, T, type CiteId, type Lang } from './content'
import { DemoModal, SourcePanel } from './Overlays'
import { SiteContext, useIsMobile, useReducedMotion, useSite, type Site } from './site'
import { Architecture } from './sections/Architecture'
import { Close, Roadmap } from './sections/Close'
import { Flow } from './sections/Flow'
import { Hero } from './sections/Hero'
import { Jev } from './sections/Jev'
import { Limits } from './sections/Limits'
import { OpenSource } from './sections/OpenSource'
import { Problem } from './sections/Problem'
import { Proof } from './sections/Proof'
import { Recordings } from './sections/Recordings'
import { Verify } from './sections/Verify'

const LANG_KEY = 'dc-copilot-lang'

function readLang(): Lang {
  try {
    const l = localStorage.getItem(LANG_KEY)
    if (l === 'en' || l === 'tr') return l
  } catch { /* storage blocked */ }
  return 'en'
}

function Header({ setLang }: { setLang: (l: Lang) => void }) {
  const { t, lang } = useSite()
  return (
    <header className="site-header">
      <div className="inner">
        <a href="#top" className="brand"><img className="brand-mark" src="favicon.svg" alt="" width="24" height="24" /><span>Document Copilot</span></a>
        <nav className="nav">
          <a href="#how">{t.nav.how}</a>
          <a href="#source">{t.nav.source}</a>
          <a href="#jev">{t.nav.jev}</a>
          <a href="#proof">{t.nav.proof}</a>
          <a href={GITHUB_URL} target="_blank" rel="noopener" className="strong">{t.nav.github} ↗</a>
        </nav>
        <div role="group" aria-label="Language" className="toggle lang">
          <button type="button" aria-pressed={lang === 'en'} onClick={() => setLang('en')}>EN</button>
          <button type="button" aria-pressed={lang === 'tr'} onClick={() => setLang('tr')}>TR</button>
        </div>
      </div>
    </header>
  )
}

export default function App() {
  const [lang, setLangState] = useState<Lang>(readLang)
  const mobile = useIsMobile()
  const reduced = useReducedMotion()
  const [panelOpen, setPanelOpen] = useState(false)
  const [panelCite, setPanelCite] = useState<CiteId>('nvda1')
  const [demoOpen, setDemoOpen] = useState(false)
  const lastFocus = useRef<HTMLElement | null>(null)

  const setLang = (l: Lang) => {
    setLangState(l)
    try { localStorage.setItem(LANG_KEY, l) } catch { /* storage blocked */ }
  }

  useEffect(() => { document.documentElement.lang = lang }, [lang])

  const openPanel = useCallback((cite: CiteId) => {
    lastFocus.current = document.activeElement as HTMLElement | null
    setPanelCite(cite)
    setPanelOpen(true)
  }, [])

  const closePanel = useCallback(() => {
    setPanelOpen(false)
    const f = lastFocus.current
    if (f) window.setTimeout(() => f.focus({ preventScroll: true }), 30)
  }, [])

  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (panelOpen) closePanel()
      if (demoOpen) setDemoOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [panelOpen, demoOpen, closePanel])

  const site = useMemo<Site>(() => ({
    t: T[lang], lang, mobile, reduced,
    paused: panelOpen || demoOpen,
    activeCite: panelOpen ? panelCite : null,
    openPanel,
    openDemo: () => setDemoOpen(true),
  }), [lang, mobile, reduced, panelOpen, demoOpen, panelCite, openPanel])

  return (
    <SiteContext.Provider value={site}>
      <Header setLang={setLang} />
      <main>
        <Hero />
        <Problem />
        <Flow />
        <OpenSource />
        <Verify />
        <Jev />
        <Limits />
        <Recordings />
        <Proof />
        <Architecture />
        <Roadmap />
      </main>
      <Close />
      <SourcePanel open={panelOpen} cite={panelCite} onClose={closePanel} />
      {demoOpen && <DemoModal onClose={() => setDemoOpen(false)} />}
    </SiteContext.Provider>
  )
}
