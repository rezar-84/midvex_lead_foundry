import { CheckCircle2, Inbox, MessagesSquare } from "lucide-react"
import type { ReactNode } from "react"
import { Link } from "react-router"

import { useDashboard } from "@/api/queries"
import { EmptyState, StatusBadge, formatDateTime } from "@/components/shared"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

function Metric({
  label,
  value,
  icon,
}: {
  label: string
  value: number | undefined
  icon: ReactNode
}) {
  return (
    <div className="neu-raised flex items-center gap-5 p-6">
      <div className="neu-inset flex size-14 shrink-0 items-center justify-center rounded-full text-primary">
        {icon}
      </div>
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-4xl font-bold tabular-nums tracking-tight">
          {value === undefined ? <Skeleton className="h-9 w-16" /> : value}
        </p>
      </div>
    </div>
  )
}

export function DashboardPage() {
  const { data, isPending } = useDashboard()

  return (
    <div className="space-y-10">
      <div>
        <p className="text-xs font-extrabold uppercase tracking-[0.13em] text-primary">
          Workspace
        </p>
        <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
      </div>
      <div className="grid gap-8 sm:grid-cols-3">
        <Metric
          label="Pending candidates"
          value={data?.pending_count}
          icon={<Inbox className="size-6" aria-hidden />}
        />
        <Metric
          label="Accepted"
          value={data?.accepted_count}
          icon={<CheckCircle2 className="size-6" aria-hidden />}
        />
        <Metric
          label="Conversations"
          value={data?.conversation_count}
          icon={<MessagesSquare className="size-6" aria-hidden />}
        />
      </div>
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Recent candidates</h2>
        {isPending ? (
          <Skeleton className="h-40 w-full" />
        ) : data && data.recent.length > 0 ? (
          <div className="neu-raised overflow-x-auto p-2">
            <Table>
              <TableHeader>
                <TableRow className="border-0 hover:bg-transparent">
                  <TableHead>Candidate</TableHead>
                  <TableHead>Signal</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last communication</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.recent.map((item) => (
                  <TableRow key={item.id} className="border-border/50">
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
          </div>
        ) : (
          <EmptyState title="No candidates yet">
            Candidates appear here after a source sync and analysis run.
          </EmptyState>
        )}
      </section>
    </div>
  )
}
