import { Link, useParams, useSearchParams } from "react-router"

import { useCancelJob, useJob, useJobs } from "@/api/queries"
import { CapabilityGate } from "@/components/CapabilityGate"
import { Pagination, formatDateTime } from "@/components/shared"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { JobsTable, ProjectNav } from "./ProjectDetailPage"

export function JobListPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [params, setParams] = useSearchParams()
  const page = Number(params.get("page") ?? "1")
  const { data, isPending } = useJobs(projectId ?? "", page)

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Jobs</h1>
      <ProjectNav projectId={projectId ?? ""} active="jobs" />
      {isPending || !data ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <>
          <JobsTable projectId={projectId ?? ""} jobs={data.items} />
          <Pagination
            page={page}
            data={data}
            onPageChange={(next) => setParams({ page: String(next) })}
          />
        </>
      )}
    </div>
  )
}

export function JobDetailPage() {
  const { projectId, jobId } = useParams<{ projectId: string; jobId: string }>()
  const { data: job, isPending } = useJob(projectId ?? "", jobId ?? "")
  const cancel = useCancelJob(projectId ?? "", jobId ?? "")

  if (isPending) return <Skeleton className="h-72 w-full" />
  if (!job) return <p className="text-muted-foreground">Job not found.</p>

  return (
    <div className="space-y-6">
      <Link
        to={`/projects/${projectId}/jobs`}
        className="text-sm text-muted-foreground hover:text-foreground"
      >
        ← All jobs
      </Link>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.13em] text-primary">
            {job.kind} job
          </p>
          <h1 className="flex items-center gap-3 text-3xl font-bold tracking-tight">
            {job.status_display}
            {!job.terminal ? (
              <span className="inline-block size-2.5 animate-pulse rounded-full bg-primary" />
            ) : null}
          </h1>
        </div>
        {!job.terminal ? (
          <CapabilityGate capability="run_batches">
            <Button
              variant="destructive"
              size="sm"
              disabled={cancel.isPending}
              onClick={() => cancel.mutate()}
            >
              Cancel job
            </Button>
          </CapabilityGate>
        ) : null}
      </div>
      {cancel.isError ? (
        <p className="text-sm text-destructive">{cancel.error.message}</p>
      ) : null}
      <div className="neu-raised max-w-2xl space-y-4 p-6">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="tabular-nums">
              {job.processed}/{job.total} ({job.percent}%)
            </span>
          </div>
          <Progress value={job.percent} aria-label="Job progress" />
        </div>
        <dl className="grid grid-cols-[auto_1fr] gap-x-8 gap-y-1.5 text-sm">
          <dt className="font-medium">Errors</dt>
          <dd className="text-muted-foreground tabular-nums">{job.error_count}</dd>
          <dt className="font-medium">Requests</dt>
          <dd className="text-muted-foreground tabular-nums">
            {job.requests_used}
            {job.request_budget ? ` of ${job.request_budget}` : ""}
          </dd>
          {job.error_code ? (
            <>
              <dt className="font-medium">Error code</dt>
              <dd>
                <Badge variant="destructive">{job.error_code}</Badge>
              </dd>
            </>
          ) : null}
          <dt className="font-medium">Started</dt>
          <dd className="text-muted-foreground">{formatDateTime(job.created_at)}</dd>
          <dt className="font-medium">Finished</dt>
          <dd className="text-muted-foreground">{formatDateTime(job.finished_at)}</dd>
        </dl>
      </div>
    </div>
  )
}
