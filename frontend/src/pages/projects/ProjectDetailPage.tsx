import { Play, Plus, RefreshCw } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router"

import { useMe, useProject, useStartAnalysis, useSyncSource } from "@/api/queries"
import type { Job, Source } from "@/api/types"
import { CapabilityGate } from "@/components/CapabilityGate"
import { EmptyState, formatDateTime } from "@/components/shared"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export function ProjectNav({ projectId, active }: { projectId: string; active: string }) {
  const tabs = [
    { key: "operations", label: "Operations", to: `/projects/${projectId}` },
    { key: "contacts", label: "Contacts", to: `/projects/${projectId}/contacts` },
    { key: "products", label: "Products", to: `/projects/${projectId}/products` },
    { key: "tags", label: "Tags", to: `/projects/${projectId}/tags` },
    { key: "jobs", label: "Jobs", to: `/projects/${projectId}/jobs` },
    { key: "settings", label: "Settings", to: `/projects/${projectId}/settings` },
  ]
  return (
    <nav aria-label="Project" className="flex w-fit gap-1 overflow-x-auto rounded-lg bg-muted p-1">
      {tabs.map((tab) => (
        <Link
          key={tab.key}
          to={tab.to}
          className={
            tab.key === active
              ? "rounded-md bg-card px-3 py-1.5 text-sm font-medium shadow-sm"
              : "rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
          }
        >
          {tab.label}
        </Link>
      ))}
    </nav>
  )
}

export function JobsTable({ projectId, jobs }: { projectId: string; jobs: Job[] }) {
  if (jobs.length === 0) {
    return (
      <EmptyState title="No jobs have been started">
        Sync a source or start an analysis run to see jobs here.
      </EmptyState>
    )
  }
  return (
    <div className="neu-flat overflow-x-auto p-2">
      <Table>
        <TableHeader>
          <TableRow className="border-0 hover:bg-transparent">
            <TableHead>Job</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Progress</TableHead>
            <TableHead>Started</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.map((job) => (
            <TableRow key={job.id} className="border-border/50">
              <TableCell>
                <Link
                  className="font-medium capitalize hover:underline"
                  to={`/projects/${projectId}/jobs/${job.id}`}
                >
                  {job.kind}
                </Link>
              </TableCell>
              <TableCell>
                <Badge variant={job.terminal ? "secondary" : "default"} className="capitalize">
                  {job.status_display}
                </Badge>
              </TableCell>
              <TableCell className="tabular-nums">
                {job.processed}/{job.total} ({job.percent}%)
              </TableCell>
              <TableCell>{formatDateTime(job.created_at)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function SourceRow({ projectId, source }: { projectId: string; source: Source }) {
  const sync = useSyncSource(projectId)
  const navigate = useNavigate()
  return (
    <TableRow className="border-border/50">
      <TableCell>
        <Link
          className="font-medium hover:underline"
          to={`/projects/${projectId}/sources/${source.id}`}
        >
          {source.name}
        </Link>
      </TableCell>
      <TableCell className="uppercase text-xs">{source.source_type}</TableCell>
      <TableCell>
        <Badge variant="secondary" className="capitalize">
          {source.status}
        </Badge>
      </TableCell>
      <TableCell>{formatDateTime(source.last_synced_at)}</TableCell>
      <TableCell>
        <CapabilityGate capability="manage_sources">
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            disabled={sync.isPending}
            onClick={() =>
              sync.mutate(source.id, {
                onSuccess: (job) => navigate(`/projects/${projectId}/jobs/${job.id}`),
              })
            }
          >
            <RefreshCw className="size-3.5" aria-hidden />
            Sync
          </Button>
        </CapabilityGate>
      </TableCell>
    </TableRow>
  )
}

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { data, isPending } = useProject(projectId ?? "")
  const analysis = useStartAnalysis(projectId ?? "")
  const navigate = useNavigate()
  const { data: me } = useMe()

  if (isPending) return <Skeleton className="h-96 w-full" />
  if (!data) return <p className="text-muted-foreground">Project not found.</p>

  const counts = data.entity_counts

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.13em] text-primary">
            Project · {data.status}
            {data.auto_digest_enabled ? " · auto-digest on" : ""}
          </p>
          <h1 className="text-3xl font-bold tracking-tight">{data.name}</h1>
        </div>
        <CapabilityGate capability="run_batches">
          <Button
            className="gap-1.5"
            disabled={analysis.isPending}
            onClick={() =>
              analysis.mutate(undefined, {
                onSuccess: (job) => navigate(`/projects/${projectId}/jobs/${job.id}`),
              })
            }
          >
            <Play className="size-4" aria-hidden />
            Start analysis
          </Button>
        </CapabilityGate>
      </div>
      <ProjectNav projectId={data.id} active="operations" />
      {analysis.isError ? (
        <p className="text-sm text-destructive">{analysis.error.message}</p>
      ) : null}
      <div className="grid gap-6 sm:grid-cols-4">
        {(
          [
            ["Contacts", counts.contact],
            ["Companies", counts.company],
            ["Products", counts.product],
            ["Opportunities", counts.opportunity],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="neu-raised p-5 text-center">
            <p className="text-3xl font-bold tabular-nums">{value}</p>
            <p className="text-sm text-muted-foreground">{label}</p>
          </div>
        ))}
      </div>
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Sources</h2>
          <CapabilityGate capability="manage_sources">
            <Button asChild variant="outline" size="sm" className="gap-1.5">
              <Link to={`/projects/${data.id}/sources/new`}>
                <Plus className="size-4" aria-hidden />
                Add source
              </Link>
            </Button>
          </CapabilityGate>
        </div>
        {data.sources.length > 0 ? (
          <div className="neu-flat overflow-x-auto p-2">
            <Table>
              <TableHeader>
                <TableRow className="border-0 hover:bg-transparent">
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last synced</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.sources.map((source) => (
                  <SourceRow key={source.id} projectId={data.id} source={source} />
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <EmptyState title="No sources yet">
            Add a mailbox or synthetic source to begin ingesting conversations.
          </EmptyState>
        )}
        {me && !me.flags.source_network_enabled ? (
          <p className="text-xs text-muted-foreground">
            External source sync is disabled by policy; synthetic sources run locally.
          </p>
        ) : null}
      </section>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Recent jobs</h2>
        <JobsTable projectId={data.id} jobs={data.jobs} />
      </section>
    </div>
  )
}
