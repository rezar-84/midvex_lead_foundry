import type { ReactNode } from "react"

import type { OpportunityStatus, Page } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

const STATUS_VARIANTS: Record<OpportunityStatus, string> = {
  pending: "bg-secondary text-secondary-foreground",
  accepted: "bg-primary text-primary-foreground",
  rejected: "bg-destructive text-white",
  deferred: "bg-muted text-muted-foreground",
}

export function StatusBadge({ status }: { status: OpportunityStatus }) {
  return <Badge className={STATUS_VARIANTS[status]}>{status}</Badge>
}

export function formatDateTime(value: string | null): string {
  if (!value) return "Unknown"
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

export function Pagination({
  page,
  data,
  onPageChange,
}: {
  page: number
  data: Pick<Page<unknown>, "pages" | "count"> | undefined
  onPageChange: (page: number) => void
}) {
  if (!data || data.pages <= 1) return null
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between pt-2">
      <Button
        variant="outline"
        size="sm"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </Button>
      <span className="text-sm text-muted-foreground">
        Page {page} of {data.pages} ({data.count} total)
      </span>
      <Button
        variant="outline"
        size="sm"
        disabled={page >= data.pages}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </Button>
    </nav>
  )
}

export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <CardContent className="py-10 text-center">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{children}</p>
      </CardContent>
    </Card>
  )
}

export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
      {children}
    </div>
  )
}
