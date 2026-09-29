export type RecencyGroup = 'Today' | 'Yesterday' | 'Previous 7 days' | 'Older'

const RECENCY_ORDER: RecencyGroup[] = ['Today', 'Yesterday', 'Previous 7 days', 'Older']
const DAY_MS = 24 * 60 * 60 * 1000

function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()
}

function recencyGroup(isoDate: string): RecencyGroup {
  const today = startOfDay(new Date())
  const day = startOfDay(new Date(isoDate))
  if (day >= today) return 'Today'
  if (day >= today - DAY_MS) return 'Yesterday'
  if (day >= today - 7 * DAY_MS) return 'Previous 7 days'
  return 'Older'
}

export function groupByRecency<T>(items: T[], getDate: (item: T) => string): { label: RecencyGroup; items: T[] }[] {
  const buckets = new Map<RecencyGroup, T[]>()
  for (const item of items) {
    const label = recencyGroup(getDate(item))
    buckets.set(label, [...(buckets.get(label) ?? []), item])
  }
  return RECENCY_ORDER.filter((label) => buckets.has(label)).map((label) => ({ label, items: buckets.get(label)! }))
}
