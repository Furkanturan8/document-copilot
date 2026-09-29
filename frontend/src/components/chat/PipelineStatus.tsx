import type { PipelineStatus as PipelineStatusState } from '@/lib/citations'
import { cn } from '@/lib/utils'

export function PipelineStatus({ status }: { status: PipelineStatusState | null }) {
  return (
    <p
      aria-live="polite"
      className={cn(
        'w-fit bg-clip-text text-sm font-medium text-transparent',
        'bg-[linear-gradient(to_right,var(--muted-foreground)_35%,var(--foreground)_50%,var(--muted-foreground)_65%)]',
        'animate-[shimmer_2.5s_linear_infinite] bg-size-[200%_auto]',
      )}
    >
      {status?.message ?? 'Analyzing your question…'}
    </p>
  )
}
