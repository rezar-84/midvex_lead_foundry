import type { ReactNode } from "react"

import { useMe } from "@/api/queries"
import type { Capability } from "@/api/types"

export function CapabilityGate({
  capability,
  children,
}: {
  capability: Capability
  children: ReactNode
}) {
  const { data: me } = useMe()
  if (!me || !me.capabilities.includes(capability)) {
    return null
  }
  return <>{children}</>
}
