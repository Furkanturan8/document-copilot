import { HERO, INSUFFICIENT, JEVQ, type CiteId } from './content'

// One chat turn as the running app showed it in docs/media.
export interface Turn {
  q: string
  answer: string
  status?: string // "Searching SEC filings… (…)" line, only where the recording shows it
  think?: number // ms of bare "thinking" dot when no status line was recorded
  chips?: string[]
  marks?: { at: number; m: string }[] // citation superscripts, by character offset in `answer`
  noSources?: boolean
}

export interface Replay {
  turns: Turn[]
  // The chip that gets clicked at the end, opening the source panel (as in the recording).
  panel?: { cite: CiteId; chip: number }
}

function heroTurn(i: number): Turn {
  let at = 0
  const marks: { at: number; m: string }[] = []
  for (const sg of HERO[i].segs) {
    at += sg.t.length
    if (sg.m) marks.push({ at, m: sg.m })
  }
  return { q: HERO[i].q, status: HERO[i].status, answer: HERO[i].segs.map((s) => s.t).join(''), marks, chips: HERO[i].chips.map((c) => c.label) }
}
const jevTurn = (i: number): Turn => ({ q: JEVQ[i].q, answer: JEVQ[i].reply, think: 500, noSources: true })

// Same order as the MediaItem list in content.ts.
export const REPLAYS: Replay[] = [
  { turns: [heroTurn(0)], panel: { cite: 'nvda1', chip: 0 } },
  { turns: [heroTurn(1)], panel: { cite: 'aapl24', chip: 0 } },
  { turns: [heroTurn(2)] },
  { turns: [jevTurn(1), jevTurn(2)] },
  { turns: [jevTurn(3)] },
  { turns: [{ q: JEVQ[4].q, answer: INSUFFICIENT, think: 1800, noSources: true }] },
]

export const TYPE_MS = 38
export const STREAM_MS = 12
const STATUS_MS = 1800

export interface TurnPlan { typeStart: number; sent: number; answerStart: number; answerEnd: number; extrasAt: number }
export interface ReplayPlan { turns: TurnPlan[]; pressAt?: number; panelAt?: number; dur: number }

export function planReplay(r: Replay): ReplayPlan {
  let t = 500
  const turns = r.turns.map((tu) => {
    const typeStart = t
    const sent = typeStart + tu.q.length * TYPE_MS + 300
    const answerStart = sent + (tu.status ? STATUS_MS : tu.think ?? 600)
    const answerEnd = answerStart + tu.answer.length * STREAM_MS
    const extrasAt = answerEnd + 150
    t = extrasAt + 1200
    return { typeStart, sent, answerStart, answerEnd, extrasAt }
  })
  if (!r.panel) return { turns, dur: t + 2300 }
  const pressAt = t
  const panelAt = t + 350
  return { turns, pressAt, panelAt, dur: panelAt + 5000 }
}

export const PLANS = REPLAYS.map(planReplay)
