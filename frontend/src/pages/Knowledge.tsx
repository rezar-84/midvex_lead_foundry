import { useSearchParams } from "react-router"

import { useKnowledge } from "@/api/queries"
import { EmptyState, PageHeader, Pagination } from "@/components/shared"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function KnowledgePage() {
  const [params, setParams] = useSearchParams()
  const page = Number(params.get("page") ?? "1")
  const { data, isPending } = useKnowledge(page)

  return (
    <div className="space-y-6">
      <PageHeader title="Knowledge" />
      {isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((company) => (
              <Card key={company.id}>
                <CardHeader>
                  <CardTitle className="text-base">{company.name}</CardTitle>
                  {company.domain ? (
                    <CardDescription>{company.domain}</CardDescription>
                  ) : null}
                </CardHeader>
                <CardContent>
                  {company.contacts.length > 0 ? (
                    <ul className="space-y-1.5 text-sm">
                      {company.contacts.map((contact) => (
                        <li key={contact.id}>
                          <span className="font-medium">
                            {contact.display_name || contact.primary_email}
                          </span>
                          {contact.display_name && contact.primary_email ? (
                            <span className="text-muted-foreground">
                              {" "}
                              · {contact.primary_email}
                            </span>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground">No linked contacts.</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
          <Pagination
            page={page}
            data={data}
            onPageChange={(next) => setParams({ page: String(next) })}
          />
        </>
      ) : (
        <EmptyState title="No companies yet">
          Companies and contacts appear here as analysis extracts them from conversations.
        </EmptyState>
      )}
    </div>
  )
}
