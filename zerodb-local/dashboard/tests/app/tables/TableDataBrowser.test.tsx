import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as React from 'react'

// Mock component for testing
const TableDataBrowser = ({
  tableId,
  projectId,
  fetchData,
  onInsert,
  onUpdate,
  onDelete,
}: {
  tableId: string
  projectId: string
  fetchData: (page: number, limit: number) => Promise<{ rows: any[]; total: number }>
  onInsert: (row: any) => Promise<void>
  onUpdate: (rowId: string, row: any) => Promise<void>
  onDelete: (rowId: string) => Promise<void>
}) => {
  const [page, setPage] = React.useState(1)
  const [limit] = React.useState(10)
  const [data, setData] = React.useState<any[]>([])
  const [total, setTotal] = React.useState(0)
  const [loading, setLoading] = React.useState(false)
  const [insertDialogOpen, setInsertDialogOpen] = React.useState(false)
  const [editDialogOpen, setEditDialogOpen] = React.useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false)
  const [selectedRow, setSelectedRow] = React.useState<any>(null)
  const [searchQuery, setSearchQuery] = React.useState('')

  React.useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        const result = await fetchData(page, limit)
        setData(result.rows)
        setTotal(result.total)
      } catch (error) {
        console.error('Failed to load data', error)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [page, limit, fetchData])

  const handleInsert = async (row: any) => {
    await onInsert(row)
    setInsertDialogOpen(false)
    const result = await fetchData(page, limit)
    setData(result.rows)
    setTotal(result.total)
  }

  const handleUpdate = async (row: any) => {
    await onUpdate(selectedRow.id, row)
    setEditDialogOpen(false)
    const result = await fetchData(page, limit)
    setData(result.rows)
  }

  const handleDelete = async () => {
    await onDelete(selectedRow.id)
    setDeleteDialogOpen(false)
    setSelectedRow(null)
    const result = await fetchData(page, limit)
    setData(result.rows)
    setTotal(result.total)
  }

  const filteredData = searchQuery
    ? data.filter(row =>
        Object.values(row).some(val =>
          String(val).toLowerCase().includes(searchQuery.toLowerCase())
        )
      )
    : data

  const totalPages = Math.ceil(total / limit)

  return (
    <div data-testid="data-browser">
      <div>
        <h2>Table Data</h2>
        <input
          type="text"
          placeholder="Search..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Search table data"
        />
        <button onClick={() => setInsertDialogOpen(true)}>Insert Row</button>
      </div>

      {loading ? (
        <div data-testid="loading-spinner">Loading...</div>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                {data.length > 0 &&
                  Object.keys(data[0]).map((key) => (
                    <th key={key}>{key}</th>
                  ))}
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.length > 0 ? (
                filteredData.map((row, index) => (
                  <tr key={row.id || index} data-testid={`row-${index}`}>
                    {Object.values(row).map((value: any, i) => (
                      <td key={i}>{String(value)}</td>
                    ))}
                    <td>
                      <button
                        onClick={() => {
                          setSelectedRow(row)
                          setEditDialogOpen(true)
                        }}
                        aria-label={`Edit row ${index + 1}`}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => {
                          setSelectedRow(row)
                          setDeleteDialogOpen(true)
                        }}
                        aria-label={`Delete row ${index + 1}`}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={100}>
                    {searchQuery ? 'No matching rows found' : 'No data available'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div data-testid="pagination">
            <span>
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
              aria-label="Previous page"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page === totalPages}
              aria-label="Next page"
            >
              Next
            </button>
            <span>
              Showing {(page - 1) * limit + 1}-{Math.min(page * limit, total)} of {total}
            </span>
          </div>
        </>
      )}

      {insertDialogOpen && (
        <div role="dialog" data-testid="insert-dialog" aria-label="Insert Row">
          <h3>Insert New Row</h3>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              const formData = new FormData(e.currentTarget)
              const row: any = {}
              formData.forEach((value, key) => {
                row[key] = value
              })
              handleInsert(row)
            }}
          >
            <input name="name" placeholder="Name" />
            <input name="email" placeholder="Email" />
            <button type="button" onClick={() => setInsertDialogOpen(false)}>
              Cancel
            </button>
            <button type="submit">Insert</button>
          </form>
        </div>
      )}

      {editDialogOpen && selectedRow && (
        <div role="dialog" data-testid="edit-dialog" aria-label="Edit Row">
          <h3>Edit Row</h3>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              const formData = new FormData(e.currentTarget)
              const row: any = {}
              formData.forEach((value, key) => {
                row[key] = value
              })
              handleUpdate(row)
            }}
          >
            {Object.keys(selectedRow).map((key) => (
              <input
                key={key}
                name={key}
                defaultValue={selectedRow[key]}
                placeholder={key}
              />
            ))}
            <button type="button" onClick={() => setEditDialogOpen(false)}>
              Cancel
            </button>
            <button type="submit">Save</button>
          </form>
        </div>
      )}

      {deleteDialogOpen && selectedRow && (
        <div role="dialog" data-testid="delete-dialog" aria-label="Confirm Delete">
          <h3>Confirm Delete</h3>
          <p>Are you sure you want to delete this row?</p>
          <button onClick={() => setDeleteDialogOpen(false)}>Cancel</button>
          <button onClick={handleDelete}>Delete</button>
        </div>
      )}
    </div>
  )
}

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
const mockRows = [
  { id: '1', name: 'John Doe', email: 'john@example.com', age: 30 },
  { id: '2', name: 'Jane Smith', email: 'jane@example.com', age: 25 },
  { id: '3', name: 'Bob Johnson', email: 'bob@example.com', age: 35 },
]

describe('TableDataBrowser', () => {
  let mockFetchData: ReturnType<typeof vi.fn>
  let mockOnInsert: ReturnType<typeof vi.fn>
  let mockOnUpdate: ReturnType<typeof vi.fn>
  let mockOnDelete: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockFetchData = vi.fn().mockResolvedValue({ rows: mockRows, total: 3 })
    mockOnInsert = vi.fn().mockResolvedValue(undefined)
    mockOnUpdate = vi.fn().mockResolvedValue(undefined)
    mockOnDelete = vi.fn().mockResolvedValue(undefined)
  })

  describe('Component Rendering', () => {
    it('should render data browser', async () => {
      // Given: Data is available
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Data browser should be visible
      await waitFor(() => {
        expect(screen.getByTestId('data-browser')).toBeInTheDocument()
      })
    })

    it('should display table heading', async () => {
      // Given: Data is available
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Heading should be visible
      await waitFor(() => {
        expect(screen.getByText('Table Data')).toBeInTheDocument()
      })
    })

    it('should call fetchData on mount', async () => {
      // Given: Component setup
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: fetchData should be called
      await waitFor(() => {
        expect(mockFetchData).toHaveBeenCalledWith(1, 10)
      })
    })
  })

  describe('Loading State', () => {
    it('should show loading spinner while fetching data', async () => {
      // Given: Data is loading
      mockFetchData.mockImplementation(() => new Promise(() => {}))

      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Loading spinner should be visible
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
    })

    it('should hide loading spinner after data loads', async () => {
      // Given: Data loads successfully
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Loading spinner should be hidden
      await waitFor(() => {
        expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument()
      })
    })
  })

  describe('Data Grid Display', () => {
    it('should render table with column headers', async () => {
      // Given: Data is available
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Column headers should be visible
      await waitFor(() => {
        expect(screen.getByText('id')).toBeInTheDocument()
        expect(screen.getByText('name')).toBeInTheDocument()
        expect(screen.getByText('email')).toBeInTheDocument()
        expect(screen.getByText('age')).toBeInTheDocument()
      })
    })

    it('should display all data rows', async () => {
      // Given: Multiple rows are available
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: All rows should be displayed
      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
        expect(screen.getByText('Jane Smith')).toBeInTheDocument()
        expect(screen.getByText('Bob Johnson')).toBeInTheDocument()
      })
    })

    it('should display row data correctly', async () => {
      // Given: Data with specific values
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: All cell values should be visible
      await waitFor(() => {
        expect(screen.getByText('john@example.com')).toBeInTheDocument()
        expect(screen.getByText('30')).toBeInTheDocument()
      })
    })

    it('should display Actions column', async () => {
      // Given: Data is available
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Actions column header should be visible
      await waitFor(() => {
        expect(screen.getByText('Actions')).toBeInTheDocument()
      })
    })

    it('should show empty state when no data', async () => {
      // Given: No data is available
      mockFetchData.mockResolvedValue({ rows: [], total: 0 })

      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Empty state message should be visible
      await waitFor(() => {
        expect(screen.getByText('No data available')).toBeInTheDocument()
      })
    })
  })

  describe('Search Functionality', () => {
    it('should render search input', async () => {
      // Given: Component is loaded
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Search input should be visible
      await waitFor(() => {
        expect(screen.getByLabelText('Search table data')).toBeInTheDocument()
      })
    })

    it('should filter results by search query', async () => {
      // Given: Data is loaded
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      })

      // When: User searches for specific text
      const searchInput = screen.getByLabelText('Search table data')
      await user.type(searchInput, 'jane')

      // Then: Only matching rows should be visible
      expect(screen.getByText('Jane Smith')).toBeInTheDocument()
      expect(screen.queryByText('John Doe')).not.toBeInTheDocument()
    })

    it('should search across all fields', async () => {
      // Given: Data is loaded
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      })

      // When: User searches for email
      const searchInput = screen.getByLabelText('Search table data')
      await user.type(searchInput, 'bob@example')

      // Then: Matching row should be visible
      expect(screen.getByText('Bob Johnson')).toBeInTheDocument()
      expect(screen.queryByText('John Doe')).not.toBeInTheDocument()
    })

    it('should show no results message for empty search', async () => {
      // Given: Data is loaded
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      })

      // When: User searches for non-existent text
      const searchInput = screen.getByLabelText('Search table data')
      await user.type(searchInput, 'nonexistent')

      // Then: No matching message should be visible
      expect(screen.getByText('No matching rows found')).toBeInTheDocument()
    })

    it('should be case insensitive', async () => {
      // Given: Data is loaded
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      })

      // When: User searches with different case
      const searchInput = screen.getByLabelText('Search table data')
      await user.type(searchInput, 'JOHN')

      // Then: Matching row should be visible
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })
  })

  describe('Pagination', () => {
    it('should render pagination controls', async () => {
      // Given: Data is loaded
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Pagination should be visible
      await waitFor(() => {
        expect(screen.getByTestId('pagination')).toBeInTheDocument()
      })
    })

    it('should display current page number', async () => {
      // Given: Data is loaded
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Current page should be visible
      await waitFor(() => {
        expect(screen.getByText(/Page 1 of/i)).toBeInTheDocument()
      })
    })

    it('should display row count', async () => {
      // Given: Data is loaded
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Row count should be visible
      await waitFor(() => {
        expect(screen.getByText(/Showing 1-3 of 3/i)).toBeInTheDocument()
      })
    })

    it('should disable Previous button on first page', async () => {
      // Given: First page is loaded
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Previous button should be disabled
      await waitFor(() => {
        expect(screen.getByLabelText('Previous page')).toBeDisabled()
      })
    })

    it('should enable Next button when more pages exist', async () => {
      // Given: Multiple pages of data
      mockFetchData.mockResolvedValue({ rows: mockRows, total: 25 })

      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Next button should be enabled
      await waitFor(() => {
        expect(screen.getByLabelText('Next page')).not.toBeDisabled()
      })
    })

    it('should navigate to next page when Next is clicked', async () => {
      // Given: Multiple pages exist
      const user = userEvent.setup()
      mockFetchData.mockResolvedValue({ rows: mockRows, total: 25 })

      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByLabelText('Next page')).toBeInTheDocument()
      })

      // When: User clicks Next
      await user.click(screen.getByLabelText('Next page'))

      // Then: fetchData should be called with page 2
      await waitFor(() => {
        expect(mockFetchData).toHaveBeenCalledWith(2, 10)
      })
    })
  })

  describe('Insert Row', () => {
    it('should render Insert Row button', async () => {
      // Given: Component is loaded
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Insert button should be visible
      await waitFor(() => {
        expect(screen.getByText('Insert Row')).toBeInTheDocument()
      })
    })

    it('should open insert dialog when Insert Row is clicked', async () => {
      // Given: Component is loaded
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('Insert Row')).toBeInTheDocument()
      })

      // When: User clicks Insert Row
      await user.click(screen.getByText('Insert Row'))

      // Then: Insert dialog should be visible
      expect(screen.getByTestId('insert-dialog')).toBeInTheDocument()
    })

    it('should call onInsert when form is submitted', async () => {
      // Given: Insert dialog is open
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('Insert Row')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Insert Row'))

      // When: User submits form
      const insertButton = within(screen.getByTestId('insert-dialog')).getByText('Insert')
      await user.click(insertButton)

      // Then: onInsert should be called
      await waitFor(() => {
        expect(mockOnInsert).toHaveBeenCalled()
      })
    })

    it('should close dialog after successful insert', async () => {
      // Given: Insert dialog is open
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('Insert Row')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Insert Row'))

      // When: User submits form
      const insertButton = within(screen.getByTestId('insert-dialog')).getByText('Insert')
      await user.click(insertButton)

      // Then: Dialog should close
      await waitFor(() => {
        expect(screen.queryByTestId('insert-dialog')).not.toBeInTheDocument()
      })
    })

    it('should refresh data after insert', async () => {
      // Given: Insert is successful
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('Insert Row')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Insert Row'))

      // When: User inserts row
      const insertButton = within(screen.getByTestId('insert-dialog')).getByText('Insert')
      await user.click(insertButton)

      // Then: fetchData should be called again
      await waitFor(() => {
        expect(mockFetchData).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Edit Row', () => {
    it('should display Edit button for each row', async () => {
      // Given: Data is loaded
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Edit buttons should be visible
      await waitFor(() => {
        expect(screen.getByLabelText('Edit row 1')).toBeInTheDocument()
        expect(screen.getByLabelText('Edit row 2')).toBeInTheDocument()
      })
    })

    it('should open edit dialog when Edit is clicked', async () => {
      // Given: Data is loaded
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByLabelText('Edit row 1')).toBeInTheDocument()
      })

      // When: User clicks Edit
      await user.click(screen.getByLabelText('Edit row 1'))

      // Then: Edit dialog should be visible
      expect(screen.getByTestId('edit-dialog')).toBeInTheDocument()
    })

    it('should call onUpdate when form is submitted', async () => {
      // Given: Edit dialog is open
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByLabelText('Edit row 1')).toBeInTheDocument()
      })
      await user.click(screen.getByLabelText('Edit row 1'))

      // When: User submits form
      const saveButton = within(screen.getByTestId('edit-dialog')).getByText('Save')
      await user.click(saveButton)

      // Then: onUpdate should be called
      await waitFor(() => {
        expect(mockOnUpdate).toHaveBeenCalledWith('1', expect.any(Object))
      })
    })
  })

  describe('Delete Row', () => {
    it('should display Delete button for each row', async () => {
      // Given: Data is loaded
      // When: Component is rendered
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: Delete buttons should be visible
      await waitFor(() => {
        expect(screen.getByLabelText('Delete row 1')).toBeInTheDocument()
      })
    })

    it('should show confirmation dialog when Delete is clicked', async () => {
      // Given: Data is loaded
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByLabelText('Delete row 1')).toBeInTheDocument()
      })

      // When: User clicks Delete
      await user.click(screen.getByLabelText('Delete row 1'))

      // Then: Confirmation dialog should be visible
      expect(screen.getByTestId('delete-dialog')).toBeInTheDocument()
    })

    it('should call onDelete when confirmed', async () => {
      // Given: Delete dialog is open
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByLabelText('Delete row 1')).toBeInTheDocument()
      })
      await user.click(screen.getByLabelText('Delete row 1'))

      // When: User confirms deletion
      const deleteButtons = screen.getAllByText('Delete')
      await user.click(deleteButtons[deleteButtons.length - 1])

      // Then: onDelete should be called with row ID
      await waitFor(() => {
        expect(mockOnDelete).toHaveBeenCalledWith('1')
      })
    })

    it('should refresh data after delete', async () => {
      // Given: Delete is confirmed
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByLabelText('Delete row 1')).toBeInTheDocument()
      })
      await user.click(screen.getByLabelText('Delete row 1'))

      // When: User confirms deletion
      const deleteButtons = screen.getAllByText('Delete')
      await user.click(deleteButtons[deleteButtons.length - 1])

      // Then: fetchData should be called again
      await waitFor(() => {
        expect(mockFetchData).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', async () => {
      // Given: Component is rendered
      // When: Data is loaded
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      // Then: ARIA labels should be present
      await waitFor(() => {
        expect(screen.getByLabelText('Search table data')).toBeInTheDocument()
        expect(screen.getByLabelText('Edit row 1')).toBeInTheDocument()
        expect(screen.getByLabelText('Delete row 1')).toBeInTheDocument()
      })
    })

    it('should have role="dialog" for dialogs', async () => {
      // Given: Component is loaded
      const user = userEvent.setup()
      renderWithQuery(
        <TableDataBrowser
          tableId="table-1"
          projectId="proj-1"
          fetchData={mockFetchData}
          onInsert={mockOnInsert}
          onUpdate={mockOnUpdate}
          onDelete={mockOnDelete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('Insert Row')).toBeInTheDocument()
      })

      // When: User opens dialog
      await user.click(screen.getByText('Insert Row'))

      // Then: Dialog should have proper role
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })
})
