import axios, { AxiosError } from 'axios'
import type {
  Project,
  ProjectStats,
  Vector,
  VectorSearchResult,
  Memory,
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
  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError<ApiError>) => {
      if (error.response) {
        const detail = error.response.data?.detail
        throw new Error(typeof detail === 'string' ? detail : 'API request failed')
      } else if (error.request) {
        throw new Error('No response from the ZeroDB Local API. Is it running?')
      } else {
        throw new Error(error.message || 'Request setup failed')
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
      return (await http.post<Vector>(`${db(projectId)}/vectors/upsert`, body)).data
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
      return (await http.post<VectorSearchResult[]>(`${db(projectId)}/vectors/search`, body)).data
    },
    async deleteVector(projectId: string, vectorId: string): Promise<void> {
      await http.delete(`${db(projectId)}/vectors/${enc(vectorId)}`)
    },

    // Memory
    async listMemory(projectId: string, sessionId?: string): Promise<Memory[]> {
      return (await http.get<Memory[]>(`${db(projectId)}/memory`, { params: { session_id: sessionId } })).data
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
