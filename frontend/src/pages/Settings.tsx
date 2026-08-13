import { useState } from "react"

import { useInstanceSettings, useUpdateInstanceSetting } from "@/api/queries"
import type { SettingRow } from "@/api/types"
import { PageHeader } from "@/components/shared"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"

function EditableRow({ row }: { row: SettingRow }) {
  const update = useUpdateInstanceSetting()
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState("")

  if (!editing) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">{row.value || "—"}</span>
        <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
          Edit
        </Button>
      </div>
    )
  }
  return (
    <div className="flex items-center gap-2">
      <Input
        aria-label={`New value for ${row.label}`}
        type={row.secret ? "password" : "text"}
        className="h-8 w-64"
        value={value}
        placeholder={row.secret ? "New secret value (blank clears)" : "New value (blank clears)"}
        onChange={(e) => setValue(e.target.value)}
      />
      <Button
        size="sm"
        disabled={update.isPending}
        onClick={() =>
          update.mutate(
            { key: row.key, value },
            {
              onSuccess: () => {
                setEditing(false)
                setValue("")
              },
            },
          )
        }
      >
        Save
      </Button>
      <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
        Cancel
      </Button>
      {update.isError ? (
        <p className="text-sm text-destructive">{update.error.message}</p>
      ) : null}
    </div>
  )
}

export function SettingsPage() {
  const { data: groups, isPending } = useInstanceSettings()

  return (
    <div className="space-y-8">
      <PageHeader title="Instance settings" />
      {isPending || !groups ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        groups.map((group) => (
          <section key={group.title} className="space-y-3">
            <h2 className="text-lg font-semibold">{group.title}</h2>
            <div className="neu-flat divide-y divide-border/50 p-2">
              {group.rows.map((row) => (
                <div
                  key={row.key}
                  className="flex flex-wrap items-center justify-between gap-3 px-3 py-2.5"
                >
                  <div>
                    <p className="text-sm font-medium">{row.label}</p>
                    <p className="text-xs text-muted-foreground">{row.key}</p>
                  </div>
                  {row.editable ? (
                    <EditableRow row={row} />
                  ) : (
                    <span className="text-sm text-muted-foreground">{row.value || "—"}</span>
                  )}
                </div>
              ))}
            </div>
          </section>
        ))
      )}
      <p className="text-xs text-muted-foreground">
        Values marked editable are stored encrypted and override environment configuration.
        Policy gates can only be changed through the deployment environment.
      </p>
    </div>
  )
}
