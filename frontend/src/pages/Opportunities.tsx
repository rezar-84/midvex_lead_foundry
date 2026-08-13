import { Download } from "lucide-react"
import { Link, useSearchParams } from "react-router"

import { useOpportunities } from "@/api/queries"
import type { OpportunityStatus } from "@/api/types"
import { CapabilityGate } from "@/components/CapabilityGate"
import {
  EmptyState,
  PageHeader,
  Pagination,
  StatusBadge,
  formatDateTime,
} from "@/components/shared"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

const STATUSES: OpportunityStatus[] = ["pending", "accepted", "rejected", "deferred"]

function cookie(name: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : ""
}

function ExportButton() {
  // The CSV download stays a plain Django POST endpoint; a form submit keeps
  // the browser's native file-download behaviour.
  return (
    <form method="post" action="/exports/csv/">
      <input type="hidden" name="csrfmiddlewaretoken" value={cookie("csrftoken")} />
      <Button type="submit" variant="outline" size="sm" className="gap-1.5">
        <Download className="size-4" aria-hidden />
        Export accepted (CSV)
      </Button>
    </form>
  )
}

export function OpportunitiesPage() {
  const [params, setParams] = useSearchParams()
  const status = (params.get("status") ?? "pending") as OpportunityStatus
  const page = Number(params.get("page") ?? "1")
  const { data, isPending } = useOpportunities(status, page)

  const setFilter = (next: Partial<{ status: string; page: number }>) => {
    const merged = new URLSearchParams(params)
    if (next.status !== undefined) {
      merged.set("status", next.status)
      merged.delete("page")
    }
    if (next.page !== undefined) merged.set("page", String(next.page))
    setParams(merged)
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Opportunities">
        <CapabilityGate capability="export">
          <ExportButton />
        </CapabilityGate>
      </PageHeader>
      <nav aria-label="Status filter" className="flex gap-1 rounded-lg bg-muted p-1 w-fit">
        {STATUSES.map((item) => (
          <button
            key={item}
            onClick={() => setFilter({ status: item })}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm capitalize transition-colors",
              item === status
                ? "bg-card font-medium shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {item}
          </button>
        ))}
      </nav>
      {isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : data && data.items.length > 0 ? (
        <>
          <Card>
            <CardContent className="overflow-x-auto p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Candidate</TableHead>
                    <TableHead>Signal</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last communication</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <Link
                          className="font-medium hover:underline"
                          to={`/opportunities/${item.id}`}
                        >
                          {item.title}
                        </Link>
                      </TableCell>
                      <TableCell className="max-w-md truncate text-muted-foreground">
                        {item.reason}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={item.status} />
                      </TableCell>
                      <TableCell>{formatDateTime(item.last_communication_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          <Pagination page={page} data={data} onPageChange={(next) => setFilter({ page: next })} />
        </>
      ) : (
        <EmptyState title="No candidates in this view">
          Candidates appear here after a source sync; switch status filters to see decided ones.
        </EmptyState>
      )}
    </div>
  )
}
