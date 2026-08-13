import { useState } from "react"
import { useNavigate } from "react-router"

import { useCreateProject, useMe, useUpdateProject } from "@/api/queries"
import type { Project, ProjectPayload, ProjectStatus } from "@/api/types"
import { RequestError } from "@/api/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

const STATUSES: ProjectStatus[] = ["draft", "active", "paused", "archived"]
const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "tr", label: "Türkçe" },
]

function FieldErrors({ errors, name }: { errors: Record<string, unknown> | null; name: string }) {
  const value = errors?.[name]
  if (!value) return null
  const messages = Array.isArray(value) ? value : [String(value)]
  return <p className="text-sm text-destructive">{messages.join(" ")}</p>
}

export function ProjectForm({ project }: { project?: Project }) {
  const navigate = useNavigate()
  const create = useCreateProject()
  const update = useUpdateProject(project?.id ?? "")
  const mutation = project ? update : create
  const { data: me } = useMe()
  const networkEditable =
    (me?.flags.source_network_enabled ?? false) ||
    (me?.flags.enrichment_network_enabled ?? false)

  const [form, setForm] = useState<ProjectPayload>({
    name: project?.name ?? "",
    purpose: project?.purpose ?? "",
    status: project?.status ?? "draft",
    languages: project?.languages ?? ["en", "tr"],
    retention_days: project?.retention_days ?? 30,
    monthly_request_budget: project?.monthly_request_budget ?? 1000,
    allowed_domains_text: project?.allowed_domains.join("\n") ?? "",
    network_execution_enabled: project?.network_execution_enabled ?? false,
  })
  const errors =
    mutation.error instanceof RequestError ? mutation.error.error.fields : null

  const submit = () => {
    mutation.mutate(form, {
      onSuccess: (saved) => navigate(`/projects/${saved.id}`),
    })
  }

  return (
    <Card className="max-w-2xl">
      <CardContent className="space-y-5 pt-6">
        <div className="space-y-2">
          <Label htmlFor="project-name">Name</Label>
          <Input
            id="project-name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <FieldErrors errors={errors} name="name" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="project-purpose">Purpose</Label>
          <Textarea
            id="project-purpose"
            rows={4}
            value={form.purpose}
            onChange={(e) => setForm({ ...form, purpose: e.target.value })}
          />
          <FieldErrors errors={errors} name="purpose" />
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="project-status">Status</Label>
            <select
              id="project-status"
              className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value as ProjectStatus })}
            >
              {STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label>Languages</Label>
            <div className="flex gap-4 pt-1.5">
              {LANGUAGES.map((language) => (
                <label key={language.code} className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={form.languages.includes(language.code)}
                    onCheckedChange={(checked) =>
                      setForm({
                        ...form,
                        languages: checked
                          ? [...form.languages, language.code]
                          : form.languages.filter((code) => code !== language.code),
                      })
                    }
                  />
                  {language.label}
                </label>
              ))}
            </div>
            <FieldErrors errors={errors} name="languages" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="project-retention">Retention days</Label>
            <Input
              id="project-retention"
              type="number"
              min={1}
              value={form.retention_days}
              onChange={(e) => setForm({ ...form, retention_days: Number(e.target.value) })}
            />
            <FieldErrors errors={errors} name="retention_days" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="project-budget">Monthly request budget</Label>
            <Input
              id="project-budget"
              type="number"
              min={0}
              value={form.monthly_request_budget}
              onChange={(e) =>
                setForm({ ...form, monthly_request_budget: Number(e.target.value) })
              }
            />
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="project-domains">Approved enrichment domains</Label>
          <Textarea
            id="project-domains"
            rows={4}
            placeholder="example.com"
            value={form.allowed_domains_text}
            onChange={(e) => setForm({ ...form, allowed_domains_text: e.target.value })}
          />
          <p className="text-xs text-muted-foreground">
            One public domain per line. Network enrichment remains disabled by policy.
          </p>
          <FieldErrors errors={errors} name="allowed_domains_text" />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <Checkbox
            disabled={!networkEditable}
            checked={form.network_execution_enabled}
            onCheckedChange={(checked) =>
              setForm({ ...form, network_execution_enabled: checked === true })
            }
          />
          Network execution enabled
          <span className="text-xs text-muted-foreground">
            (requires approved deployment feature flags)
          </span>
        </label>
        <div className="flex items-center gap-3">
          <Button onClick={submit} disabled={mutation.isPending}>
            {project ? "Save settings" : "Create project"}
          </Button>
          {mutation.isError && !errors ? (
            <p className="text-sm text-destructive">{mutation.error.message}</p>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}
