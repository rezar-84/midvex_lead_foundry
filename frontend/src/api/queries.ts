import { useQuery } from "@tanstack/react-query"

import { api } from "./client"
import type { Me } from "./types"

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<Me>("/api/me"),
    staleTime: 5 * 60 * 1000,
  })
}
