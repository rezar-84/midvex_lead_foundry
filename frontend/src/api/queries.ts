import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "./client"
import type {
  Company,
  Conversation,
  Dashboard,
  Me,
  Opportunity,
  OpportunityDetail,
  OpportunityStatus,
  Page,
} from "./types"

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<Me>("/api/me"),
    staleTime: 5 * 60 * 1000,
  })
}

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<Dashboard>("/api/dashboard"),
  })
}

export function useOpportunities(status: OpportunityStatus, page: number) {
  return useQuery({
    queryKey: ["opportunities", status, page],
    queryFn: () =>
      api.get<Page<Opportunity>>(`/api/opportunities?status=${status}&page=${page}`),
  })
}

export function useOpportunity(id: string) {
  return useQuery({
    queryKey: ["opportunities", id],
    queryFn: () => api.get<OpportunityDetail>(`/api/opportunities/${id}`),
  })
}

export function useReviewOpportunity(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: { decision: "accepted" | "rejected" | "deferred"; note: string }) =>
      api.post<OpportunityDetail>(`/api/opportunities/${id}/review`, payload),
    onSuccess: (detail) => {
      queryClient.setQueryData(["opportunities", id], detail)
      void queryClient.invalidateQueries({ queryKey: ["opportunities"] })
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useConversations(page: number) {
  return useQuery({
    queryKey: ["conversations", page],
    queryFn: () => api.get<Page<Conversation>>(`/api/conversations?page=${page}`),
  })
}

export function useKnowledge(page: number) {
  return useQuery({
    queryKey: ["knowledge", page],
    queryFn: () => api.get<Page<Company>>(`/api/knowledge?page=${page}`),
  })
}
