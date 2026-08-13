import { useState } from "react"
import { Link, useNavigate, useParams, useSearchParams } from "react-router"

import {
  useAssignTag,
  useMe,
  useProjectContact,
  useProjectContacts,
  useReviewEnrichment,
  useStartEnrichment,
  useTags,
} from "@/api/queries"
import { CapabilityGate } from "@/components/CapabilityGate"
import { EmptyState, Pagination, formatDateTime } from "@/components/shared"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ProjectNav } from "./ProjectDetailPage"

function TagChip({ name, color }: { name: string; color: string }) {
  return (
    <span
      className="rounded-full px-2 py-0.5 text-xs font-medium text-white"
      style={{ backgroundColor: color }}
    >
      {name}
    </span>
  )
}

export function ContactsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [params, setParams] = useSearchParams()
  const page = Number(params.get("page") ?? "1")
  const { data, isPending } = useProjectContacts(projectId ?? "", page)
  const { data: tags } = useTags(projectId ?? "")
  const { data: me } = useMe()
  const assign = useAssignTag(projectId ?? "")
  const enrich = useStartEnrichment(projectId ?? "")
  const navigate = useNavigate()

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [tagId, setTagId] = useState("")
  const [budget, setBudget] = useState(25)
  const [confirmScope, setConfirmScope] = useState(false)

  const toggle = (id: string, on: boolean) => {
    const next = new Set(selected)
    if (on) next.add(id)
    else next.delete(id)
    setSelected(next)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Contacts</h1>
      <ProjectNav projectId={projectId ?? ""} active="contacts" />
      {isPending || !data ? (
        <Skeleton className="h-64 w-full" />
      ) : data.items.length === 0 ? (
        <EmptyState title="No contacts yet">
          Contacts appear here after an analysis run extracts them from synced messages.
        </EmptyState>
      ) : (
        <>
          <div className="neu-flat overflow-x-auto p-2">
            <Table>
              <TableHeader>
                <TableRow className="border-0 hover:bg-transparent">
                  <TableHead className="w-8" />
                  <TableHead>Contact</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Messages</TableHead>
                  <TableHead>Last contact</TableHead>
                  <TableHead>Products</TableHead>
                  <TableHead>Tags</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((row) => (
                  <TableRow key={row.id} className="border-border/50">
                    <TableCell>
                      <Checkbox
                        aria-label={`Select ${row.display_name || row.primary_email}`}
                        checked={selected.has(row.id)}
                        onCheckedChange={(checked) => toggle(row.id, checked === true)}
                      />
                    </TableCell>
                    <TableCell>
                      <Link
                        className="font-medium hover:underline"
                        to={`/projects/${projectId}/contacts/${row.id}`}
                      >
                        {row.display_name || row.primary_email}
                      </Link>
                      {row.display_name ? (
                        <p className="text-xs text-muted-foreground">{row.primary_email}</p>
                      ) : null}
                    </TableCell>
                    <TableCell>{row.company_name ?? "—"}</TableCell>
                    <TableCell className="tabular-nums">
                      {row.metric?.contact_count ?? 0}
                    </TableCell>
                    <TableCell>{formatDateTime(row.metric?.last_contact_at ?? null)}</TableCell>
                    <TableCell className="max-w-40 truncate text-sm text-muted-foreground">
                      {row.products.map((product) => product.canonical_name).join(", ") || "—"}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {row.tags.map((tag) => (
                          <TagChip key={tag.id} name={tag.name} color={tag.color} />
                        ))}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <Pagination
            page={page}
            data={data}
            onPageChange={(next) => setParams({ page: String(next) })}
          />
          <div className="grid gap-6 lg:grid-cols-2">
            <CapabilityGate capability="run_batches">
              <div className="neu-raised space-y-3 p-5">
                <h2 className="font-semibold">Assign tag to selected</h2>
                <select
                  aria-label="Tag"
                  className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
                  value={tagId}
                  onChange={(e) => setTagId(e.target.value)}
                >
                  <option value="">Choose a tag…</option>
                  {tags?.map((tag) => (
                    <option key={tag.id} value={tag.id}>
                      {tag.category}: {tag.name}
                    </option>
                  ))}
                </select>
                <Button
                  size="sm"
                  disabled={!tagId || selected.size === 0 || assign.isPending}
                  onClick={() =>
                    assign.mutate(
                      { contact_ids: [...selected], tag_id: tagId },
                      { onSuccess: () => setSelected(new Set()) },
                    )
                  }
                >
                  Assign tag ({selected.size})
                </Button>
                {assign.isError ? (
                  <p className="text-sm text-destructive">{assign.error.message}</p>
                ) : null}
              </div>
            </CapabilityGate>
            {(me?.flags.enrichment_network_enabled ?? false) ? (
              <CapabilityGate capability="run_enrichment">
                <div className="neu-raised space-y-3 p-5">
                  <h2 className="font-semibold">Start enrichment for selected</h2>
                  <div className="space-y-2">
                    <Label htmlFor="enrich-budget">Request budget</Label>
                    <Input
                      id="enrich-budget"
                      type="number"
                      min={1}
                      max={1000}
                      value={budget}
                      onChange={(e) => setBudget(Number(e.target.value))}
                    />
                  </div>
                  <label className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={confirmScope}
                      onCheckedChange={(checked) => setConfirmScope(checked === true)}
                    />
                    Use only the approved project domains and public pages
                  </label>
                  <Button
                    size="sm"
                    disabled={!confirmScope || selected.size === 0 || enrich.isPending}
                    onClick={() =>
                      enrich.mutate(
                        {
                          contact_ids: [...selected],
                          request_budget: budget,
                          confirm_scope: confirmScope,
                        },
                        {
                          onSuccess: (job) =>
                            navigate(`/projects/${projectId}/jobs/${job.id}`),
                        },
                      )
                    }
                  >
                    Start enrichment ({selected.size})
                  </Button>
                  {enrich.isError ? (
                    <p className="text-sm text-destructive">{enrich.error.message}</p>
                  ) : null}
                </div>
              </CapabilityGate>
            ) : null}
          </div>
        </>
      )}
    </div>
  )
}

export function ContactDetailPage() {
  const { projectId, contactId } = useParams<{ projectId: string; contactId: string }>()
  const { data: contact, isPending } = useProjectContact(projectId ?? "", contactId ?? "")
  const review = useReviewEnrichment(projectId ?? "", contactId ?? "")

  if (isPending) return <Skeleton className="h-96 w-full" />
  if (!contact) return <p className="text-muted-foreground">Contact not found.</p>

  return (
    <div className="space-y-6">
      <Link
        to={`/projects/${projectId}/contacts`}
        className="text-sm text-muted-foreground hover:text-foreground"
      >
        ← Contacts
      </Link>
      <div>
        <p className="text-xs font-extrabold uppercase tracking-[0.13em] text-primary">Contact</p>
        <h1 className="text-3xl font-bold tracking-tight">
          {contact.display_name || contact.primary_email}
        </h1>
        <p className="text-muted-foreground">
          {contact.primary_email}
          {contact.company_name ? ` · ${contact.company_name}` : ""}
        </p>
        <div className="mt-2 flex flex-wrap gap-1">
          {contact.tags.map((tag) => (
            <TagChip key={tag.id} name={tag.name} color={tag.color} />
          ))}
        </div>
      </div>
      {contact.metric ? (
        <dl className="neu-flat grid max-w-xl grid-cols-[auto_1fr] gap-x-8 gap-y-1.5 p-5 text-sm">
          <dt className="font-medium">Messages</dt>
          <dd className="text-muted-foreground tabular-nums">
            {contact.metric.contact_count} ({contact.metric.inbound_count} in /{" "}
            {contact.metric.outbound_count} out)
          </dd>
          <dt className="font-medium">First contact</dt>
          <dd className="text-muted-foreground">
            {formatDateTime(contact.metric.first_contact_at)}
          </dd>
          <dt className="font-medium">Last contact</dt>
          <dd className="text-muted-foreground">
            {formatDateTime(contact.metric.last_contact_at)}
          </dd>
          <dt className="font-medium">Quality score</dt>
          <dd className="text-muted-foreground tabular-nums">
            {contact.metric.quality_score ?? "Not scored"}
          </dd>
          <dt className="font-medium">Sentiment</dt>
          <dd className="text-muted-foreground capitalize">{contact.metric.sentiment}</dd>
          {contact.metric.main_topics.length > 0 ? (
            <>
              <dt className="font-medium">Topics</dt>
              <dd className="text-muted-foreground">
                {contact.metric.main_topics.join(", ")}
              </dd>
            </>
          ) : null}
        </dl>
      ) : null}
      {contact.products.length > 0 ? (
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Products discussed</h2>
          <ul className="list-inside list-disc text-sm text-muted-foreground">
            {contact.products.map((product) => (
              <li key={product.id}>{product.canonical_name}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Enrichment results</h2>
        {contact.enrichment_results.length === 0 ? (
          <p className="text-sm text-muted-foreground">No enrichment results yet.</p>
        ) : (
          contact.enrichment_results.map((result) => (
            <div key={result.id} className="neu-flat space-y-2 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="break-all text-sm font-medium">{result.source_url}</p>
                <Badge variant="secondary" className="capitalize">
                  {result.status}
                </Badge>
              </div>
              <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">
                {JSON.stringify(result.candidate_data, null, 2)}
              </pre>
              <p className="text-xs text-muted-foreground">
                Fetched {formatDateTime(result.created_at)}
              </p>
              {result.status === "pending" ? (
                <CapabilityGate capability="review">
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      disabled={review.isPending}
                      onClick={() =>
                        review.mutate({ resultId: result.id, decision: "accepted" })
                      }
                    >
                      Accept
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={review.isPending}
                      onClick={() =>
                        review.mutate({ resultId: result.id, decision: "rejected" })
                      }
                    >
                      Reject
                    </Button>
                  </div>
                </CapabilityGate>
              ) : null}
            </div>
          ))
        )}
      </section>
    </div>
  )
}
