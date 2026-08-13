import { ArrowRight } from "lucide-react"
import { useSearchParams } from "react-router"

import { useDecideMergeSuggestion, useMergeSuggestions } from "@/api/queries"
import type { ContactRef } from "@/api/types"
import { CapabilityGate } from "@/components/CapabilityGate"
import { EmptyState, PageHeader, Pagination, formatDateTime } from "@/components/shared"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

const REASON_LABELS: Record<string, string> = {
  same_name: "Same display name, different email",
  same_email_local_part: "Same email local part, different domain",
}

function ContactCard({ contact, label }: { contact: ContactRef; label: string }) {
  return (
    <div className="neu-inset flex-1 space-y-0.5 p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="font-medium">{contact.display_name || "(no name)"}</p>
      <p className="text-sm text-muted-foreground">{contact.primary_email || "(no email)"}</p>
      {contact.company_name ? (
        <p className="text-xs text-muted-foreground">{contact.company_name}</p>
      ) : null}
    </div>
  )
}

export function DataQualityPage() {
  const [params, setParams] = useSearchParams()
  const status = params.get("status") ?? "pending"
  const page = Number(params.get("page") ?? "1")
  const { data, isPending } = useMergeSuggestions(status, page)
  const decide = useDecideMergeSuggestion()

  return (
    <div className="space-y-6">
      <PageHeader title="Data quality" />
      <p className="max-w-2xl text-sm text-muted-foreground">
        The dedup job merges exact email duplicates automatically and lists fuzzy matches here
        for review. Run it from a project's operations page. Accepting a suggestion merges the
        duplicate into the primary contact; every merge is audit logged.
      </p>
      <nav aria-label="Status filter" className="flex w-fit gap-1 rounded-lg bg-muted p-1">
        {["pending", "rejected"].map((item) => (
          <button
            key={item}
            onClick={() => setParams({ status: item })}
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
      {isPending || !data ? (
        <Skeleton className="h-64 w-full" />
      ) : data.items.length === 0 ? (
        <EmptyState title="No merge suggestions">
          {status === "pending"
            ? "Run a dedup job from a project to scan for duplicate contacts."
            : "No rejected suggestions."}
        </EmptyState>
      ) : (
        <>
          <div className="space-y-4">
            {data.items.map((suggestion) => (
              <div key={suggestion.id} className="neu-raised space-y-4 p-5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Badge variant="secondary">
                    {REASON_LABELS[suggestion.reason] ?? suggestion.reason}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    Suggested {formatDateTime(suggestion.created_at)}
                  </span>
                </div>
                <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
                  <ContactCard contact={suggestion.primary} label="Keep (primary)" />
                  <ArrowRight
                    className="hidden size-5 shrink-0 text-muted-foreground sm:block"
                    aria-hidden
                  />
                  <ContactCard contact={suggestion.duplicate} label="Merge away (duplicate)" />
                </div>
                {suggestion.status === "pending" ? (
                  <CapabilityGate capability="review">
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        disabled={decide.isPending}
                        onClick={() =>
                          decide.mutate({ id: suggestion.id, decision: "accepted" })
                        }
                      >
                        Merge
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={decide.isPending}
                        onClick={() =>
                          decide.mutate({ id: suggestion.id, decision: "rejected" })
                        }
                      >
                        Not a duplicate
                      </Button>
                    </div>
                  </CapabilityGate>
                ) : null}
              </div>
            ))}
          </div>
          {decide.isError ? (
            <p className="text-sm text-destructive">{decide.error.message}</p>
          ) : null}
          <Pagination
            page={page}
            data={data}
            onPageChange={(next) => setParams({ status, page: String(next) })}
          />
        </>
      )}
    </div>
  )
}
