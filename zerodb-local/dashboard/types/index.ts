export interface Project {
  id: string
  name: string
  description?: string
  user_id: string
  organization_id?: string
  settings?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface ProjectStats {
  project_id: string
  vector_count: number
  memory_count: number
  table_count: number
  file_count: number
  event_count: number
  storage_bytes: number
}

export interface Vector {
  id: string
  project_id: string
  collection: string
  vector: number[]
  metadata?: Record<string, any>
  created_at: string
}

export interface Memory {
  id: string
  project_id: string
  session_id: string
  role: string
  content: string
  metadata?: Record<string, any>
  created_at: string
}

export interface Table {
  id: string
  project_id: string
  name: string
  schema?: Record<string, any>
  row_count: number
  created_at: string
  updated_at: string
}

export interface File {
  id: string
  project_id: string
  name: string
  path: string
  mime_type: string
  file_size: number
  url?: string
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface Event {
  id: string
  project_id: string
  type: string
  data: Record<string, any>
  timestamp: string
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  services: {
    postgres: ServiceHealth
    qdrant: ServiceHealth
    minio: ServiceHealth
    redpanda: ServiceHealth
    embeddings: ServiceHealth
  }
  summary: {
    healthy: number
    total: number
  }
}

export interface ServiceHealth {
  status: 'healthy' | 'unhealthy'
  latency_ms?: number
  error?: string
}

export interface ApiError {
  detail: string
  status?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// Cloud Sync Types
export interface CloudAuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user_id: string
  email: string
}

export interface BundleUploadResponse {
  upload_id: string
  bundle_id: string
  status: BundleStatus
  size_bytes: number
  uploaded_at: string
}

export interface BundleDownloadResponse {
  bundle_id: string
  bundle_data: any
  metadata?: Record<string, any>
  size_bytes: number
  created_at: string
}

export interface CloudSyncStatus {
  is_authenticated: boolean
  last_sync_at?: string
  pending_changes: number
  total_bundles: number
  storage_used_bytes: number
  sync_enabled: boolean
}

export interface BundleInfo {
  bundle_id: string
  bundle_name: string
  status: BundleStatus
  size_bytes: number
  entity_counts: {
    vectors?: number
    tables?: number
    memory?: number
    files?: number
    events?: number
  }
  created_at: string
  updated_at: string
}

export enum BundleStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

// Logs Types
export interface LogEntry {
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  service: 'postgres' | 'qdrant' | 'minio' | 'redpanda' | 'embeddings' | 'api' | 'dashboard'
  message: string
  source?: string
}

export interface LogsResponse {
  logs: LogEntry[]
  total_count: number
  service?: string
  level?: string
  time_range_start: string
  time_range_end: string
}
