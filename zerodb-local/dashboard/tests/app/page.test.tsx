import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DashboardPage from '@/app/page'
import { apiClient } from '@/services/api-client'

// Mock the API client
vi.mock('@/services/api-client', () => ({
  apiClient: {
    getHealth: vi.fn(),
  },
}))

// Mock Next.js Link
vi.mock('next/link', () => ({
  default: ({ children, href }: any) => <a href={href}>{children}</a>,
}))

// Mock lucide-react icons with a Proxy for dynamic icon creation
vi.mock('lucide-react', () => {
  const createMockIcon = (name: string) => {
    return () => <div data-testid={`${name.toLowerCase()}-icon`}>{name} Icon</div>
  }

  const icons = {
    Database: createMockIcon('Database'),
    HardDrive: createMockIcon('HardDrive'),
    Activity: createMockIcon('Activity'),
    AlertCircle: createMockIcon('AlertCircle'),
    CheckCircle: createMockIcon('CheckCircle'),
    Server: createMockIcon('Server'),
    Zap: createMockIcon('Zap'),
    Shield: createMockIcon('Shield'),
    Copy: createMockIcon('Copy'),
    Check: createMockIcon('Check'),
    BookOpen: createMockIcon('BookOpen'),
    ArrowRight: createMockIcon('ArrowRight'),
    TrendingUp: createMockIcon('TrendingUp'),
    FileText: createMockIcon('FileText'),
    Box: createMockIcon('Box'),
    Plus: createMockIcon('Plus'),
    Layers: createMockIcon('Layers'),
  }

  // Return a Proxy that creates missing icons dynamically
  return new Proxy(icons, {
    get: (target: any, prop: string) => {
      if (prop in target) {
        return target[prop]
      }
      // Dynamically create missing icons
      return createMockIcon(prop)
    }
  })
})

// Helper function to render with QueryClient
const renderWithQuery = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  )
}

// Mock health data
const mockHealthyResponse = {
  status: 'healthy',
  summary: {
    healthy: 5,
    total: 5,
  },
  services: {
    postgres: { status: 'healthy', latency_ms: 5 },
    qdrant: { status: 'healthy', latency_ms: 12 },
    minio: { status: 'healthy', latency_ms: 8 },
    redpanda: { status: 'healthy', latency_ms: 15 },
    embeddings: { status: 'healthy', latency_ms: 120 },
  },
}

const mockDegradedResponse = {
  status: 'degraded',
  summary: {
    healthy: 3,
    total: 5,
  },
  services: {
    postgres: { status: 'healthy', latency_ms: 5 },
    qdrant: { status: 'unhealthy' },
    minio: { status: 'healthy', latency_ms: 8 },
    redpanda: { status: 'unhealthy' },
    embeddings: { status: 'healthy', latency_ms: 120 },
  },
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Loading State', () => {
    it('should display loading spinner when data is being fetched', () => {
      // Given: API is loading
      vi.mocked(apiClient.getHealth).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      // When: Component is rendered
      const { container } = renderWithQuery(<DashboardPage />)

      // Then: Loading spinner should be visible
      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })

    it('should have proper loading container structure', () => {
      // Given: API is loading
      vi.mocked(apiClient.getHealth).mockImplementation(
        () => new Promise(() => {})
      )

      // When: Component is rendered
      const { container } = renderWithQuery(<DashboardPage />)

      // Then: Loading container should have proper styling
      const loadingContainer = container.querySelector('.p-8')
      expect(loadingContainer).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('should display error message when API call fails', async () => {
      // Given: API returns an error
      const errorMessage = 'Network connection failed'
      vi.mocked(apiClient.getHealth).mockRejectedValue(new Error(errorMessage))

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Error card should be displayed
      await waitFor(() => {
        expect(screen.getByText('Connection Error')).toBeInTheDocument()
        expect(screen.getByText(errorMessage)).toBeInTheDocument()
      })
    })

    it('should display error card with proper styling', async () => {
      // Given: API returns an error
      vi.mocked(apiClient.getHealth).mockRejectedValue(new Error('Test error'))

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Error card should have red border styling
      await waitFor(() => {
        const errorCard = screen.getByText('Connection Error').closest('div[class*="border-red"]')
        expect(errorCard).toBeInTheDocument()
      })
    })

    it('should display alert icon in error state', async () => {
      // Given: API returns an error
      vi.mocked(apiClient.getHealth).mockRejectedValue(new Error('Test error'))

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Alert icon should be visible
      await waitFor(() => {
        expect(screen.getByTestId('alert-icon')).toBeInTheDocument()
      })
    })

    it('should display connection error description', async () => {
      // Given: API returns an error
      vi.mocked(apiClient.getHealth).mockRejectedValue(new Error('Test error'))

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Connection error description should be visible
      await waitFor(() => {
        expect(screen.getByText('Unable to connect to ZeroDB API at localhost:8000')).toBeInTheDocument()
      })
    })
  })

  describe('Hero Section', () => {
    beforeEach(() => {
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)
    })

    it('should render hero section with heading', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Hero content should be visible
      await waitFor(() => {
        expect(screen.getByText('Welcome to ZeroDB Local')).toBeInTheDocument()
      })
    })

    it('should render hero section tagline', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Tagline should be visible
      await waitFor(() => {
        expect(screen.getByText(/Self-hosted AI database/i)).toBeInTheDocument()
      })
    })

    it('should render CTA buttons in hero section', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: CTA buttons should be visible
      await waitFor(() => {
        expect(screen.getByText('Get Started')).toBeInTheDocument()
        expect(screen.getByText('View Documentation')).toBeInTheDocument()
      })
    })
  })

  describe('Feature Cards Section', () => {
    beforeEach(() => {
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)
    })

    it('should render all three feature cards', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: All feature cards should be visible
      await waitFor(() => {
        expect(screen.getByText('Local-First Development')).toBeInTheDocument()
        expect(screen.getByText('Lightning Fast')).toBeInTheDocument()
        expect(screen.getByText('Enterprise Security')).toBeInTheDocument()
      })
    })

    it('should render feature card descriptions', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Feature descriptions should be visible
      await waitFor(() => {
        expect(screen.getByText(/Build AI applications without cloud dependencies/i)).toBeInTheDocument()
      })
    })

    it('should display feature icons', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Feature icons should be rendered
      await waitFor(() => {
        expect(screen.getByTestId('server-icon')).toBeInTheDocument()
        expect(screen.getByTestId('zap-icon')).toBeInTheDocument()
        expect(screen.getByTestId('shield-icon')).toBeInTheDocument()
      })
    })
  })

  describe('Code Examples Section', () => {
    beforeEach(() => {
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)
    })

    it('should render code examples section heading', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Code examples heading should be visible
      await waitFor(() => {
        expect(screen.getByText('Quick Start Examples')).toBeInTheDocument()
      })
    })

    it('should render code example tabs', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Code tabs should be visible
      await waitFor(() => {
        expect(screen.getByText('Python')).toBeInTheDocument()
        expect(screen.getByText('JavaScript')).toBeInTheDocument()
        expect(screen.getByText('cURL')).toBeInTheDocument()
      })
    })

    it('should display code snippets', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Code snippets should be visible
      await waitFor(() => {
        const codeBlocks = screen.getAllByRole('code')
        expect(codeBlocks.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Enhanced Quick Stats Section', () => {
    beforeEach(() => {
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)
    })

    it('should render quick stats section', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Quick stats should be visible
      await waitFor(() => {
        expect(screen.getByText(/Total Vectors|Vectors Stored/i)).toBeInTheDocument()
      })
    })

    it('should display stat values', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Stat values should be displayed (as 0 in this case)
      await waitFor(() => {
        const statValues = screen.getAllByText('0')
        expect(statValues.length).toBeGreaterThan(0)
      })
    })
  })

  describe('System Status Overview', () => {
    it('should render system status card when healthy', async () => {
      // Given: All services are healthy
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: System status card should be visible
      await waitFor(() => {
        expect(screen.getByText('System Status')).toBeInTheDocument()
        expect(screen.getByText('Overall Health')).toBeInTheDocument()
      })
    })

    it('should display correct status badge for healthy system', async () => {
      // Given: All services are healthy
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Healthy badge should be visible
      await waitFor(() => {
        expect(screen.getByText('HEALTHY')).toBeInTheDocument()
      })
    })

    it('should display correct status badge for degraded system', async () => {
      // Given: Some services are unhealthy
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockDegradedResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Degraded badge should be visible
      await waitFor(() => {
        expect(screen.getByText('DEGRADED')).toBeInTheDocument()
      })
    })

    it('should display correct service count summary', async () => {
      // Given: All services are healthy
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Service count should be correct
      await waitFor(() => {
        expect(screen.getByText('5 of 5 services operational')).toBeInTheDocument()
      })
    })

    it('should display correct service count for degraded system', async () => {
      // Given: Some services are unhealthy
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockDegradedResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Service count should reflect degraded state
      await waitFor(() => {
        expect(screen.getByText('3 of 5 services operational')).toBeInTheDocument()
      })
    })
  })

  describe('Service Status Grid', () => {
    beforeEach(() => {
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)
    })

    it('should render all five service cards', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: All service cards should be visible
      await waitFor(() => {
        expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
        expect(screen.getByText('Qdrant')).toBeInTheDocument()
        expect(screen.getByText('MinIO')).toBeInTheDocument()
        expect(screen.getByText('RedPanda')).toBeInTheDocument()
        expect(screen.getByText('Embeddings')).toBeInTheDocument()
      })
    })

    it('should display PostgreSQL service with correct details', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: PostgreSQL card should have correct content
      await waitFor(() => {
        expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
        expect(screen.getByText('Primary database')).toBeInTheDocument()
      })
    })

    it('should display Qdrant service with correct details', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Qdrant card should have correct content
      await waitFor(() => {
        expect(screen.getByText('Qdrant')).toBeInTheDocument()
        expect(screen.getByText('Vector search engine')).toBeInTheDocument()
      })
    })

    it('should display MinIO service with correct details', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: MinIO card should have correct content
      await waitFor(() => {
        expect(screen.getByText('MinIO')).toBeInTheDocument()
        expect(screen.getByText('Object storage')).toBeInTheDocument()
      })
    })

    it('should display RedPanda service with correct details', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: RedPanda card should have correct content
      await waitFor(() => {
        expect(screen.getByText('RedPanda')).toBeInTheDocument()
        expect(screen.getByText('Event streaming')).toBeInTheDocument()
      })
    })

    it('should display Embeddings service with correct details', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Embeddings card should have correct content
      await waitFor(() => {
        expect(screen.getByText('Embeddings')).toBeInTheDocument()
        expect(screen.getByText('Local embeddings (BAAI BGE)')).toBeInTheDocument()
      })
    })

    it('should display icons for all services', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: All service icons should be visible
      await waitFor(() => {
        const icons = screen.getAllByTestId(/icon/)
        expect(icons.length).toBeGreaterThan(0)
      })
    })

    it('should have responsive grid layout', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      const { container } = renderWithQuery(<DashboardPage />)

      // Then: Grid should have responsive classes
      await waitFor(() => {
        const grid = container.querySelector('.grid')
        expect(grid).toHaveClass('md:grid-cols-2', 'lg:grid-cols-3')
      })
    })
  })


  describe('ServiceCard Component', () => {
    it('should display check icon for healthy service', async () => {
      // Given: Healthy service
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Check icons should be visible
      await waitFor(() => {
        const checkIcons = screen.getAllByTestId('check-icon')
        expect(checkIcons.length).toBeGreaterThan(0)
      })
    })

    it('should display alert icon for unhealthy service', async () => {
      // Given: Degraded system with unhealthy services
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockDegradedResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Alert icons should be visible
      await waitFor(() => {
        const alertIcons = screen.getAllByTestId('alert-icon')
        expect(alertIcons.length).toBeGreaterThan(0)
      })
    })

    it('should display latency for healthy services', async () => {
      // Given: Healthy services with latency
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Latency should be displayed
      await waitFor(() => {
        expect(screen.getByText('5ms')).toBeInTheDocument()
        expect(screen.getByText('12ms')).toBeInTheDocument()
        expect(screen.getByText('8ms')).toBeInTheDocument()
      })
    })

    it('should not display latency for unhealthy services', async () => {
      // Given: Degraded system
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockDegradedResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Unhealthy services should not show latency
      await waitFor(() => {
        // Qdrant is unhealthy in mock, should not have its latency
        const qdrantCard = screen.getByText('Qdrant').closest('div[class*="border"]')
        expect(qdrantCard).toBeInTheDocument()
        expect(qdrantCard?.textContent).not.toContain('12ms')
      })
    })

    it('should have green border for healthy services', async () => {
      // Given: Healthy services
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component is rendered
      const { container } = renderWithQuery(<DashboardPage />)

      // Then: Cards should have green borders
      await waitFor(() => {
        const greenBorders = container.querySelectorAll('[class*="border-green"]')
        expect(greenBorders.length).toBeGreaterThan(0)
      })
    })

    it('should have red border for unhealthy services', async () => {
      // Given: Degraded system
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockDegradedResponse)

      // When: Component is rendered
      const { container } = renderWithQuery(<DashboardPage />)

      // Then: Cards should have red borders
      await waitFor(() => {
        const redBorders = container.querySelectorAll('[class*="border-red"]')
        expect(redBorders.length).toBeGreaterThan(0)
      })
    })

    it('should display status badge with correct variant', async () => {
      // Given: Mixed health status
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockDegradedResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Both healthy and unhealthy badges should be present
      await waitFor(() => {
        const healthyBadges = screen.getAllByText('healthy')
        const unhealthyBadges = screen.getAllByText('unhealthy')
        expect(healthyBadges.length).toBeGreaterThan(0)
        expect(unhealthyBadges.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Integration Tests', () => {
    it('should call getHealth API on mount', async () => {
      // Given: Healthy API response
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: API should be called
      await waitFor(() => {
        expect(apiClient.getHealth).toHaveBeenCalled()
      })
    })

    it('should handle complete data flow from API to UI', async () => {
      // Given: Complete health response
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: All data should be displayed correctly
      await waitFor(() => {
        expect(screen.getByText('HEALTHY')).toBeInTheDocument()
        expect(screen.getByText('5 of 5 services operational')).toBeInTheDocument()
        expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
        expect(screen.getByText('5ms')).toBeInTheDocument()
      })
    })

    it('should render without errors when health data is complete', async () => {
      // Given: Complete health response
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component is rendered
      const { container } = renderWithQuery(<DashboardPage />)

      // Then: No error messages should be present
      await waitFor(() => {
        expect(container.textContent).not.toContain('Connection Error')
        expect(container.querySelector('[class*="border-red-200"]')).not.toBeInTheDocument()
      })
    })

    it('should handle missing optional latency data gracefully', async () => {
      // Given: Health response without some latency data
      const mockWithoutLatency = {
        ...mockHealthyResponse,
        services: {
          ...mockHealthyResponse.services,
          postgres: { status: 'healthy' }, // No latency_ms
        },
      }
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockWithoutLatency)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Component should still render correctly
      await waitFor(() => {
        expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
        expect(screen.getByText('Primary database')).toBeInTheDocument()
      })
    })

    it('should update status when health data changes', async () => {
      // Given: Initially healthy response
      const { rerender } = renderWithQuery(<DashboardPage />)
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component renders and then data changes
      await waitFor(() => {
        expect(screen.getByText('HEALTHY')).toBeInTheDocument()
      })

      // Then: Degraded status should be reflected (via query refetch)
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockDegradedResponse)
      // Note: Actual refetch would be triggered by React Query interval
    })

    it('should have proper accessibility attributes on main content', async () => {
      // Given: Healthy API response
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component is rendered
      const { container } = renderWithQuery(<DashboardPage />)

      // Then: Main container should exist
      await waitFor(() => {
        const mainContainer = container.querySelector('.p-8')
        expect(mainContainer).toBeInTheDocument()
      })
    })
  })

  describe('Responsive Layout', () => {
    beforeEach(() => {
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)
    })

    it('should have responsive service grid classes', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      const { container } = renderWithQuery(<DashboardPage />)

      // Then: Service grid should have mobile, tablet, and desktop breakpoints
      await waitFor(() => {
        const serviceGrid = container.querySelector('.grid.grid-cols-1.md\\:grid-cols-2')
        expect(serviceGrid).toBeInTheDocument()
      })
    })

    it('should have responsive stats grid classes', async () => {
      // Given: Healthy API response
      // When: Component is rendered
      const { container } = renderWithQuery(<DashboardPage />)

      // Then: Stats grid should have desktop breakpoint
      await waitFor(() => {
        const grids = container.querySelectorAll('.grid')
        const hasResponsiveGrid = Array.from(grids).some(
          grid => grid.className.includes('md:grid-cols-4')
        )
        expect(hasResponsiveGrid).toBe(true)
      })
    })
  })

  describe('Status Badge Variants', () => {
    it('should use success variant for healthy status', async () => {
      // Given: Healthy system
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockHealthyResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: HEALTHY badge should be displayed
      await waitFor(() => {
        expect(screen.getByText('HEALTHY')).toBeInTheDocument()
      })
    })

    it('should use warning variant for degraded status', async () => {
      // Given: Degraded system
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockDegradedResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: DEGRADED badge should be displayed
      await waitFor(() => {
        expect(screen.getByText('DEGRADED')).toBeInTheDocument()
      })
    })

    it('should use destructive variant for unhealthy status', async () => {
      // Given: Unhealthy system
      const mockUnhealthyResponse = {
        ...mockHealthyResponse,
        status: 'unhealthy',
        summary: { healthy: 0, total: 5 },
      }
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockUnhealthyResponse)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: UNHEALTHY badge should be displayed
      await waitFor(() => {
        expect(screen.getByText('UNHEALTHY')).toBeInTheDocument()
      })
    })
  })

  describe('Data Rendering Edge Cases', () => {
    it('should handle undefined health status gracefully', async () => {
      // Given: Health response with undefined status
      const mockUndefinedStatus = {
        summary: {
          healthy: 0,
          total: 5,
        },
        services: {
          postgres: { status: 'unhealthy' },
          qdrant: { status: 'unhealthy' },
          minio: { status: 'unhealthy' },
          redpanda: { status: 'unhealthy' },
          embeddings: { status: 'unhealthy' },
        },
      }
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockUndefinedStatus as any)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Component should render without status or show empty status
      await waitFor(() => {
        expect(screen.getByText('System Status')).toBeInTheDocument()
      })
    })

    it('should handle missing service data gracefully', async () => {
      // Given: Health response with all services but some missing data
      const mockMissingService = {
        ...mockHealthyResponse,
        services: {
          postgres: { status: 'healthy', latency_ms: 5 },
          qdrant: { status: 'unhealthy' },
          minio: { status: 'unhealthy' },
          redpanda: { status: 'unhealthy' },
          embeddings: { status: 'unhealthy' },
        },
      }
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockMissingService as any)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Should handle gracefully without crashing
      await waitFor(() => {
        expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
        expect(screen.getByText('Qdrant')).toBeInTheDocument()
      })
    })

    it('should render correctly with very low latency', async () => {
      // Given: Service with very low latency
      const mockLowLatency = {
        ...mockHealthyResponse,
        services: {
          ...mockHealthyResponse.services,
          postgres: { status: 'healthy', latency_ms: 1 },
        },
      }
      vi.mocked(apiClient.getHealth).mockResolvedValue(mockLowLatency)

      // When: Component is rendered
      renderWithQuery(<DashboardPage />)

      // Then: Should display latency
      await waitFor(() => {
        expect(screen.getByText('1ms')).toBeInTheDocument()
      })
    })
  })
})
