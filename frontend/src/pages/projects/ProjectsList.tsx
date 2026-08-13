import { Plus } from "lucide-react"
import { Link } from "react-router"

import { useProjects } from "@/api/queries"
import { CapabilityGate } from "@/components/CapabilityGate"
import { EmptyState, PageHeader, formatDateTime } from "@/components/shared"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"

export function ProjectsListPage() {
  const { data, isPending } = useProjects()

  return (
    <div className="space-y-6">
      <PageHeader title="Projects">
        <CapabilityGate capability="manage_projects">
          <Button asChild size="sm" className="gap-1.5">
            <Link to="/projects/new">
              <Plus className="size-4" aria-hidden />
              New project
            </Link>
          </Button>
        </CapabilityGate>
      </PageHeader>
      {isPending ? (
        <Skeleton className="h-48 w-full" />
      ) : data && data.length > 0 ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="neu-flat block space-y-3 p-5 transition-transform hover:-translate-y-0.5"
            >
              <div className="flex items-center justify-between gap-2">
                <h2 className="font-semibold">{project.name}</h2>
                <span className="flex gap-1">
                  {project.auto_digest_enabled ? <Badge>Auto-digest</Badge> : null}
                  <Badge variant="secondary" className="capitalize">
                    {project.status}
                  </Badge>
                </span>
              </div>
              <p className="line-clamp-2 text-sm text-muted-foreground">{project.purpose}</p>
              <p className="text-xs text-muted-foreground">
                Updated {formatDateTime(project.updated_at)}
              </p>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState title="No projects yet">
          Create a project to organise sources, analysis runs, and extracted entities.
        </EmptyState>
      )}
    </div>
  )
}
