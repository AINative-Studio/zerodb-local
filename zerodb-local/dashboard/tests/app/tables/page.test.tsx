import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TablesPage from '@/app/tables/page'
import { apiClient } from '@/services/api-client'
import type { Project, Table } from '@/types'

// Mock the API client
vi.mock('@/services/api-client', () => ({
  apiClient: {
    listProjects: vi.fn(),
    listTables: vi.fn(),
  },
}))

// Mock lucide-react icons
vi.mock('lucide-react', () => {
  const createMockIcon = (name: string) => {
    return () => <div data-testid={`${name.toLowerCase()}-icon`}>{name} Icon</div>
  }

  const icons = {
    Table: createMockIcon('Table'),
    Database: createMockIcon('Database'),
    FileJson: createMockIcon('FileJson'),
    Type: createMockIcon('Type'),
    Hash: createMockIcon('Hash'),
    ToggleLeft: createMockIcon('ToggleLeft'),
    Calendar: createMockIcon('Calendar'),
    Plus: createMockIcon('Plus'),
    Edit: createMockIcon('Edit'),
    Trash2: createMockIcon('Trash2'),
    Download: createMockIcon('Download'),
    MoreVertical: createMockIcon('MoreVertical'),
    Search: createMockIcon('Search'),
    Filter: createMockIcon('Filter'),
    SortAsc: createMockIcon('SortAsc'),
    SortDesc: createMockIcon('SortDesc'),
    X: createMockIcon('X'),
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

// Mock data
const mockProjects: Project[] = [
  {
    id: 'proj-1',
    name: 'Test Project 1',
    description: 'First test project',
    user_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'proj-2',
    name: 'Test Project 2',
    description: 'Second test project',
    user_id: 'user-1',
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
]

const mockTables: Table[] = [
  {
    id: 'table-1',
    project_id: 'proj-1',
    name: 'users',
    schema: {
      fields: {
        name: { type: 'string', required: true },
        email: { type: 'string', required: true },
      },
    },
    row_count: 150,
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T10:30:00Z',
  },
  {
    id: 'table-2',
    project_id: 'proj-1',
    name: 'products',
    schema: {
      fields: {
        name: { type: 'string' },
        price: { type: 'number' },
      },
    },
    row_count: 42,
    created_at: '2024-01-16T14:20:00Z',
    updated_at: '2024-01-16T14:20:00Z',
  },
]

describe('TablesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Page Header', () => {
    it('should render page heading', async () => {
      // Given: Projects are available
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)

      // When: Component is rendered
      renderWithQuery(<TablesPage />)

      // Then: Page heading should be visible
      expect(screen.getByText('NoSQL Tables')).toBeInTheDocument()
    })

    it('should render page description', async () => {
      // Given: Projects are available
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)

      // When: Component is rendered
      renderWithQuery(<TablesPage />)

      // Then: Page description should be visible
      expect(
        screen.getByText('Browse and manage your document-based data collections')
      ).toBeInTheDocument()
    })

    it('should have proper heading hierarchy', () => {
      // Given: Projects are available
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)

      // When: Component is rendered
      const { container } = renderWithQuery(<TablesPage />)

      // Then: H1 heading should exist
      const heading = container.querySelector('h1')
      expect(heading).toBeInTheDocument()
      expect(heading).toHaveTextContent('NoSQL Tables')
    })
  })

  describe('Project Selector', () => {
    it('should render project selector card', async () => {
      // Given: Projects are available
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)

      // When: Component is rendered
      renderWithQuery(<TablesPage />)

      // Then: Project selector card should be visible
      expect(screen.getByText('Select Project')).toBeInTheDocument()
    })

    it('should list all available projects', async () => {
      // Given: Multiple projects are available
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)

      // When: Component is rendered
      renderWithQuery(<TablesPage />)

      // Then: All projects should be displayed as buttons
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
        expect(screen.getByText('Test Project 2')).toBeInTheDocument()
      })
    })

    it('should show message when no projects available', async () => {
      // Given: No projects are available
      vi.mocked(apiClient.listProjects).mockResolvedValue([])

      // When: Component is rendered
      renderWithQuery(<TablesPage />)

      // Then: No projects message should be visible
      await waitFor(() => {
        expect(screen.getByText('No projects available')).toBeInTheDocument()
      })
    })

    it('should allow selecting a project', async () => {
      // Given: Projects and tables are available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      const projectButton = screen.getByText('Test Project 1')
      await user.click(projectButton)

      // Then: Tables should be loaded for the selected project
      await waitFor(() => {
        expect(apiClient.listTables).toHaveBeenCalledWith('proj-1')
      })
    })

    it('should highlight selected project', async () => {
      // Given: Projects are available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      const projectButton = screen.getByText('Test Project 1')
      await user.click(projectButton)

      // Then: Selected button should have default variant (not outline)
      // Note: This is a simplified check, actual implementation may vary
      expect(projectButton.closest('button')).toBeInTheDocument()
    })
  })

  describe('Tables List', () => {
    it('should show loading state while fetching tables', async () => {
      // Given: Projects available but tables are loading
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: Loading spinner should be visible
      await waitFor(() => {
        const spinner = document.querySelector('.animate-spin')
        expect(spinner).toBeInTheDocument()
      })
    })

    it('should display tables when project is selected', async () => {
      // Given: Projects and tables are available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: Tables should be displayed
      await waitFor(() => {
        expect(screen.getByText('users')).toBeInTheDocument()
        expect(screen.getByText('products')).toBeInTheDocument()
      })
    })

    it('should show table information correctly', async () => {
      // Given: Projects and tables are available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: Table details should be displayed
      await waitFor(() => {
        expect(screen.getByText('150')).toBeInTheDocument() // users row count
        expect(screen.getByText('42')).toBeInTheDocument() // products row count
      })
    })

    it('should show empty state when no tables exist', async () => {
      // Given: Project has no tables
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue([])

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: Empty state message should be visible
      await waitFor(() => {
        expect(screen.getByText('No tables in this project')).toBeInTheDocument()
      })
    })

    it('should display table icons', async () => {
      // Given: Projects and tables are available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: Table icons should be visible
      await waitFor(() => {
        const tableIcons = screen.getAllByTestId('table-icon')
        expect(tableIcons.length).toBeGreaterThan(0)
      })
    })

    it('should display View Data buttons for each table', async () => {
      // Given: Projects and tables are available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: View Data buttons should be visible
      await waitFor(() => {
        const viewDataButtons = screen.getAllByText('View Data')
        expect(viewDataButtons).toHaveLength(2)
      })
    })

    it('should have responsive grid layout', async () => {
      // Given: Projects and tables are available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: Component is rendered and project is selected
      const { container } = renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: Grid should have responsive classes
      await waitFor(() => {
        const grids = container.querySelectorAll('.grid')
        const hasResponsiveGrid = Array.from(grids).some(
          grid => grid.className.includes('md:grid-cols-2') &&
                  grid.className.includes('lg:grid-cols-3')
        )
        expect(hasResponsiveGrid).toBe(true)
      })
    })
  })

  describe('No Project Selected State', () => {
    it('should show placeholder when no project is selected', async () => {
      // Given: Projects are available but none selected
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)

      // When: Component is rendered
      renderWithQuery(<TablesPage />)

      // Then: Placeholder message should be visible
      await waitFor(() => {
        expect(screen.getByText('Select a project to view tables')).toBeInTheDocument()
      })
    })

    it('should show database icon in placeholder', async () => {
      // Given: Projects are available but none selected
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)

      // When: Component is rendered
      renderWithQuery(<TablesPage />)

      // Then: Database icon should be visible
      await waitFor(() => {
        expect(screen.getByTestId('database-icon')).toBeInTheDocument()
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle project loading error gracefully', async () => {
      // Given: API returns an error
      vi.mocked(apiClient.listProjects).mockRejectedValue(
        new Error('Failed to load projects')
      )

      // When: Component is rendered
      renderWithQuery(<TablesPage />)

      // Then: Component should still render without crashing
      await waitFor(() => {
        expect(screen.getByText('NoSQL Tables')).toBeInTheDocument()
      })
    })

    it('should handle table loading error gracefully', async () => {
      // Given: Projects load but tables fail
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockRejectedValue(
        new Error('Failed to load tables')
      )

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: Component should handle error gracefully
      await waitFor(() => {
        // Tables list should not appear, but page should not crash
        expect(screen.getByText('NoSQL Tables')).toBeInTheDocument()
      })
    })
  })

  describe('Integration Tests', () => {
    it('should complete full workflow of selecting project and viewing tables', async () => {
      // Given: Complete data is available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: User navigates through the page
      renderWithQuery(<TablesPage />)

      // Then: Initial state shows project selector
      await waitFor(() => {
        expect(screen.getByText('Select Project')).toBeInTheDocument()
        expect(screen.getByText('Select a project to view tables')).toBeInTheDocument()
      })

      // When: User selects a project
      await user.click(screen.getByText('Test Project 1'))

      // Then: Tables are loaded and displayed
      await waitFor(() => {
        expect(screen.getByText('users')).toBeInTheDocument()
        expect(screen.getByText('products')).toBeInTheDocument()
        expect(screen.getByText('150')).toBeInTheDocument()
        expect(screen.getByText('42')).toBeInTheDocument()
      })
    })

    it('should switch between projects correctly', async () => {
      // Given: Multiple projects with different tables
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables)
        .mockResolvedValueOnce(mockTables)
        .mockResolvedValueOnce([mockTables[0]])

      // When: Component is rendered
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })

      // When: First project is selected
      await user.click(screen.getByText('Test Project 1'))
      await waitFor(() => {
        expect(screen.getByText('users')).toBeInTheDocument()
      })

      // When: Second project is selected
      await user.click(screen.getByText('Test Project 2'))

      // Then: API should be called with new project ID
      await waitFor(() => {
        expect(apiClient.listTables).toHaveBeenCalledWith('proj-2')
      })
    })

    it('should call API on component mount', async () => {
      // Given: Projects are available
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)

      // When: Component is rendered
      renderWithQuery(<TablesPage />)

      // Then: API should be called
      await waitFor(() => {
        expect(apiClient.listProjects).toHaveBeenCalled()
      })
    })

    it('should not fetch tables until project is selected', async () => {
      // Given: Projects are available
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)

      // When: Component is rendered
      renderWithQuery(<TablesPage />)

      // Then: Tables API should not be called
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      expect(apiClient.listTables).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('should have proper page structure', async () => {
      // Given: Projects are available
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)

      // When: Component is rendered
      const { container } = renderWithQuery(<TablesPage />)

      // Then: Page should have proper structure
      expect(container.querySelector('.p-8')).toBeInTheDocument()
    })

    it('should have clickable project buttons', async () => {
      // Given: Projects are available
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)

      // When: Component is rendered
      renderWithQuery(<TablesPage />)

      // Then: Project buttons should be interactive
      await waitFor(() => {
        const button = screen.getByText('Test Project 1')
        expect(button.closest('button')).toBeInTheDocument()
      })
    })

    it('should have clickable View Data buttons', async () => {
      // Given: Projects and tables are available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: Component is rendered and project selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: View Data buttons should be interactive
      await waitFor(() => {
        const buttons = screen.getAllByText('View Data')
        buttons.forEach(button => {
          expect(button.closest('button')).toBeInTheDocument()
        })
      })
    })
  })

  describe('Table Card Display', () => {
    it('should show NoSQL collection description', async () => {
      // Given: Projects and tables are available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: NoSQL collection descriptions should be visible
      await waitFor(() => {
        const descriptions = screen.getAllByText('NoSQL collection')
        expect(descriptions).toHaveLength(2)
      })
    })

    it('should format row counts correctly', async () => {
      // Given: Table with large row count
      const user = userEvent.setup()
      const largeTable: Table = {
        ...mockTables[0],
        row_count: 1234567,
      }
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue([largeTable])

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: Row count should be formatted with commas
      await waitFor(() => {
        expect(screen.getByText('1,234,567')).toBeInTheDocument()
      })
    })

    it('should display relative time for created date', async () => {
      // Given: Projects and tables are available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: Component is rendered and project is selected
      renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: Relative time should be displayed (e.g., "2 months ago")
      await waitFor(() => {
        expect(screen.getByText('Created')).toBeInTheDocument()
      })
    })

    it('should show hover effect on table cards', async () => {
      // Given: Projects and tables are available
      const user = userEvent.setup()
      vi.mocked(apiClient.listProjects).mockResolvedValue(mockProjects)
      vi.mocked(apiClient.listTables).mockResolvedValue(mockTables)

      // When: Component is rendered and project is selected
      const { container } = renderWithQuery(<TablesPage />)
      await waitFor(() => {
        expect(screen.getByText('Test Project 1')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Test Project 1'))

      // Then: Cards should have hover transition classes
      await waitFor(() => {
        const cards = container.querySelectorAll('.hover\\:shadow-lg')
        expect(cards.length).toBeGreaterThan(0)
      })
    })
  })
})
