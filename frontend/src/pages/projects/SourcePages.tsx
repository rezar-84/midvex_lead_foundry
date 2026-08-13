import { useState } from "react"
import { Link, useNavigate, useParams, useSearchParams } from "react-router"

import {
  useCreateSource,
  useMe,
  useSource,
  useSyncSource,
  useUpdateSource,
} from "@/api/queries"
import { RequestError } from "@/api/client"
import type { SourcePayload } from "@/api/types"
import { CapabilityGate } from "@/components/CapabilityGate"
import { formatDateTime } from "@/components/shared"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { cookie } from "@/lib/utils"

function FieldErrors({ errors, name }: { errors: Record<string, unknown> | null; name: string }) {
  const value = errors?.[name]
  if (!value) return null
  const messages = Array.isArray(value) ? value : [String(value)]
  return <p className="text-sm text-destructive">{messages.join(" ")}</p>
}

const PROTOCOL_TYPES = new Set(["imap", "pop3"])

export function SourceFormPage({ edit }: { edit?: boolean }) {
  const { projectId, sourceId } = useParams<{ projectId: string; sourceId: string }>()
  const navigate = useNavigate()
  const existing = useSource(projectId ?? "", sourceId ?? "")
  const create = useCreateSource(projectId ?? "")
  const update = useUpdateSource(projectId ?? "", sourceId ?? "")
  const mutation = edit ? update : create
  const source = edit ? existing.data : undefined

  const [form, setForm] = useState<Partial<SourcePayload> | null>(null)
  if (edit && existing.isPending) return <Skeleton className="h-96 w-full" />
  const value: Partial<SourcePayload> = form ?? {
    source_type: source?.source_type ?? "synthetic",
    name: source?.name ?? "",
    email_address: source?.email_address ?? "",
    host: source?.host ?? "",
    port: source?.port ?? null,
    username: source?.username ?? "",
    password: "",
    use_tls: source?.use_tls ?? true,
    rate_limit_per_minute: source?.rate_limit_per_minute ?? 60,
    max_messages_per_run: source?.max_messages_per_run ?? 500,
    confirm_authority: false,
  }
  const set = (patch: Partial<SourcePayload>) => setForm({ ...value, ...patch })
  const errors =
    mutation.error instanceof RequestError ? mutation.error.error.fields : null
  const needsProtocol = PROTOCOL_TYPES.has(value.source_type ?? "")

  const submit = () => {
    if (edit) {
      update.mutate(value, {
        onSuccess: () => navigate(`/projects/${projectId}/sources/${sourceId}`),
      })
    } else {
      create.mutate(value, {
        onSuccess: (result) =>
          navigate(
            result.job_id
              ? `/projects/${projectId}/jobs/${result.job_id}`
              : `/projects/${projectId}/sources/${result.source.id}`,
          ),
      })
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">
        {edit ? "Edit source" : "Add source"}
      </h1>
      <Card className="max-w-2xl">
        <CardContent className="space-y-5 pt-6">
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="source-type">Source type</Label>
              <select
                id="source-type"
                disabled={edit}
                className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
                value={value.source_type}
                onChange={(e) => set({ source_type: e.target.value })}
              >
                <option value="synthetic">Synthetic fixture</option>
                <option value="gmail">Gmail</option>
                <option value="imap">IMAP</option>
                <option value="pop3">POP3</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="source-name">Name</Label>
              <Input
                id="source-name"
                value={value.name}
                onChange={(e) => set({ name: e.target.value })}
              />
              <FieldErrors errors={errors} name="name" />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="source-email">Mailbox address</Label>
            <Input
              id="source-email"
              type="email"
              value={value.email_address}
              onChange={(e) => set({ email_address: e.target.value })}
            />
            <FieldErrors errors={errors} name="email_address" />
          </div>
          {needsProtocol ? (
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="source-host">Host</Label>
                <Input
                  id="source-host"
                  value={value.host}
                  onChange={(e) => set({ host: e.target.value })}
                />
                <FieldErrors errors={errors} name="host" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="source-port">Port</Label>
                <Input
                  id="source-port"
                  type="number"
                  value={value.port ?? ""}
                  onChange={(e) =>
                    set({ port: e.target.value ? Number(e.target.value) : null })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="source-username">Username</Label>
                <Input
                  id="source-username"
                  value={value.username}
                  onChange={(e) => set({ username: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="source-password">Password</Label>
                <Input
                  id="source-password"
                  type="password"
                  value={value.password}
                  onChange={(e) => set({ password: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  Encrypted at rest and never shown again.
                </p>
                <FieldErrors errors={errors} name="password" />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={value.use_tls}
                  onCheckedChange={(checked) => set({ use_tls: checked === true })}
                />
                Use TLS (mandatory for IMAP/POP3)
              </label>
              <FieldErrors errors={errors} name="use_tls" />
            </div>
          ) : null}
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="source-rate">Rate limit / minute</Label>
              <Input
                id="source-rate"
                type="number"
                value={value.rate_limit_per_minute}
                onChange={(e) => set({ rate_limit_per_minute: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="source-max">Max messages per run</Label>
              <Input
                id="source-max"
                type="number"
                value={value.max_messages_per_run}
                onChange={(e) => set({ max_messages_per_run: Number(e.target.value) })}
              />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={value.confirm_authority}
              onCheckedChange={(checked) => set({ confirm_authority: checked === true })}
            />
            I am authorised to configure and process this source
          </label>
          <FieldErrors errors={errors} name="confirm_authority" />
          <div className="flex items-center gap-3">
            <Button onClick={submit} disabled={mutation.isPending}>
              {edit ? "Save source" : "Create source"}
            </Button>
            {mutation.isError && !errors ? (
              <p className="text-sm text-destructive">{mutation.error.message}</p>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export function SourceDetailPage() {
  const { projectId, sourceId } = useParams<{ projectId: string; sourceId: string }>()
  const { data: source, isPending } = useSource(projectId ?? "", sourceId ?? "")
  const sync = useSyncSource(projectId ?? "")
  const navigate = useNavigate()
  const { data: me } = useMe()
  const [params] = useSearchParams()

  if (isPending) return <Skeleton className="h-96 w-full" />
  if (!source) return <p className="text-muted-foreground">Source not found.</p>

  const gmailConnectAllowed =
    source.source_type === "gmail" && (me?.flags.source_network_enabled ?? false)

  return (
    <div className="space-y-6">
      <Link
        to={`/projects/${projectId}`}
        className="text-sm text-muted-foreground hover:text-foreground"
      >
        ← Project operations
      </Link>
      {params.get("connected") ? (
        <p className="rounded-md bg-accent px-3 py-2 text-sm text-accent-foreground">
          Gmail source connected with read-only access.
        </p>
      ) : null}
      {params.get("error") === "network_disabled" ? (
        <p className="text-sm text-destructive">
          External source execution is disabled for this project.
        </p>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.13em] text-primary">
            {source.source_type} source ·{" "}
            <Badge variant="secondary" className="capitalize">
              {source.status}
            </Badge>
          </p>
          <h1 className="text-3xl font-bold tracking-tight">{source.name}</h1>
        </div>
        <div className="flex gap-2">
          <CapabilityGate capability="manage_sources">
            <Button asChild variant="outline" size="sm">
              <Link to={`/projects/${projectId}/sources/${sourceId}/edit`}>Edit</Link>
            </Button>
            <Button
              size="sm"
              disabled={sync.isPending}
              onClick={() =>
                sync.mutate(source.id, {
                  onSuccess: (job) => navigate(`/projects/${projectId}/jobs/${job.id}`),
                })
              }
            >
              Sync now
            </Button>
          </CapabilityGate>
        </div>
      </div>
      {sync.isError ? <p className="text-sm text-destructive">{sync.error.message}</p> : null}
      <dl className="neu-flat grid max-w-xl grid-cols-[auto_1fr] gap-x-8 gap-y-2 p-5 text-sm">
        <dt className="font-medium">Mailbox</dt>
        <dd className="text-muted-foreground">{source.email_address || "—"}</dd>
        <dt className="font-medium">Connected</dt>
        <dd className="text-muted-foreground">{source.mailbox_connected ? "Yes" : "No"}</dd>
        <dt className="font-medium">Last synced</dt>
        <dd className="text-muted-foreground">{formatDateTime(source.last_synced_at)}</dd>
        <dt className="font-medium">Last error</dt>
        <dd className="text-muted-foreground">{source.last_error_code || "None"}</dd>
        <dt className="font-medium">Limits</dt>
        <dd className="text-muted-foreground">
          {source.rate_limit_per_minute}/min · {source.max_messages_per_run} per run
        </dd>
      </dl>
      {source.source_type === "gmail" ? (
        <CapabilityGate capability="manage_sources">
          <form
            method="post"
            action={`/integrations/gmail/projects/${projectId}/sources/${sourceId}/connect/`}
          >
            <input type="hidden" name="csrfmiddlewaretoken" value={cookie("csrftoken")} />
            <Button type="submit" variant="outline" disabled={!gmailConnectAllowed}>
              Connect Gmail (read-only OAuth)
            </Button>
            {!gmailConnectAllowed ? (
              <p className="mt-1 text-xs text-muted-foreground">
                Requires the external source policy gate to be enabled.
              </p>
            ) : null}
          </form>
        </CapabilityGate>
      ) : null}
    </div>
  )
}
