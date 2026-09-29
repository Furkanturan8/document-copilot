import { isDataUIPart, type UIMessage } from 'ai'

// Mirrors the `data-citation` part built by backend/app/chat/messages.py::citation_part.
export type CitationPayload = {
  citationIndex: number
  chunkId: string
  excerpt: string
  ticker: string
  companyName: string | null
  form: string
  filingDate: string
  fiscalYear: number | null
  page: string | null
  section: string | null
}

// Transient `data-status` parts from backend/app/assistant/status.py.
export type PipelineStatus = {
  stage: 'analyzing' | 'searching' | 'reading' | 'verifying'
  message: string
}

type Part = UIMessage['parts'][number]

function isCitationData(data: unknown): data is CitationPayload {
  if (typeof data !== 'object' || data === null) return false
  const record = data as Record<string, unknown>
  return (
    typeof record.citationIndex === 'number' &&
    typeof record.chunkId === 'string' &&
    typeof record.excerpt === 'string' &&
    typeof record.ticker === 'string' &&
    typeof record.form === 'string' &&
    typeof record.filingDate === 'string'
  )
}

function isCitationPart(part: Part): part is Part & { type: 'data-citation'; data: CitationPayload } {
  return isDataUIPart(part) && part.type === 'data-citation' && isCitationData(part.data)
}

export function isPipelineStatus(data: unknown): data is PipelineStatus {
  if (typeof data !== 'object' || data === null) return false
  const record = data as Record<string, unknown>
  return typeof record.stage === 'string' && typeof record.message === 'string'
}

export function citationsFromMessage(message: UIMessage): CitationPayload[] {
  return message.parts
    .filter(isCitationPart)
    .map((part) => part.data)
    .sort((a, b) => a.citationIndex - b.citationIndex)
}

export function citationLabel(citation: CitationPayload): string {
  const parts = [citation.ticker, citation.form, citation.filingDate]
  if (citation.page) parts.push(`p.${citation.page}`)
  return parts.join(' · ')
}
