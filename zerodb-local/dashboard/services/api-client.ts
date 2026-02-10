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
}

export const apiClient = new ApiClient()
