import { useMemo } from 'react'
import type { Components } from 'react-markdown'

import { CitationMarker } from '@/components/chat/CitationMarker'
import { Markdown } from '@/components/ui/markdown'
import type { CitationPayload } from '@/lib/citations'
import { cn } from '@/lib/utils'

const CITE_PREFIX = '#citation-'

// Child-targeting utilities style the rendered markdown without the typography plugin.
const MARKDOWN_CLASSES = cn(
  'space-y-3 text-sm leading-relaxed',
  '[&_strong]:font-semibold [&_a]:font-medium [&_a]:underline [&_a]:underline-offset-4',
  '[&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-1',
  '[&_h1]:text-base [&_h1]:font-semibold [&_h2]:text-base [&_h2]:font-semibold [&_h3]:text-sm [&_h3]:font-semibold',
  '[&_table]:w-full [&_table]:text-left [&_th]:border-b [&_th]:py-1.5 [&_th]:pr-3 [&_th]:font-semibold',
  '[&_td]:border-b [&_td]:py-1.5 [&_td]:pr-3 [&_td]:align-top',
  '[&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground',
)

// Turns "[2]" into a markdown link that the `a` renderer below swaps for a CitationMarker.
function withCitationLinks(text: string, validIndices: Set<number>): string {
  return text.replace(/\[(\d+)\]/g, (match, digits: string) =>
    validIndices.has(Number(digits)) ? `[${match}](${CITE_PREFIX}${digits})` : match,
  )
}

type AssistantMarkdownProps = {
  text: string
  citations: CitationPayload[]
  selectedCitationIndex: number | null
  onSelectCitation: (citation: CitationPayload) => void
}

export function AssistantMarkdown({ text, citations, selectedCitationIndex, onSelectCitation }: AssistantMarkdownProps) {
  const source = useMemo(
    () => withCitationLinks(text, new Set(citations.map((citation) => citation.citationIndex))),
    [text, citations],
  )

  const components = useMemo<Partial<Components>>(
    () => ({
      a({ href, children }) {
        const citation = href?.startsWith(CITE_PREFIX)
          ? citations.find((item) => item.citationIndex === Number(href.slice(CITE_PREFIX.length)))
          : undefined
        if (citation) {
          return (
            <CitationMarker
              index={citation.citationIndex}
              selected={selectedCitationIndex === citation.citationIndex}
              onSelect={() => onSelectCitation(citation)}
            />
          )
        }
        return (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        )
      },
    }),
    [citations, selectedCitationIndex, onSelectCitation],
  )

  // Markdown blocks only re-render when their text changes, so a new selection remounts them.
  return (
    <Markdown key={selectedCitationIndex ?? 'none'} className={MARKDOWN_CLASSES} components={components}>
      {source}
    </Markdown>
  )
}
