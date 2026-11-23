// Shapes below mirror the real API response models in api/routers/*.py
// and api/schemas/project.py -- keep them in sync with those, not with
// the cloud product's docs.

export interface ProjectUsage {
  vectors: number
  tables: number
  events: number
  memory: number
  files: number
}

export interface Project {
  id: string
  name: string
  description?: string | null
  user_id: string
  organization_id?: string | null
  tier?: string
  status?: string
  vector_dimensions?: number
  usage?: ProjectUsage
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
  vector_id: string
  document: string
  metadata: Record<string, any>
  namespace: string
  dimensions?: number
  created_at?: string | null
  updated_at?: string | null
}

export interface VectorSearchResult {
  id: string
  vector_id: string
  document: string
  metadata: Record<string, any>
  score: number
  namespace: string
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
  name: string
  schema: Record<string, any>
  description?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface TableRow {
  id: string
  data: Record<string, any>
  created_at?: string | null
  updated_at?: string | null
}

export interface StoredFile {
  id: string
  file_name: string
  file_path: string
  content_type: string
  file_size: number
  folder?: string | null
  metadata: Record<string, any>
  created_at?: string | null
  updated_at?: string | null
}

export interface FileDownload extends StoredFile {
  /** Base64-encoded file content */
  content: string
}

export interface ZeroEvent {
  id: string
  event_type: string
  source: string | null
  correlation_id: string | null
  event_data: Record<string, any>
  timestamp: string | null
}

export interface EventStats {
  time_range: string
  total_events: number
  event_type_count: number
  source_count: number
  top_event_types: Array<Record<string, any>>
  event_type?: string | null
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  backend?: 'lite' | 'full'
  // Lite mode reports {sqlite, faiss, filesystem}; full mode reports
  // {postgres, qdrant, minio, redpanda, embeddings}. Keyed as a record
  // since the actual key set depends on `backend`.
  services: Record<string, ServiceHealth>
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
  service: string
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
