import { useSearchParams } from "react-router"

import { useConversations } from "@/api/queries"
import { EmptyState, PageHeader, Pagination, formatDateTime } from "@/components/shared"
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

export function ConversationsPage() {
  const [params, setParams] = useSearchParams()
  const page = Number(params.get("page") ?? "1")
  const { data, isPending } = useConversations(page)

  return (
    <div className="space-y-6">
      <PageHeader title="Conversations" />
      {isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : data && data.items.length > 0 ? (
        <>
          <Card>
            <CardContent className="overflow-x-auto p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Subject</TableHead>
                    <TableHead>Last message</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">
                        {item.subject || "(no subject)"}
                      </TableCell>
                      <TableCell>{formatDateTime(item.last_message_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          <Pagination
            page={page}
            data={data}
            onPageChange={(next) => setParams({ page: String(next) })}
          />
        </>
      ) : (
        <EmptyState title="No conversations yet">
          Conversations appear here after a mailbox sync.
        </EmptyState>
      )}
    </div>
  )
}
