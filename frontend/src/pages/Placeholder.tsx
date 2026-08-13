import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function Placeholder({ title }: { title: string }) {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
      <Card>
        <CardHeader>
          <CardTitle>Rebuild in progress</CardTitle>
          <CardDescription>
            This page is being migrated to the new interface. Until it lands here, the previous
            version keeps working at its original address.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          The classic page opens automatically when you follow existing links or bookmarks.
        </CardContent>
      </Card>
    </div>
  )
}
