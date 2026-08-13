import { useSearchParams } from "react-router"

import { useMailboxes, useMe } from "@/api/queries"
import { EmptyState, PageHeader, formatDateTime } from "@/components/shared"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cookie } from "@/lib/utils"

export function SourcesPage() {
  const { data: mailboxes, isPending } = useMailboxes()
  const { data: me } = useMe()
  const [params] = useSearchParams()
  const gmailEnabled = me?.flags.gmail_real_data_enabled ?? false

  return (
    <div className="space-y-6">
      <PageHeader title="Sources" />
      {params.get("connected") ? (
        <p className="rounded-md bg-accent px-3 py-2 text-sm text-accent-foreground">
          Gmail source connected with read-only access.
        </p>
      ) : null}
      {params.get("error") === "requirements" ? (
        <p className="text-sm text-destructive">
          Authority confirmation and an organisation retention policy are required.
        </p>
      ) : null}
      {isPending ? (
        <Skeleton className="h-48 w-full" />
      ) : mailboxes && mailboxes.length > 0 ? (
        <div className="neu-flat overflow-x-auto p-2">
          <Table>
            <TableHeader>
              <TableRow className="border-0 hover:bg-transparent">
                <TableHead>Mailbox</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Scopes</TableHead>
                <TableHead>Policy confirmed</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mailboxes.map((mailbox) => (
                <TableRow key={mailbox.id} className="border-border/50">
                  <TableCell className="font-medium">{mailbox.email_address}</TableCell>
                  <TableCell className="capitalize">{mailbox.provider}</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="capitalize">
                      {mailbox.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-52 truncate text-xs text-muted-foreground">
                    {mailbox.scopes.join(", ") || "—"}
                  </TableCell>
                  <TableCell>{formatDateTime(mailbox.policy_confirmed_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        <EmptyState title="No mailbox connections">
          Connect a Gmail mailbox below, or add sources inside a project.
        </EmptyState>
      )}
      <section className="neu-raised max-w-xl space-y-4 p-6">
        <h2 className="font-semibold">Connect a Gmail mailbox (read-only)</h2>
        {!gmailEnabled ? (
          <p className="text-sm text-muted-foreground">
            Real Gmail access is disabled by policy. The connect flow stays unavailable until
            the policy gate is approved and enabled.
          </p>
        ) : null}
        <form method="post" action="/integrations/gmail/connect/" className="space-y-3">
          <input type="hidden" name="csrfmiddlewaretoken" value={cookie("csrftoken")} />
          <label className="flex items-center gap-2 text-sm">
            <Checkbox name="confirm_authority" value="on" required disabled={!gmailEnabled} />
            I am authorised to process this mailbox
          </label>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox name="confirm_retention" value="on" required disabled={!gmailEnabled} />
            The organisation retention policy applies
          </label>
          <Button type="submit" disabled={!gmailEnabled}>
            Continue to Google consent
          </Button>
        </form>
      </section>
    </div>
  )
}
