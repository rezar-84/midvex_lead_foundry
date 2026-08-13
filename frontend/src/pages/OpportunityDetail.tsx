import { ArrowLeft } from "lucide-react"
import { useState } from "react"
import { Link, useParams } from "react-router"

import { useOpportunity, useReviewOpportunity } from "@/api/queries"
import { CapabilityGate } from "@/components/CapabilityGate"
import { StatusBadge, formatDateTime } from "@/components/shared"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"

type Decision = "accepted" | "rejected" | "deferred"

function ReviewForm({ candidateId }: { candidateId: string }) {
  const review = useReviewOpportunity(candidateId)
  const [note, setNote] = useState("")

  const submit = (decision: Decision) => {
    review.mutate({ decision, note })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Record a decision</CardTitle>
        <CardDescription>
          Decisions are audit logged. The source evidence is not changed.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="review-note">Note (optional)</Label>
          <Textarea
            id="review-note"
            value={note}
            maxLength={2000}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Why this decision?"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button disabled={review.isPending} onClick={() => submit("accepted")}>
            Accept
          </Button>
          <Button
            variant="destructive"
            disabled={review.isPending}
            onClick={() => submit("rejected")}
          >
            Reject
          </Button>
          <Button variant="outline" disabled={review.isPending} onClick={() => submit("deferred")}>
            Defer
          </Button>
        </div>
        {review.isSuccess ? (
          <p className="text-sm text-primary">Review decision saved.</p>
        ) : null}
        {review.isError ? (
          <p className="text-sm text-destructive">{review.error.message}</p>
        ) : null}
      </CardContent>
    </Card>
  )
}

export function OpportunityDetailPage() {
  const { candidateId } = useParams<{ candidateId: string }>()
  const { data, isPending } = useOpportunity(candidateId ?? "")

  if (isPending) {
    return <Skeleton className="h-96 w-full" />
  }
  if (!data) {
    return <p className="text-muted-foreground">Candidate not found.</p>
  }

  return (
    <div className="space-y-6">
      <Link
        to="/opportunities"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden />
        Review queue
      </Link>
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <article className="space-y-6">
          <div className="space-y-2">
            <StatusBadge status={data.status} />
            <h1 className="text-3xl font-bold tracking-tight">{data.title}</h1>
          </div>
          <section className="space-y-1.5">
            <h2 className="text-lg font-semibold">Why it was flagged</h2>
            <p className="text-muted-foreground">{data.reason}</p>
          </section>
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-sm">
            <dt className="font-medium">Rule</dt>
            <dd className="text-muted-foreground">{data.rule_code}</dd>
            <dt className="font-medium">Confidence</dt>
            <dd className="text-muted-foreground">{data.confidence ?? "Not scored"}</dd>
            <dt className="font-medium">Last communication</dt>
            <dd className="text-muted-foreground">
              {formatDateTime(data.last_communication_at)}
            </dd>
          </dl>
          <section className="space-y-2">
            <h2 className="text-lg font-semibold">Evidence</h2>
            <Card>
              <CardContent className="space-y-2 pt-6">
                <strong>{data.evidence.subject}</strong>
                <p className="text-sm text-muted-foreground">{data.evidence.snippet}</p>
                <p className="break-all text-xs text-muted-foreground">
                  Message {data.evidence.message_id} · SHA-256 {data.evidence.sha256}
                </p>
              </CardContent>
            </Card>
          </section>
        </article>
        <CapabilityGate capability="review">
          <aside>
            <ReviewForm candidateId={data.id} />
          </aside>
        </CapabilityGate>
      </div>
    </div>
  )
}
