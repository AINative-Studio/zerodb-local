import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import * as React from 'react'

// Mock component for testing
const SearchFilter = ({
  onSearchChange,
  onFilterChange,
  onSortChange,
  onClearFilters,
}: {
  onSearchChange: (query: string) => void
  onFilterChange: (filters: Record<string, any>) => void
  onSortChange: (sortBy: string, sortOrder: 'asc' | 'desc') => void
  onClearFilters: () => void
}) => {
  const [searchQuery, setSearchQuery] = React.useState('')
  const [activeFilters, setActiveFilters] = React.useState<string[]>([])
  const [sortBy, setSortBy] = React.useState('created_at')
  const [sortOrder, setSortOrder] = React.useState<'asc' | 'desc'>('desc')

  const handleSearchChange = (value: string) => {
    setSearchQuery(value)
    onSearchChange(value)
  }

  const toggleFilter = (filter: string) => {
    const newFilters = activeFilters.includes(filter)
      ? activeFilters.filter(f => f !== filter)
      : [...activeFilters, filter]
    setActiveFilters(newFilters)

    const filterObject: Record<string, any> = {}
    newFilters.forEach(f => {
      filterObject[f] = true
    })
    onFilterChange(filterObject)
  }

  const handleSortChange = (field: string) => {
    setSortBy(field)
    onSortChange(field, sortOrder)
  }

  const handleSortOrderToggle = () => {
    const newOrder = sortOrder === 'asc' ? 'desc' : 'asc'
    setSortOrder(newOrder)
    onSortChange(sortBy, newOrder)
  }

  const handleClearAll = () => {
    setSearchQuery('')
    setActiveFilters([])
    setSortBy('created_at')
    setSortOrder('desc')
    onClearFilters()
  }

  return (
    <div data-testid="search-filter">
      <div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="Search tables..."
          aria-label="Search tables"
        />
      </div>

      <div data-testid="filter-buttons">
        <h3>Filter by Type</h3>
        <button
          onClick={() => toggleFilter('has_schema')}
          data-active={activeFilters.includes('has_schema')}
          aria-pressed={activeFilters.includes('has_schema')}
        >
          Has Schema
        </button>
        <button
          onClick={() => toggleFilter('empty')}
          data-active={activeFilters.includes('empty')}
          aria-pressed={activeFilters.includes('empty')}
        >
          Empty Tables
        </button>
        <button
          onClick={() => toggleFilter('large')}
          data-active={activeFilters.includes('large')}
          aria-pressed={activeFilters.includes('large')}
        >
          Large Tables (&gt;1000 rows)
        </button>
      </div>

      <div data-testid="sort-controls">
        <h3>Sort by</h3>
        <select
          value={sortBy}
          onChange={(e) => handleSortChange(e.target.value)}
          aria-label="Sort by field"
        >
          <option value="name">Name</option>
          <option value="created_at">Date Created</option>
          <option value="row_count">Row Count</option>
          <option value="updated_at">Last Updated</option>
        </select>
        <button
          onClick={handleSortOrderToggle}
          aria-label={`Sort order: ${sortOrder}`}
        >
          {sortOrder === 'asc' ? '↑ Ascending' : '↓ Descending'}
        </button>
      </div>

      <div>
        <button
          onClick={handleClearAll}
          aria-label="Clear all filters"
          data-testid="clear-filters"
        >
          Clear Filters
        </button>
      </div>

      {(searchQuery || activeFilters.length > 0) && (
        <div data-testid="active-filters">
          <span>Active: </span>
          {searchQuery && <span>Search: "{searchQuery}"</span>}
          {activeFilters.map(filter => (
            <span key={filter}>{filter}</span>
          ))}
        </div>
      )}
    </div>
  )
}

describe('SearchFilter', () => {
  let mockOnSearchChange: ReturnType<typeof vi.fn>
  let mockOnFilterChange: ReturnType<typeof vi.fn>
  let mockOnSortChange: ReturnType<typeof vi.fn>
  let mockOnClearFilters: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockOnSearchChange = vi.fn()
    mockOnFilterChange = vi.fn()
    mockOnSortChange = vi.fn()
    mockOnClearFilters = vi.fn()
  })

  describe('Component Rendering', () => {
    it('should render search filter component', () => {
      // Given: Component props
      // When: Component is rendered
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Component should be visible
      expect(screen.getByTestId('search-filter')).toBeInTheDocument()
    })

    it('should render search input', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Search input should be visible
      expect(screen.getByLabelText('Search tables')).toBeInTheDocument()
    })

    it('should render filter buttons section', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Filter buttons section should be visible
      expect(screen.getByTestId('filter-buttons')).toBeInTheDocument()
      expect(screen.getByText('Filter by Type')).toBeInTheDocument()
    })

    it('should render sort controls section', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Sort controls should be visible
      expect(screen.getByTestId('sort-controls')).toBeInTheDocument()
      expect(screen.getByText('Sort by')).toBeInTheDocument()
    })

    it('should render clear filters button', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Clear button should be visible
      expect(screen.getByTestId('clear-filters')).toBeInTheDocument()
    })
  })

  describe('Search Input', () => {
    it('should have search placeholder', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Placeholder should be visible
      expect(screen.getByPlaceholderText('Search tables...')).toBeInTheDocument()
    })

    it('should update search query on input', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User types in search input
      const searchInput = screen.getByLabelText('Search tables')
      await user.type(searchInput, 'users')

      // Then: Input value should be updated
      expect(searchInput).toHaveValue('users')
    })

    it('should call onSearchChange when typing', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User types in search input
      const searchInput = screen.getByLabelText('Search tables')
      await user.type(searchInput, 'test')

      // Then: onSearchChange should be called for each character
      expect(mockOnSearchChange).toHaveBeenCalledWith('t')
      expect(mockOnSearchChange).toHaveBeenCalledWith('te')
      expect(mockOnSearchChange).toHaveBeenCalledWith('tes')
      expect(mockOnSearchChange).toHaveBeenCalledWith('test')
    })

    it('should show active search in indicator', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User searches
      const searchInput = screen.getByLabelText('Search tables')
      await user.type(searchInput, 'users')

      // Then: Active filters should show search
      expect(screen.getByTestId('active-filters')).toHaveTextContent('Search: "users"')
    })
  })

  describe('Filter Buttons', () => {
    it('should render all filter buttons', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: All filter buttons should be visible
      expect(screen.getByText('Has Schema')).toBeInTheDocument()
      expect(screen.getByText('Empty Tables')).toBeInTheDocument()
      expect(screen.getByText(/Large Tables/i)).toBeInTheDocument()
    })

    it('should toggle filter when button is clicked', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User clicks filter button
      const filterButton = screen.getByText('Has Schema')
      await user.click(filterButton)

      // Then: Button should be marked as active
      expect(filterButton).toHaveAttribute('data-active', 'true')
      expect(filterButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('should call onFilterChange when filter is toggled', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User clicks filter button
      await user.click(screen.getByText('Has Schema'))

      // Then: onFilterChange should be called with filter object
      expect(mockOnFilterChange).toHaveBeenCalledWith({ has_schema: true })
    })

    it('should deactivate filter when clicked again', async () => {
      // Given: Filter is active
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )
      const filterButton = screen.getByText('Empty Tables')
      await user.click(filterButton)

      // When: User clicks same filter again
      await user.click(filterButton)

      // Then: Filter should be deactivated
      expect(filterButton).toHaveAttribute('data-active', 'false')
      expect(filterButton).toHaveAttribute('aria-pressed', 'false')
    })

    it('should allow multiple filters to be active', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User activates multiple filters
      await user.click(screen.getByText('Has Schema'))
      await user.click(screen.getByText('Empty Tables'))

      // Then: Both filters should be active
      expect(screen.getByText('Has Schema')).toHaveAttribute('data-active', 'true')
      expect(screen.getByText('Empty Tables')).toHaveAttribute('data-active', 'true')
    })

    it('should call onFilterChange with multiple filters', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User activates multiple filters
      await user.click(screen.getByText('Has Schema'))
      await user.click(screen.getByText('Empty Tables'))

      // Then: onFilterChange should be called with both filters
      expect(mockOnFilterChange).toHaveBeenLastCalledWith({
        has_schema: true,
        empty: true,
      })
    })

    it('should show active filters in indicator', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User activates a filter
      await user.click(screen.getByText('Has Schema'))

      // Then: Active filters should show the filter
      expect(screen.getByTestId('active-filters')).toHaveTextContent('has_schema')
    })
  })

  describe('Sort Controls', () => {
    it('should render sort dropdown', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Sort dropdown should be visible
      expect(screen.getByLabelText('Sort by field')).toBeInTheDocument()
    })

    it('should have default sort value', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Default sort should be 'created_at'
      expect(screen.getByLabelText('Sort by field')).toHaveValue('created_at')
    })

    it('should render all sort options', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: All sort options should be available
      expect(screen.getByRole('option', { name: 'Name' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Date Created' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Row Count' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Last Updated' })).toBeInTheDocument()
    })

    it('should call onSortChange when sort field is changed', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User changes sort field
      const sortSelect = screen.getByLabelText('Sort by field')
      await user.selectOptions(sortSelect, 'name')

      // Then: onSortChange should be called
      expect(mockOnSortChange).toHaveBeenCalledWith('name', 'desc')
    })

    it('should render sort order button', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Sort order button should be visible
      expect(screen.getByLabelText('Sort order: desc')).toBeInTheDocument()
    })

    it('should show descending by default', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Descending should be shown
      expect(screen.getByText('↓ Descending')).toBeInTheDocument()
    })

    it('should toggle sort order when clicked', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User clicks sort order button
      await user.click(screen.getByLabelText('Sort order: desc'))

      // Then: Sort order should change to ascending
      expect(screen.getByText('↑ Ascending')).toBeInTheDocument()
    })

    it('should call onSortChange when sort order is toggled', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User toggles sort order
      await user.click(screen.getByLabelText('Sort order: desc'))

      // Then: onSortChange should be called with new order
      expect(mockOnSortChange).toHaveBeenCalledWith('created_at', 'asc')
    })

    it('should toggle back to descending', async () => {
      // Given: Sort is ascending
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )
      await user.click(screen.getByLabelText('Sort order: desc'))

      // When: User toggles again
      await user.click(screen.getByLabelText('Sort order: asc'))

      // Then: Should change back to descending
      expect(screen.getByText('↓ Descending')).toBeInTheDocument()
    })
  })

  describe('Clear Filters', () => {
    it('should render clear filters button', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Clear button should be visible
      expect(screen.getByLabelText('Clear all filters')).toBeInTheDocument()
    })

    it('should clear search query when clicked', async () => {
      // Given: Search query is entered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )
      await user.type(screen.getByLabelText('Search tables'), 'test')

      // When: User clicks clear filters
      await user.click(screen.getByLabelText('Clear all filters'))

      // Then: Search should be cleared
      expect(screen.getByLabelText('Search tables')).toHaveValue('')
    })

    it('should clear active filters when clicked', async () => {
      // Given: Filters are active
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )
      await user.click(screen.getByText('Has Schema'))
      expect(screen.getByText('Has Schema')).toHaveAttribute('data-active', 'true')

      // When: User clicks clear filters
      await user.click(screen.getByLabelText('Clear all filters'))

      // Then: Filters should be cleared
      expect(screen.getByText('Has Schema')).toHaveAttribute('data-active', 'false')
    })

    it('should reset sort to default when clicked', async () => {
      // Given: Sort is changed
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )
      await user.selectOptions(screen.getByLabelText('Sort by field'), 'name')

      // When: User clicks clear filters
      await user.click(screen.getByLabelText('Clear all filters'))

      // Then: Sort should reset to default
      expect(screen.getByLabelText('Sort by field')).toHaveValue('created_at')
    })

    it('should reset sort order to default when clicked', async () => {
      // Given: Sort order is changed
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )
      await user.click(screen.getByLabelText('Sort order: desc'))

      // When: User clicks clear filters
      await user.click(screen.getByLabelText('Clear all filters'))

      // Then: Sort order should reset
      expect(screen.getByText('↓ Descending')).toBeInTheDocument()
    })

    it('should call onClearFilters when clicked', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User clicks clear filters
      await user.click(screen.getByLabelText('Clear all filters'))

      // Then: onClearFilters should be called
      expect(mockOnClearFilters).toHaveBeenCalled()
    })

    it('should hide active filters indicator after clearing', async () => {
      // Given: Filters are active
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )
      await user.type(screen.getByLabelText('Search tables'), 'test')
      expect(screen.getByTestId('active-filters')).toBeInTheDocument()

      // When: User clears filters
      await user.click(screen.getByLabelText('Clear all filters'))

      // Then: Active filters indicator should be hidden
      expect(screen.queryByTestId('active-filters')).not.toBeInTheDocument()
    })
  })

  describe('Active Filters Indicator', () => {
    it('should not show indicator by default', () => {
      // Given: Component is rendered without filters
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Indicator should not be visible
      expect(screen.queryByTestId('active-filters')).not.toBeInTheDocument()
    })

    it('should show indicator when search is active', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User searches
      await user.type(screen.getByLabelText('Search tables'), 'test')

      // Then: Indicator should be visible
      expect(screen.getByTestId('active-filters')).toBeInTheDocument()
    })

    it('should show indicator when filters are active', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User activates a filter
      await user.click(screen.getByText('Empty Tables'))

      // Then: Indicator should be visible
      expect(screen.getByTestId('active-filters')).toBeInTheDocument()
    })

    it('should show all active items in indicator', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User adds search and filters
      await user.type(screen.getByLabelText('Search tables'), 'test')
      await user.click(screen.getByText('Has Schema'))
      await user.click(screen.getByText('Empty Tables'))

      // Then: All active items should be shown
      const indicator = screen.getByTestId('active-filters')
      expect(indicator).toHaveTextContent('Search: "test"')
      expect(indicator).toHaveTextContent('has_schema')
      expect(indicator).toHaveTextContent('empty')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels for all inputs', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: All inputs should have ARIA labels
      expect(screen.getByLabelText('Search tables')).toBeInTheDocument()
      expect(screen.getByLabelText('Sort by field')).toBeInTheDocument()
      expect(screen.getByLabelText('Sort order: desc')).toBeInTheDocument()
      expect(screen.getByLabelText('Clear all filters')).toBeInTheDocument()
    })

    it('should have aria-pressed for filter buttons', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: Filter buttons should have aria-pressed
      expect(screen.getByText('Has Schema')).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByText('Empty Tables')).toHaveAttribute('aria-pressed', 'false')
    })

    it('should update aria-pressed when filter is toggled', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User activates filter
      const filterButton = screen.getByText('Has Schema')
      await user.click(filterButton)

      // Then: aria-pressed should be true
      expect(filterButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('should have clickable buttons', () => {
      // Given: Component is rendered
      // When: Component loads
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // Then: All buttons should be properly rendered
      expect(screen.getByText('Has Schema').closest('button')).toBeInTheDocument()
      expect(screen.getByText('↓ Descending').closest('button')).toBeInTheDocument()
      expect(screen.getByLabelText('Clear all filters').closest('button')).toBeInTheDocument()
    })

    it('should support keyboard navigation', async () => {
      // Given: Component is rendered
      const user = userEvent.setup()
      render(
        <SearchFilter
          onSearchChange={mockOnSearchChange}
          onFilterChange={mockOnFilterChange}
          onSortChange={mockOnSortChange}
          onClearFilters={mockOnClearFilters}
        />
      )

      // When: User tabs through elements
      const searchInput = screen.getByLabelText('Search tables')
      await user.tab()

      // Then: Focus should move to first element
      expect(searchInput).toHaveFocus()
    })
  })
})
