import axios, { AxiosInstance, AxiosError } from 'axios'
import type {
  Project,
  ProjectStats,
  Vector,
  Memory,
  Table,
  File,
  Event,
  HealthStatus,
  ApiError,
  CloudAuthResponse,
  BundleUploadResponse,
  BundleDownloadResponse,
  CloudSyncStatus,
  BundleInfo,
  LogsResponse,
  LogEntry,
} from '@/types'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    const baseURL = typeof window === 'undefined'
      ? process.env.VITE_API_INTERNAL_URL || 'http://zerodb-api:8000'
      : process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        if (error.response) {
          throw new Error(error.response.data.detail || 'API request failed')
        } else if (error.request) {
          throw new Error('No response from server')
        } else {
          throw new Error(error.message || 'Request setup failed')
        }
      }
    )
  }

  // Health
  async getHealth(): Promise<HealthStatus> {
    const response = await this.client.get<HealthStatus>('/health')
    return response.data
  }

  // Projects
  async listProjects(skip = 0, limit = 100): Promise<Project[]> {
    const response = await this.client.get<Project[]>('/v1/projects', {
      params: { skip, limit },
    })
    return response.data
  }

  async getProject(projectId: string): Promise<Project> {
    const response = await this.client.get<Project>(`/v1/projects/${projectId}`)
    return response.data
  }

  async createProject(data: { name: string; description?: string }): Promise<Project> {
    const response = await this.client.post<Project>('/v1/projects', data)
    return response.data
  }

  async updateProject(
    projectId: string,
    data: { name?: string; description?: string }
  ): Promise<Project> {
    const response = await this.client.patch<Project>(`/v1/projects/${projectId}`, data)
    return response.data
  }

  async deleteProject(projectId: string): Promise<void> {
    await this.client.delete(`/v1/projects/${projectId}`)
  }

  async getProjectStats(projectId: string): Promise<ProjectStats> {
    const response = await this.client.get<ProjectStats>(`/v1/projects/${projectId}/stats`)
    return response.data
  }

  // Vectors
  async listVectors(projectId: string, collection?: string): Promise<Vector[]> {
    const response = await this.client.get<Vector[]>(
      `/v1/projects/${projectId}/database/vectors`,
      { params: { collection } }
    )
    return response.data
  }

  async searchVectors(
    projectId: string,
    query: string,
    collection?: string,
    limit = 10
  ): Promise<Vector[]> {
    const response = await this.client.post<Vector[]>(
      `/v1/projects/${projectId}/database/vectors/search`,
      { query, collection, limit }
    )
    return response.data
  }

  // Memory
  async listMemory(projectId: string, sessionId?: string): Promise<Memory[]> {
    const response = await this.client.get<Memory[]>(
      `/v1/projects/${projectId}/database/memory`,
      { params: { session_id: sessionId } }
    )
    return response.data
  }

  // Tables
  async listTables(projectId: string): Promise<Table[]> {
    const response = await this.client.get<Table[]>(
      `/v1/projects/${projectId}/database/tables`
    )
    return response.data
  }

  async getTable(projectId: string, tableName: string): Promise<Table> {
    const response = await this.client.get<Table>(
      `/v1/projects/${projectId}/database/tables/${tableName}`
    )
    return response.data
  }

  async queryTable(
    projectId: string,
    tableName: string,
    filters?: Record<string, any>
  ): Promise<any[]> {
    const response = await this.client.post<any[]>(
      `/v1/projects/${projectId}/database/tables/${tableName}/query`,
      { filters }
    )
    return response.data
  }

  // Files
  async listFiles(projectId: string): Promise<File[]> {
    const response = await this.client.get<File[]>(
      `/v1/projects/${projectId}/database/files`
    )
    return response.data
  }

  async getFile(projectId: string, fileId: string): Promise<File> {
    const response = await this.client.get<File>(
      `/v1/projects/${projectId}/database/files/${fileId}`
    )
    return response.data
  }

  // Events
  async listEvents(projectId: string, type?: string, limit = 100): Promise<Event[]> {
    const response = await this.client.get<Event[]>(
      `/v1/projects/${projectId}/database/events`,
      { params: { type, limit } }
    )
    return response.data
  }

  // Cloud Sync
  async authenticateCloud(projectId: string, apiKey: string): Promise<CloudAuthResponse> {
    const response = await this.client.post<CloudAuthResponse>(
      `/v1/projects/${projectId}/cloud/auth`,
      { api_key: apiKey }
    )
    return response.data
  }

  async uploadToCloud(
    projectId: string,
    bundleData: any,
    bundleName?: string,
    metadata?: Record<string, any>
  ): Promise<BundleUploadResponse> {
    const response = await this.client.post<BundleUploadResponse>(
      `/v1/projects/${projectId}/cloud/upload`,
      {
        bundle_data: bundleData,
        bundle_name: bundleName,
        metadata,
        compression: true
      }
    )
    return response.data
  }

  async downloadFromCloud(
    projectId: string,
    bundleId: string,
    includeMetadata = true
  ): Promise<BundleDownloadResponse> {
    const response = await this.client.get<BundleDownloadResponse>(
      `/v1/projects/${projectId}/cloud/download/${bundleId}`,
      { params: { include_metadata: includeMetadata } }
    )
    return response.data
  }

  async getCloudSyncStatus(projectId: string): Promise<CloudSyncStatus> {
    const response = await this.client.get<CloudSyncStatus>(
      `/v1/projects/${projectId}/cloud/status`
    )
    return response.data
  }

  async listCloudBundles(
    projectId: string,
    statusFilter?: string,
    limit = 50,
    offset = 0
  ): Promise<BundleInfo[]> {
    const response = await this.client.get<BundleInfo[]>(
      `/v1/projects/${projectId}/cloud/bundles`,
      { params: { status_filter: statusFilter, limit, offset } }
    )
    return response.data
  }

  // Logs
  async getLogs(
    service?: string,
    level?: string,
    limit = 100,
    sinceMinutes = 60
  ): Promise<LogsResponse> {
    const response = await this.client.get<LogsResponse>('/v1/logs', {
      params: {
        service,
        level,
        limit,
        since_minutes: sinceMinutes
      }
    })
    return response.data
  }

  async getAvailableServices(): Promise<string[]> {
    const response = await this.client.get<string[]>('/v1/logs/services')
    return response.data
  }

  async getLogLevels(): Promise<string[]> {
    const response = await this.client.get<string[]>('/v1/logs/levels')
    return response.data
  }
}

export const apiClient = new ApiClient()
