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

// Agent memory -- api/routers/memory.py
export type MemoryRole = 'user' | 'assistant' | 'system'

export interface MemoryRecord {
  id: string
  session_id: string | null
  agent_id: string
  role: MemoryRole
  content: string
  metadata: Record<string, any>
  created_at?: string | null
}

export interface MemorySearchResult extends MemoryRecord {
  score: number
}

export interface MemorySession {
  session_id: string
  agent_id: string
  message_count: number
  first_message_at?: string | null
  last_message_at?: string | null
}

export interface MemoryContext {
  session_id: string
  messages: MemoryRecord[]
  message_count: number
  estimated_tokens: number
  truncated: boolean
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

// Sync -- api/schemas/sync_orchestrator.py, conflict_resolution, sync_history
export type SyncDirection = 'push' | 'pull' | 'bidirectional'
export type ConflictStrategy = 'local_wins' | 'cloud_wins' | 'newest_wins' | 'manual'
export type SyncRunStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'rolled_back'

export interface SyncStatusInfo {
  project_id: string
  last_sync_at?: string | null
  last_sync_direction?: SyncDirection | null
  sync_in_progress: boolean
  current_sync_id?: string | null
  pending_changes_count: number
  entity_sync_states: Record<string, Record<string, any>>
}

export interface SyncPlanStep {
  step_number: number
  step_type: string
  entity_type?: string | null
  operation?: string | null
  data_count: number
  estimated_duration_seconds?: number | null
  description: string
}

export interface SyncEntityCount {
  tables: number
  table_rows: number
  vectors: number
  memory: number
  events: number
  files: number
}

export interface SyncPlanResult {
  plan_id: string
  project_id: string
  direction: SyncDirection
  created_at: string
  steps: SyncPlanStep[]
  entity_counts: SyncEntityCount
  estimated_duration_seconds: number
  estimated_data_size_bytes: number
  schema_changes: { has_changes: boolean; is_breaking: boolean; changes: string[]; migration_required: boolean }
  conflicts: { has_conflicts: boolean; conflict_count: number; conflicts: Array<Record<string, any>>; resolution_strategy?: ConflictStrategy | null }
  warnings: Array<{ severity: string; message: string; category: string }>
  requires_approval: boolean
  can_rollback: boolean
}

export interface SyncRunResult {
  sync_id: string
  plan_id: string
  direction: SyncDirection
  status: SyncRunStatus
  started_at: string
  completed_at?: string | null
  duration_seconds?: number | null
  total_steps: number
  successful_steps: number
  failed_steps: number
  records_synced: number
  bytes_transferred: number
  errors: string[]
}

export interface SyncConflict {
  id: string
  project_id: string
  entity_type: string
  entity_id: string
  local_version: any
  cloud_version: any
  resolution_strategy?: string | null
  chosen_version?: string | null
  detected_at?: string | null
  resolved_at?: string | null
  conflict_metadata?: Record<string, any> | null
  notes?: string | null
}

export interface SyncHistoryEntry {
  id: string
  sync_id: string
  direction: SyncDirection
  mode?: string
  status: SyncRunStatus
  started_at: string
  completed_at?: string | null
  duration_seconds?: number | null
  records_synced: Record<string, number>
  bytes_transferred: number
  error_message?: string | null
}

export interface SyncHistoryPage {
  items: SyncHistoryEntry[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}
