import { Badge } from '@/components/ui/badge'
import { Markdown } from '@/components/ui/markdown'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import type { CitationPayload } from '@/lib/citations'
import { cn } from '@/lib/utils'

const PASSAGE_CLASSES = cn(
  'space-y-2 text-sm leading-relaxed',
  '[&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4',
  '[&_table]:w-full [&_table]:border-collapse [&_table]:text-left [&_table]:text-xs',
  '[&_th]:border [&_th]:bg-muted [&_th]:px-2 [&_th]:py-1.5 [&_th]:font-semibold',
  '[&_td]:border [&_td]:px-2 [&_td]:py-1.5 [&_td]:align-top',
)

type SourcePassageSheetProps = {
  citation: CitationPayload | null
  onClose: () => void
}

export function SourcePassageSheet({ citation, onClose }: SourcePassageSheetProps) {
  return (
    <Sheet open={citation !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 sm:max-w-xl">
        {citation && (
          <>
            <SheetHeader className="border-b">
              <div className="flex items-center gap-2 pr-8">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground tabular-nums">
                  {citation.citationIndex}
                </span>
                <SheetTitle className="truncate text-base">{citation.companyName ?? citation.ticker}</SheetTitle>
              </div>
              <SheetDescription className="sr-only">Source passage for citation {citation.citationIndex}</SheetDescription>
              <div className="flex flex-wrap gap-1.5 pt-1">
                <Badge variant="secondary">{citation.ticker}</Badge>
                <Badge variant="outline">{citation.form}</Badge>
                {citation.fiscalYear && <Badge variant="outline">FY {citation.fiscalYear}</Badge>}
                <Badge variant="outline">Filed {citation.filingDate}</Badge>
                {citation.page && <Badge variant="outline">Page {citation.page}</Badge>}
                {citation.section && <Badge variant="outline">{citation.section}</Badge>}
              </div>
            </SheetHeader>

            <div className="flex-1 overflow-y-auto p-4">
              <p className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">Cited passage</p>
              <blockquote className="overflow-x-auto rounded-xl border border-primary/30 bg-primary/5 p-4">
                <Markdown className={PASSAGE_CLASSES}>{citation.excerpt}</Markdown>
              </blockquote>
              <p className="mt-3 text-xs text-muted-foreground">
                Quoted verbatim from the filing and checked against the retrieved passage before the answer was shown.
              </p>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
