import axios, { AxiosError } from 'axios'
import type {
  Project,
  ProjectStats,
  Vector,
  VectorSearchResult,
  MemoryRecord,
  MemorySearchResult,
  MemorySession,
  MemoryContext,
  MemoryRole,
  SyncStatusInfo,
  SyncPlanResult,
  SyncRunResult,
  SyncConflict,
  SyncHistoryPage,
  SyncDirection,
  ConflictStrategy,
  Table,
  TableRow,
  StoredFile,
  FileDownload,
  ZeroEvent,
  EventStats,
  HealthStatus,
  ApiError,
  CloudAuthResponse,
  BundleUploadResponse,
  BundleDownloadResponse,
  CloudSyncStatus,
  BundleInfo,
  LogsResponse,
} from '@/types'
import type { UpsertVectorRequest } from '@/lib/vector-form'
import type { TableSchema } from '@/lib/schema-builder'
import { getApiKey } from '@/lib/api-key'

/** An API failure that keeps the HTTP status (401 -> show the sign-in hint). */
export class ApiRequestError extends Error {
  status?: number
  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
  }
  get isAuthError(): boolean {
    return this.status === 401 || this.status === 403
  }
}

/** Adds `Authorization: Bearer <key>` unless the request already has one. */
export function withApiKey<T extends { headers?: any }>(config: T, key: string | null): T {
  if (!key) return config
  const headers = { ...(config.headers ?? {}) }
  if (!headers.Authorization && !headers.authorization) headers.Authorization = `Bearer ${key}`
  return { ...config, headers }
}

/** The subset of an axios instance the client uses -- injectable for tests. */
export interface HttpLike {
  defaults: { baseURL?: string }
  get<T = any>(url: string, config?: any): Promise<{ data: T }>
  post<T = any>(url: string, body?: any, config?: any): Promise<{ data: T }>
  patch<T = any>(url: string, body?: any, config?: any): Promise<{ data: T }>
  put<T = any>(url: string, body?: any, config?: any): Promise<{ data: T }>
  delete<T = any>(url: string, config?: any): Promise<{ data: T }>
}

export function defaultBaseURL(): string {
  return typeof window === 'undefined'
    ? process.env.API_INTERNAL_URL || process.env.VITE_API_INTERNAL_URL || 'http://zerodb-api:8000'
    : process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}

function createHttp(): HttpLike {
  const instance = axios.create({
    baseURL: defaultBaseURL(),
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
  })
  instance.interceptors.request.use((config) => withApiKey(config, getApiKey()))
  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError<ApiError>) => {
      if (error.response) {
        const { status, data } = error.response
        const detail = data?.detail
        if (status === 401 || status === 403) {
          throw new ApiRequestError(
            'This server needs an API key. Add one in Settings › Connection.',
            status
          )
        }
        throw new ApiRequestError(typeof detail === 'string' ? detail : `API request failed (${status})`, status)
      } else if (error.request) {
        throw new ApiRequestError('No response from the ZeroDB Local API. Is it running?')
      } else {
        throw new ApiRequestError(error.message || 'Request setup failed')
      }
    }
  )
  return instance as unknown as HttpLike
}

const enc = encodeURIComponent

export function createApiClient(http: HttpLike = createHttp()) {
  const db = (projectId: string) => `/v1/projects/${projectId}/database`

  return {
    /** The API URL actually in use -- shown on Settings instead of a hardcoded string. */
    get baseURL(): string {
      return http.defaults.baseURL ?? ''
    },

    // Health
    async getHealth(): Promise<HealthStatus> {
      return (await http.get<HealthStatus>('/health')).data
    },

    // Projects
    async listProjects(skip = 0, limit = 100): Promise<Project[]> {
      return (await http.get<Project[]>('/v1/projects', { params: { skip, limit } })).data
    },
    async getProject(projectId: string): Promise<Project> {
      return (await http.get<Project>(`/v1/projects/${projectId}`)).data
    },
    async createProject(data: { name: string; description?: string }): Promise<Project> {
      return (await http.post<Project>('/v1/projects', data)).data
    },
    async updateProject(projectId: string, data: { name?: string; description?: string }): Promise<Project> {
      return (await http.patch<Project>(`/v1/projects/${projectId}`, data)).data
    },
    async deleteProject(projectId: string): Promise<void> {
      await http.delete(`/v1/projects/${projectId}`)
    },
    async getProjectStats(projectId: string): Promise<ProjectStats> {
      return (await http.get<ProjectStats>(`/v1/projects/${projectId}/stats`)).data
    },

    // Vectors
    async listVectors(projectId: string, namespace?: string, limit = 100): Promise<Vector[]> {
      return (await http.get<Vector[]>(`${db(projectId)}/vectors`, { params: { namespace, limit } })).data
    },
    async upsertVector(projectId: string, body: UpsertVectorRequest): Promise<Vector> {
      // Lite mode embeds `document` server-side with a local model
      // (BAAI/bge-small-en-v1.5) that lazily downloads from HuggingFace Hub
      // on first use -- a cold, unauthenticated-rate-limited load can take
      // well over the client's default 30s timeout (confirmed live: the
      // server returned 200 after ~15-20s on a cold start, but the request
      // had already timed out client-side with "No response from the
      // ZeroDB Local API"). The vector is NOT lost when this happens --
      // it's a false-negative error, not a failed write -- but it's a
      // confusing first-run experience. Every later call on a warm model is
      // fast; this long timeout only matters for the first one.
      return (await http.post<Vector>(`${db(projectId)}/vectors/upsert`, body, { timeout: 90000 })).data
    },
    async searchVectors(
      projectId: string,
      opts: { query: string; namespace?: string; limit?: number; threshold?: number }
    ): Promise<VectorSearchResult[]> {
      const body = {
        query: opts.query,
        namespace: opts.namespace,
        limit: opts.limit ?? 10,
        // The API defaults to 0.7, which hides most results for short
        // queries; show everything ranked by score and let people judge.
        threshold: opts.threshold ?? 0,
      }
      // Same cold-start embedding cost as upsertVector above.
      return (await http.post<VectorSearchResult[]>(`${db(projectId)}/vectors/search`, body, { timeout: 90000 })).data
    },
    async deleteVector(projectId: string, vectorId: string): Promise<void> {
      await http.delete(`${db(projectId)}/vectors/${enc(vectorId)}`)
    },

    // Memory (api/routers/memory.py)
    async listMemorySessions(projectId: string, opts: { agentId?: string; limit?: number } = {}): Promise<MemorySession[]> {
      const params: Record<string, any> = {}
      if (opts.agentId) params.agent_id = opts.agentId
      params.limit = opts.limit ?? 100
      return (await http.get<MemorySession[]>(`${db(projectId)}/memory/sessions`, { params })).data
    },
    async getMemoryContext(projectId: string, sessionId: string, limit = 200): Promise<MemoryContext> {
      return (await http.get<MemoryContext>(`${db(projectId)}/memory/context/${enc(sessionId)}`, { params: { limit } })).data
    },
    async storeMemory(
      projectId: string,
      body: { content: string; role: MemoryRole; agent_id?: string; session_id?: string; metadata?: Record<string, any> }
    ): Promise<MemoryRecord> {
      return (await http.post<MemoryRecord>(`${db(projectId)}/memory/store`, body)).data
    },
    async searchMemory(
      projectId: string,
      opts: { query: string; limit?: number; threshold?: number; agentId?: string; sessionId?: string; role?: MemoryRole }
    ): Promise<MemorySearchResult[]> {
      const body: Record<string, any> = { query: opts.query, limit: opts.limit ?? 20, threshold: opts.threshold ?? 0 }
      if (opts.agentId) body.agent_id = opts.agentId
      if (opts.sessionId) body.session_id = opts.sessionId
      if (opts.role) body.role = opts.role
      return (await http.post<MemorySearchResult[]>(`${db(projectId)}/memory/search`, body)).data
    },
    async deleteMemorySession(projectId: string, sessionId: string): Promise<void> {
      await http.delete(`${db(projectId)}/memory/sessions/${enc(sessionId)}`)
    },

    // Sync (api/routers/sync_orchestrator.py, conflict_resolution.py, sync_history.py)
    async getSyncStatus(projectId: string): Promise<SyncStatusInfo> {
      return (await http.get<SyncStatusInfo>(`/v1/projects/${projectId}/sync/status`)).data
    },
    async planSync(
      projectId: string,
      body: { direction: SyncDirection; conflict_strategy?: ConflictStrategy; entity_types?: string[]; include_schema?: boolean }
    ): Promise<SyncPlanResult> {
      return (await http.post<SyncPlanResult>(`/v1/projects/${projectId}/sync/plan`, body)).data
    },
    async executeSync(projectId: string, planId: string): Promise<SyncRunResult> {
      // The dashboard only executes after the person has reviewed the plan
      // and pressed the run button, so that click is the approval.
      return (await http.post<SyncRunResult>(`/v1/projects/${projectId}/sync/execute`, { plan_id: planId, approved: true })).data
    },
    async listConflicts(projectId: string, limit = 100): Promise<SyncConflict[]> {
      return (await http.get<SyncConflict[]>(`/v1/projects/${projectId}/sync/conflicts/`, { params: { limit } })).data
    },
    async resolveConflict(projectId: string, conflictId: string, strategy: ConflictStrategy, manualChoice?: 'local' | 'cloud') {
      const body: Record<string, any> = { conflict_id: conflictId, strategy }
      if (manualChoice) body.manual_choice = manualChoice
      return (await http.post(`/v1/projects/${projectId}/sync/conflicts/${enc(conflictId)}/resolve`, body)).data
    },
    async listSyncHistory(projectId: string, limit = 20, offset = 0): Promise<SyncHistoryPage> {
      return (await http.get<SyncHistoryPage>(`/v1/projects/${projectId}/sync/history`, { params: { limit, offset } })).data
    },

    // Tables
    async listTables(projectId: string): Promise<Table[]> {
      return (await http.get<Table[]>(`${db(projectId)}/tables`)).data
    },
    async getTable(projectId: string, tableName: string): Promise<Table> {
      return (await http.get<Table>(`${db(projectId)}/tables/${enc(tableName)}`)).data
    },
    async createTable(
      projectId: string,
      body: { table_name: string; schema: TableSchema | Record<string, any>; description?: string }
    ): Promise<Table> {
      return (await http.post<Table>(`${db(projectId)}/tables`, body)).data
    },
    async deleteTable(projectId: string, tableName: string): Promise<void> {
      await http.delete(`${db(projectId)}/tables/${enc(tableName)}`)
    },
    async queryTable(
      projectId: string,
      tableName: string,
      opts: { filter?: Record<string, any>; limit?: number; offset?: number } = {}
    ): Promise<TableRow[]> {
      const body = { filter: opts.filter, limit: opts.limit ?? 100, offset: opts.offset ?? 0 }
      return (await http.post<TableRow[]>(`${db(projectId)}/tables/${enc(tableName)}/query`, body)).data
    },
    async insertRows(projectId: string, tableName: string, rows: Record<string, any>[]) {
      return (await http.post(`${db(projectId)}/tables/${enc(tableName)}/insert`, { rows })).data
    },

    // Files
    async listFiles(projectId: string, folder?: string): Promise<StoredFile[]> {
      const config = folder ? { params: { folder } } : undefined
      return (await http.get<StoredFile[]>(`${db(projectId)}/files`, config)).data
    },
    async uploadFile(
      projectId: string,
      body: { file_name: string; file_content: string; content_type?: string; folder?: string; metadata?: Record<string, any> }
    ): Promise<StoredFile> {
      return (await http.post<StoredFile>(`${db(projectId)}/files/upload`, body)).data
    },
    async downloadFile(projectId: string, fileId: string): Promise<FileDownload> {
      return (await http.get<FileDownload>(`${db(projectId)}/files/${enc(fileId)}`, { params: { return_base64: true } })).data
    },
    async deleteFile(projectId: string, fileId: string): Promise<void> {
      await http.delete(`${db(projectId)}/files/${enc(fileId)}`)
    },

    // Events
    async listEvents(projectId: string, opts: { eventType?: string; limit?: number } = {}): Promise<ZeroEvent[]> {
      const params: Record<string, any> = {}
      if (opts.eventType) params.event_type = opts.eventType
      params.limit = opts.limit ?? 100
      return (await http.get<ZeroEvent[]>(`${db(projectId)}/events`, { params })).data
    },
    async createEvent(
      projectId: string,
      body: { event_type: string; event_data: Record<string, any>; source?: string; correlation_id?: string }
    ): Promise<ZeroEvent> {
      return (await http.post<ZeroEvent>(`${db(projectId)}/events`, body)).data
    },
    async getEventStats(projectId: string, timeRange = 'day'): Promise<EventStats> {
      return (await http.get<EventStats>(`${db(projectId)}/events/stats/summary`, { params: { time_range: timeRange } })).data
    },

    // Cloud Sync
    async authenticateCloud(projectId: string, apiKey: string): Promise<CloudAuthResponse> {
      return (await http.post<CloudAuthResponse>(`/v1/projects/${projectId}/cloud/auth`, { api_key: apiKey })).data
    },
    async uploadToCloud(projectId: string, bundleData: any, bundleName?: string, metadata?: Record<string, any>): Promise<BundleUploadResponse> {
      return (
        await http.post<BundleUploadResponse>(`/v1/projects/${projectId}/cloud/upload`, {
          bundle_data: bundleData,
          bundle_name: bundleName,
          metadata,
          compression: true,
        })
      ).data
    },
    async downloadFromCloud(projectId: string, bundleId: string, includeMetadata = true): Promise<BundleDownloadResponse> {
      return (
        await http.get<BundleDownloadResponse>(`/v1/projects/${projectId}/cloud/download/${bundleId}`, {
          params: { include_metadata: includeMetadata },
        })
      ).data
    },
    async getCloudSyncStatus(projectId: string): Promise<CloudSyncStatus> {
      return (await http.get<CloudSyncStatus>(`/v1/projects/${projectId}/cloud/status`)).data
    },
    async listCloudBundles(projectId: string, statusFilter?: string, limit = 50, offset = 0): Promise<BundleInfo[]> {
      return (
        await http.get<BundleInfo[]>(`/v1/projects/${projectId}/cloud/bundles`, {
          params: { status_filter: statusFilter, limit, offset },
        })
      ).data
    },

    // Logs
    async getLogs(service?: string, level?: string, limit = 100, sinceMinutes = 60): Promise<LogsResponse> {
      return (
        await http.get<LogsResponse>('/v1/logs', {
          params: { service, level, limit, since_minutes: sinceMinutes },
        })
      ).data
    },
    async getAvailableServices(): Promise<string[]> {
      return (await http.get<string[]>('/v1/logs/services')).data
    },
    async getLogLevels(): Promise<string[]> {
      return (await http.get<string[]>('/v1/logs/levels')).data
    },
  }
}

export type ApiClient = ReturnType<typeof createApiClient>

export const apiClient = createApiClient()
