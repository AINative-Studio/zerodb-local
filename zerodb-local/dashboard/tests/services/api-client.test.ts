import { describe, it, expect, beforeEach, vi } from 'vitest'
import { apiClient } from '@/services/api-client'
import axios from 'axios'

// Mock axios
vi.mock('axios')

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getHealth', () => {
    it('fetches health status successfully', async () => {
      const mockHealth = {
        status: 'healthy',
        services: {
          postgres: { status: 'healthy', latency_ms: 5 },
          qdrant: { status: 'healthy', latency_ms: 3 },
          minio: { status: 'healthy', latency_ms: 4 },
          redpanda: { status: 'healthy', latency_ms: 6 },
          embeddings: { status: 'healthy', latency_ms: 10 },
        },
        summary: { healthy: 5, total: 5 },
      }

      const mockAxios = axios as any
      mockAxios.create = vi.fn(() => ({
        get: vi.fn().mockResolvedValue({ data: mockHealth }),
        interceptors: {
          response: {
            use: vi.fn(),
          },
        },
      }))

      const result = await apiClient.getHealth()
      expect(result.status).toBe('healthy')
      expect(result.summary.healthy).toBe(5)
    })
  })

  describe('listProjects', () => {
    it('fetches projects list successfully', async () => {
      const mockProjects = [
        {
          id: '123',
          name: 'Test Project',
          description: 'Test description',
          user_id: 'user-1',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ]

      const mockAxios = axios as any
      mockAxios.create = vi.fn(() => ({
        get: vi.fn().mockResolvedValue({ data: mockProjects }),
        interceptors: {
          response: {
            use: vi.fn(),
          },
        },
      }))

      const result = await apiClient.listProjects()
      expect(Array.isArray(result)).toBe(true)
    })

    it('handles pagination parameters', async () => {
      const mockAxios = axios as any
      const getMock = vi.fn().mockResolvedValue({ data: [] })

      mockAxios.create = vi.fn(() => ({
        get: getMock,
        interceptors: {
          response: {
            use: vi.fn(),
          },
        },
      }))

      await apiClient.listProjects(10, 50)
      expect(getMock).toHaveBeenCalledWith('/v1/projects', {
        params: { skip: 10, limit: 50 },
      })
    })
  })

  describe('createProject', () => {
    it('creates project successfully', async () => {
      const mockProject = {
        id: '123',
        name: 'New Project',
        description: 'New description',
        user_id: 'user-1',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      const mockAxios = axios as any
      mockAxios.create = vi.fn(() => ({
        post: vi.fn().mockResolvedValue({ data: mockProject }),
        interceptors: {
          response: {
            use: vi.fn(),
          },
        },
      }))

      const result = await apiClient.createProject({
        name: 'New Project',
        description: 'New description',
      })

      expect(result.name).toBe('New Project')
      expect(result.id).toBe('123')
    })
  })

  describe('Error Handling', () => {
    it('handles API errors correctly', async () => {
      const mockAxios = axios as any
      mockAxios.create = vi.fn(() => ({
        get: vi.fn().mockRejectedValue({
          response: {
            data: { detail: 'Not found' },
            status: 404,
          },
        }),
        interceptors: {
          response: {
            use: vi.fn((success, error) => {
              // Simulate error interceptor
              return error
            }),
          },
        },
      }))

      await expect(apiClient.getHealth()).rejects.toThrow()
    })

    it('handles network errors', async () => {
      const mockAxios = axios as any
      mockAxios.create = vi.fn(() => ({
        get: vi.fn().mockRejectedValue({
          request: {},
          message: 'Network Error',
        }),
        interceptors: {
          response: {
            use: vi.fn(),
          },
        },
      }))

      await expect(apiClient.getHealth()).rejects.toThrow()
    })
  })
})
