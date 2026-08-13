export interface ApiError {
  code: string
  message: string
  fields: Record<string, string> | null
}

export interface Organization {
  id: string
  name: string
  retention_days: number | null
}

export interface Flags {
  gmail_real_data_enabled: boolean
  source_network_enabled: boolean
  enrichment_network_enabled: boolean
}

export type Capability =
  | "view"
  | "review"
  | "export"
  | "manage_sources"
  | "manage_users"
  | "manage_projects"
  | "run_batches"
  | "run_enrichment"

export interface Me {
  username: string
  role: string
  capabilities: Capability[]
  organization: Organization
  brand_name: string
  flags: Flags
}

export interface Page<T> {
  items: T[]
  count: number
  page: number
  pages: number
  per_page: number
}

export type OpportunityStatus = "pending" | "accepted" | "rejected" | "deferred"

export interface Opportunity {
  id: string
  title: string
  reason: string
  rule_code: string
  status: OpportunityStatus
  score: number | null
  confidence: number | null
  last_communication_at: string | null
  conversation_subject: string
}

export interface Evidence {
  message_id: string
  subject: string
  snippet: string
  sha256: string
}

export interface OpportunityDetail extends Opportunity {
  evidence: Evidence
}

export interface Dashboard {
  pending_count: number
  accepted_count: number
  conversation_count: number
  recent: Opportunity[]
}

export interface Conversation {
  id: string
  subject: string
  last_message_at: string | null
}

export interface Contact {
  id: string
  display_name: string
  primary_email: string
  phone: string
}

export interface Company {
  id: string
  name: string
  domain: string
  website: string
  contacts: Contact[]
}
