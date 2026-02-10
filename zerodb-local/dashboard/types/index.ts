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
