import { cn } from '@/lib/utils'

type CitationMarkerProps = {
  index: number
  selected: boolean
  onSelect: () => void
}

export function CitationMarker({ index, selected, onSelect }: CitationMarkerProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-label={`Show source ${index}`}
      className={cn(
        'mx-0.5 inline-flex h-4 min-w-4 -translate-y-1 items-center justify-center rounded px-1 align-baseline text-[0.65rem] font-semibold tabular-nums transition-colors',
        selected
          ? 'bg-primary text-primary-foreground'
          : 'bg-muted text-muted-foreground hover:bg-primary hover:text-primary-foreground',
      )}
    >
      {index}
    </button>
  )
}
