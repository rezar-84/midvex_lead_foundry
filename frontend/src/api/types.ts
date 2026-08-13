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

export type ProjectStatus = "draft" | "active" | "paused" | "archived"

export interface Project {
  id: string
  name: string
  slug: string
  purpose: string
  status: ProjectStatus
  languages: string[]
  retention_days: number
  monthly_request_budget: number
  allowed_domains: string[]
  network_execution_enabled: boolean
  auto_digest_enabled: boolean
  updated_at: string
}

export interface Source {
  id: string
  source_type: "gmail" | "imap" | "pop3" | "synthetic"
  name: string
  email_address: string
  host: string
  port: number | null
  username: string
  use_tls: boolean
  rate_limit_per_minute: number
  max_messages_per_run: number
  status: string
  last_synced_at: string | null
  last_error_code: string
  has_password: boolean
  mailbox_connected: boolean
}

export interface Job {
  id: string
  kind: "sync" | "analyze" | "enrich"
  status: string
  status_display: string
  processed: number
  total: number
  percent: number
  error_count: number
  requests_used: number
  request_budget: number
  error_code: string
  terminal: boolean
  target_key: string
  source_id: string | null
  created_at: string
  finished_at: string | null
}

export interface ProjectDetail extends Project {
  entity_counts: Record<"contact" | "company" | "product" | "opportunity", number>
  sources: Source[]
  jobs: Job[]
}

export interface TagT {
  id: string
  name: string
  category: string
  color: string
}

export interface Metric {
  contact_count: number
  inbound_count: number
  outbound_count: number
  first_contact_at: string | null
  last_contact_at: string | null
  quality_score: number | null
  sentiment: string
  latest_outcome: string
  main_topics: string[]
}

export interface ProductRef {
  id: string
  canonical_name: string
  relationship_type: string
}

export interface ContactRow {
  id: string
  display_name: string
  primary_email: string
  phone: string
  company_name: string | null
  metric: Metric | null
  products: ProductRef[]
  tags: TagT[]
}

export interface EnrichmentResult {
  id: string
  source_url: string
  status: string
  candidate_data: Record<string, unknown>
  created_at: string
}

export interface ContactDetailT extends ContactRow {
  enrichment_results: EnrichmentResult[]
}

export interface Product {
  id: string
  canonical_name: string
  aliases: string[]
  product_group: string
  description: string
  status: string
}

export interface Mailbox {
  id: string
  provider: string
  email_address: string
  status: string
  scopes: string[]
  policy_confirmed_at: string | null
  created_at: string
}

export interface SettingRow {
  label: string
  value: string
  key: string
  editable: boolean
  secret: boolean
}

export interface SettingGroup {
  title: string
  rows: SettingRow[]
}

export interface SourceCreateResult {
  source: Source
  job_id: string | null
}

export interface ProjectPayload {
  name: string
  purpose: string
  status: ProjectStatus
  languages: string[]
  retention_days: number
  monthly_request_budget: number
  allowed_domains_text: string
  network_execution_enabled: boolean
  auto_digest_enabled: boolean
}

export interface SourcePayload {
  source_type: string
  name: string
  email_address: string
  host: string
  port: number | null
  username: string
  password: string
  use_tls: boolean
  rate_limit_per_minute: number
  max_messages_per_run: number
  confirm_authority: boolean
}

export interface ContactRef {
  id: string
  display_name: string
  primary_email: string
  company_name: string | null
}

export interface MergeSuggestion {
  id: string
  reason: string
  status: "pending" | "accepted" | "rejected"
  primary: ContactRef
  duplicate: ContactRef
  created_at: string
}
