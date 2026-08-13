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
}
