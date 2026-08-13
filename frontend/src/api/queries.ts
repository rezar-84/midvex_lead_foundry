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

// --- projects layer ---------------------------------------------------------

import type {
  ContactDetailT,
  ContactRow,
  EnrichmentResult,
  Job,
  Mailbox,
  Product,
  Project,
  ProjectDetail,
  ProjectPayload,
  SettingGroup,
  Source,
  SourceCreateResult,
  SourcePayload,
  TagT,
} from "./types"

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/api/projects"),
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ["projects", id],
    queryFn: () => api.get<ProjectDetail>(`/api/projects/${id}`),
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ProjectPayload) => api.post<Project>("/api/projects", payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["projects"] }),
  })
}

export function useUpdateProject(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ProjectPayload) => api.patch<Project>(`/api/projects/${id}`, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["projects"] }),
  })
}

export function useSource(projectId: string, sourceId: string) {
  return useQuery({
    queryKey: ["projects", projectId, "sources", sourceId],
    queryFn: () => api.get<Source>(`/api/projects/${projectId}/sources/${sourceId}`),
  })
}

export function useCreateSource(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Partial<SourcePayload>) =>
      api.post<SourceCreateResult>(`/api/projects/${projectId}/sources`, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["projects", projectId] }),
  })
}

export function useUpdateSource(projectId: string, sourceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Partial<SourcePayload>) =>
      api.patch<Source>(`/api/projects/${projectId}/sources/${sourceId}`, payload),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["projects", projectId] }),
  })
}

export function useSyncSource(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (sourceId: string) =>
      api.post<Job>(`/api/projects/${projectId}/sources/${sourceId}/sync`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["projects", projectId] }),
  })
}

export function useStartAnalysis(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<Job>(`/api/projects/${projectId}/analysis/start`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["projects", projectId] }),
  })
}

export function useJobs(projectId: string, page: number) {
  return useQuery({
    queryKey: ["projects", projectId, "jobs", page],
    queryFn: () => api.get<Page<Job>>(`/api/projects/${projectId}/jobs?page=${page}`),
  })
}

export function useJob(projectId: string, jobId: string) {
  return useQuery({
    queryKey: ["projects", projectId, "jobs", "detail", jobId],
    queryFn: () => api.get<Job>(`/api/projects/${projectId}/jobs/${jobId}`),
    refetchInterval: (query) => (query.state.data?.terminal ? false : 2500),
  })
}

export function useCancelJob(projectId: string, jobId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<Job>(`/api/projects/${projectId}/jobs/${jobId}/cancel`),
    onSuccess: (job) => {
      queryClient.setQueryData(["projects", projectId, "jobs", "detail", jobId], job)
      void queryClient.invalidateQueries({ queryKey: ["projects", projectId, "jobs"] })
    },
  })
}

export function useProjectContacts(projectId: string, page: number) {
  return useQuery({
    queryKey: ["projects", projectId, "contacts", page],
    queryFn: () => api.get<Page<ContactRow>>(`/api/projects/${projectId}/contacts?page=${page}`),
  })
}

export function useProjectContact(projectId: string, contactId: string) {
  return useQuery({
    queryKey: ["projects", projectId, "contacts", "detail", contactId],
    queryFn: () =>
      api.get<ContactDetailT>(`/api/projects/${projectId}/contacts/${contactId}`),
  })
}

export function useAssignTag(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: { contact_ids: string[]; tag_id: string }) =>
      api.post<{ assigned: number }>(`/api/projects/${projectId}/contacts/tags/assign`, payload),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["projects", projectId, "contacts"] }),
  })
}

export function useStartEnrichment(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: { contact_ids: string[]; request_budget: number; confirm_scope: boolean }) =>
      api.post<Job>(`/api/projects/${projectId}/enrichment/start`, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["projects", projectId] }),
  })
}

export function useReviewEnrichment(projectId: string, contactId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ resultId, decision }: { resultId: string; decision: "accepted" | "rejected" }) =>
      api.post<EnrichmentResult>(
        `/api/projects/${projectId}/enrichment/${resultId}/review`,
        { decision },
      ),
    onSuccess: () =>
      void queryClient.invalidateQueries({
        queryKey: ["projects", projectId, "contacts", "detail", contactId],
      }),
  })
}

export function useTags(projectId: string) {
  return useQuery({
    queryKey: ["projects", projectId, "tags"],
    queryFn: () => api.get<TagT[]>(`/api/projects/${projectId}/tags`),
  })
}

export function useCreateTag(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: { name: string; category: string; color: string }) =>
      api.post<TagT>(`/api/projects/${projectId}/tags`, payload),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["projects", projectId, "tags"] }),
  })
}

export function useProducts(projectId: string, page: number) {
  return useQuery({
    queryKey: ["projects", projectId, "products", page],
    queryFn: () => api.get<Page<Product>>(`/api/projects/${projectId}/products?page=${page}`),
  })
}

export function useCreateProduct(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      canonical_name: string
      aliases_text: string
      product_group: string
      description: string
      status: string
    }) => api.post<Product>(`/api/projects/${projectId}/products`, payload),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["projects", projectId, "products"] }),
  })
}

export function useMailboxes() {
  return useQuery({
    queryKey: ["mailboxes"],
    queryFn: () => api.get<Mailbox[]>("/api/sources"),
  })
}

export function useInstanceSettings() {
  return useQuery({
    queryKey: ["instance-settings"],
    queryFn: () => api.get<SettingGroup[]>("/api/instance-settings"),
  })
}

export function useUpdateInstanceSetting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      api.put<{ key: string; state: string }>(`/api/instance-settings/${key}`, { value }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["instance-settings"] }),
  })
}

// --- data quality (MVX-035) -------------------------------------------------

import type { MergeSuggestion } from "./types"

export function useStartDedup(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<Job>(`/api/projects/${projectId}/dedup/start`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["projects", projectId] }),
  })
}

export function useMergeSuggestions(status: string, page: number) {
  return useQuery({
    queryKey: ["merge-suggestions", status, page],
    queryFn: () =>
      api.get<Page<MergeSuggestion>>(`/api/merge-suggestions?status=${status}&page=${page}`),
  })
}

export function useDecideMergeSuggestion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "accepted" | "rejected" }) =>
      api.post<MergeSuggestion>(`/api/merge-suggestions/${id}/decide`, { decision }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["merge-suggestions"] })
      void queryClient.invalidateQueries({ queryKey: ["projects"] })
    },
  })
}
