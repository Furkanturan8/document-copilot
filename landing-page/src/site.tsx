import { createContext, Fragment, useContext, useEffect, useRef, useState } from 'react'
import type { CiteId, Dict, HeroQuestion, Lang } from './content'

export interface Site {
  t: Dict
  lang: Lang
  mobile: boolean
  reduced: boolean
  // True while the source panel or demo modal covers the page, so loops hold still.
  paused: boolean
  activeCite: CiteId | null
  openPanel: (cite: CiteId) => void
  openDemo: () => void
}

export const SiteContext = createContext<Site | null>(null)

export function useSite(): Site {
  const s = useContext(SiteContext)
  if (!s) throw new Error('useSite outside SiteContext')
  return s
}

export const clamp01 = (v: number) => Math.max(0, Math.min(1, v))

export function useReducedMotion(): boolean {
  const [reduced] = useState(() => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false)
  return reduced
}

export function useIsMobile(): boolean {
  const [mobile, setMobile] = useState(() => window.innerWidth < 760)
  useEffect(() => {
    const on = () => setMobile(window.innerWidth < 760)
    window.addEventListener('resize', on)
    return () => window.removeEventListener('resize', on)
  }, [])
  return mobile
}

// Calls fn at most once per frame on scroll/resize, and once on mount.
export function useScrollFrame(fn: () => void) {
  const ref = useRef(fn)
  useEffect(() => { ref.current = fn })
  useEffect(() => {
    let raf = 0
    const on = () => {
      if (raf) return
      raf = requestAnimationFrame(() => { raf = 0; ref.current() })
    }
    on()
    window.addEventListener('scroll', on, { passive: true })
    window.addEventListener('resize', on)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('scroll', on)
      window.removeEventListener('resize', on)
    }
  }, [])
}

// setTimeout handles that are all cleared on unmount or on the next schedule() reset.
export function useTimers() {
  const ids = useRef<number[]>([])
  useEffect(() => () => ids.current.forEach(clearTimeout), [])
  return {
    reset: () => { ids.current.forEach(clearTimeout); ids.current = [] },
    at: (fn: () => void, ms: number) => { ids.current.push(window.setTimeout(fn, ms)) },
  }
}

export interface SegView { text: string; mark: string; on: boolean; under: boolean; c: number }

export function buildSegs(q: HeroQuestion, chars: number, isActive: (c: number) => boolean): SegView[] {
  let pos = 0
  return q.segs.map((sg) => {
    const n = Math.max(0, Math.min(sg.t.length, chars - pos))
    pos += sg.t.length
    const a = isActive(sg.c)
    return { c: sg.c, text: sg.t.slice(0, n), mark: sg.m && n === sg.t.length ? sg.m : '', on: a && !!sg.f, under: a }
  })
}

export function AnswerText({ segs, onPick, slow }: { segs: SegView[]; onPick?: (c: number) => void; slow?: boolean }) {
  return (
    <>
      {segs.map((s, i) => (
        <Fragment key={i}>
          <span
            className={'hl' + (s.on ? ' on' : '')}
            style={{ textDecorationLine: s.under ? 'underline' : 'none', cursor: onPick ? 'pointer' : undefined, transitionDuration: slow ? '.7s' : undefined, textUnderlineOffset: slow ? 5 : undefined }}
            onMouseEnter={onPick && (() => onPick(s.c))}
            onClick={onPick && (() => onPick(s.c))}
          >
            {s.text}
          </span>
          {s.mark && <sup className="sup" style={slow ? { fontSize: 11 } : undefined}>{s.mark}</sup>}
        </Fragment>
      ))}
    </>
  )
}

export function Chip({ n, label, on, onClick, onFocus }: { n: string; label: string; on?: boolean; onClick: () => void; onFocus?: () => void }) {
  return (
    <button type="button" className={'chip' + (on ? ' on' : '')} onClick={onClick} onFocus={onFocus} aria-pressed={onFocus ? !!on : undefined}>
      <span className="chip-n">{n}</span>
      <span>{label}</span>
    </button>
  )
}
