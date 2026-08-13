import { useParams } from "react-router"

import { useProject } from "@/api/queries"
import { Skeleton } from "@/components/ui/skeleton"
import { ProjectForm } from "./ProjectForm"
import { ProjectNav } from "./ProjectDetailPage"

export function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { data: project, isPending } = useProject(projectId ?? "")

  if (isPending) return <Skeleton className="h-96 w-full" />
  if (!project) return <p className="text-muted-foreground">Project not found.</p>

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Project settings</h1>
      <ProjectNav projectId={project.id} active="settings" />
      <ProjectForm project={project} />
    </div>
  )
}
