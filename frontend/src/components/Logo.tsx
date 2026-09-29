import { FileSearch } from 'lucide-react'

import { cn } from '@/lib/utils'

export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground',
        className,
      )}
    >
      <FileSearch className="size-[55%]" />
    </span>
  )
}

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <LogoMark />
      <div className="flex flex-col leading-none">
        <span className="text-sm font-semibold tracking-tight">Document Copilot</span>
        <span className="text-xs text-muted-foreground">SEC filing assistant</span>
      </div>
    </div>
  )
}
