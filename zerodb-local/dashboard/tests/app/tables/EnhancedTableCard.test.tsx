import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import * as React from 'react'
import type { Table } from '@/types'

// Mock component for testing
const EnhancedTableCard = ({
  table,
  onEdit,
  onDelete,
  onExport,
  onViewData,
}: {
  table: Table
  onEdit: (table: Table) => void
  onDelete: (tableId: string) => void
  onExport: (tableId: string) => void
  onViewData: (tableId: string) => void
}) => {
  const [menuOpen, setMenuOpen] = React.useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false)

  const handleDelete = () => {
    onDelete(table.id)
    setDeleteDialogOpen(false)
  }

  const schemaFields = table.schema?.fields ? Object.keys(table.schema.fields) : []

  return (
    <div data-testid="table-card">
      <div>
        <h3>{table.name}</h3>
        <p>NoSQL Collection</p>
      </div>

      <div>
        <div>
          <span>Rows:</span>
          <span>{table.row_count.toLocaleString()}</span>
        </div>
        <div>
          <span>Fields:</span>
          <span>{schemaFields.length}</span>
        </div>
        <div>
          <span>Created:</span>
          <span>{new Date(table.created_at).toLocaleDateString()}</span>
        </div>
      </div>

      <div>
        <h4>Schema Preview</h4>
        {schemaFields.length > 0 ? (
          <ul>
            {schemaFields.slice(0, 3).map((field) => (
              <li key={field}>
                {field}: {table.schema?.fields[field]?.type || 'string'}
              </li>
            ))}
            {schemaFields.length > 3 && (
              <li>+{schemaFields.length - 3} more fields</li>
            )}
          </ul>
        ) : (
          <p>No schema defined</p>
        )}
      </div>

      <div>
        <button onClick={() => onViewData(table.id)}>View Data</button>
        <button onClick={() => setMenuOpen(!menuOpen)} aria-label="Table actions">
          Actions
        </button>
      </div>

      {menuOpen && (
        <div role="menu" data-testid="actions-menu">
          <button role="menuitem" onClick={() => onEdit(table)}>
            Edit Schema
          </button>
          <button role="menuitem" onClick={() => onExport(table.id)}>
            Export Data
          </button>
          <button role="menuitem" onClick={() => setDeleteDialogOpen(true)}>
            Delete Table
          </button>
        </div>
      )}

      {deleteDialogOpen && (
        <div role="dialog" aria-label="Confirm Delete" data-testid="delete-dialog">
          <h3>Confirm Delete</h3>
          <p>Are you sure you want to delete table "{table.name}"?</p>
          <p>This action cannot be undone.</p>
          <button onClick={() => setDeleteDialogOpen(false)}>Cancel</button>
          <button onClick={handleDelete}>Delete</button>
        </div>
      )}
    </div>
  )
}

// Mock data
const mockTable: Table = {
  id: 'table-1',
  project_id: 'proj-1',
  name: 'users',
  schema: {
    fields: {
      id: { type: 'string', required: true },
      email: { type: 'string', required: true },
      name: { type: 'string', required: false },
      age: { type: 'number', required: false },
      active: { type: 'boolean', required: false },
    },
  },
  row_count: 1234,
  created_at: '2024-01-15T10:30:00Z',
  updated_at: '2024-01-15T10:30:00Z',
}

const mockTableNoSchema: Table = {
  id: 'table-2',
  project_id: 'proj-1',
  name: 'empty_table',
  row_count: 0,
  created_at: '2024-01-20T14:00:00Z',
  updated_at: '2024-01-20T14:00:00Z',
}

describe('EnhancedTableCard', () => {
  let mockOnEdit: ReturnType<typeof vi.fn>
  let mockOnDelete: ReturnType<typeof vi.fn>
  let mockOnExport: ReturnType<typeof vi.fn>
  let mockOnViewData: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockOnEdit = vi.fn()
    mockOnDelete = vi.fn()
    mockOnExport = vi.fn()
    mockOnViewData = vi.fn()
  })

  describe('Card Display', () => {
    it('should render table card', () => {
      // Given: Table data
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Card should be visible
      expect(screen.getByTestId('table-card')).toBeInTheDocument()
    })

    it('should display table name', () => {
      // Given: Table data
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Table name should be visible
      expect(screen.getByText('users')).toBeInTheDocument()
    })

    it('should display collection type label', () => {
      // Given: Table data
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Collection label should be visible
      expect(screen.getByText('NoSQL Collection')).toBeInTheDocument()
    })

    it('should display formatted row count', () => {
      // Given: Table with many rows
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Row count should be formatted with comma
      expect(screen.getByText('1,234')).toBeInTheDocument()
    })

    it('should display field count', () => {
      // Given: Table with schema
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Field count should be displayed
      expect(screen.getByText('Fields:')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
    })

    it('should display created date', () => {
      // Given: Table data
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Created date should be visible
      expect(screen.getByText('Created:')).toBeInTheDocument()
    })

    it('should display zero rows for empty table', () => {
      // Given: Empty table
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTableNoSchema}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Row count should be 0
      const rowsSection = screen.getByText('Rows:').parentElement
      expect(rowsSection).toHaveTextContent('0')
    })
  })

  describe('Schema Preview', () => {
    it('should display schema preview section', () => {
      // Given: Table with schema
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Schema preview heading should be visible
      expect(screen.getByText('Schema Preview')).toBeInTheDocument()
    })

    it('should display first three schema fields', () => {
      // Given: Table with multiple fields
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: First three fields should be visible
      expect(screen.getByText(/id: string/i)).toBeInTheDocument()
      expect(screen.getByText(/email: string/i)).toBeInTheDocument()
      expect(screen.getByText(/name: string/i)).toBeInTheDocument()
    })

    it('should show additional fields indicator', () => {
      // Given: Table with more than 3 fields
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Additional fields indicator should be visible
      expect(screen.getByText('+2 more fields')).toBeInTheDocument()
    })

    it('should display no schema message for table without schema', () => {
      // Given: Table without schema
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTableNoSchema}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: No schema message should be visible
      expect(screen.getByText('No schema defined')).toBeInTheDocument()
    })

    it('should display field types correctly', () => {
      // Given: Table with various field types
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Field types should be displayed
      const card = screen.getByTestId('table-card')
      expect(within(card).getAllByText(/string/i).length).toBeGreaterThan(0)
    })

    it('should not show additional fields indicator when 3 or fewer fields', () => {
      // Given: Table with exactly 3 fields
      const tableWith3Fields: Table = {
        ...mockTable,
        schema: {
          fields: {
            id: { type: 'string' },
            name: { type: 'string' },
            email: { type: 'string' },
          },
        },
      }

      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={tableWith3Fields}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Additional fields indicator should not be visible
      expect(screen.queryByText(/more fields/i)).not.toBeInTheDocument()
    })
  })

  describe('Action Buttons', () => {
    it('should display View Data button', () => {
      // Given: Table data
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: View Data button should be visible
      expect(screen.getByText('View Data')).toBeInTheDocument()
    })

    it('should display Actions button', () => {
      // Given: Table data
      // When: Component is rendered
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Actions button should be visible
      expect(screen.getByLabelText('Table actions')).toBeInTheDocument()
    })

    it('should call onViewData when View Data is clicked', async () => {
      // Given: Rendered card
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // When: User clicks View Data
      await user.click(screen.getByText('View Data'))

      // Then: onViewData should be called with table ID
      expect(mockOnViewData).toHaveBeenCalledWith('table-1')
    })
  })

  describe('Actions Menu', () => {
    it('should not show actions menu initially', () => {
      // Given: Card is rendered
      // When: Component loads
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Menu should not be visible
      expect(screen.queryByTestId('actions-menu')).not.toBeInTheDocument()
    })

    it('should show actions menu when Actions button is clicked', async () => {
      // Given: Card is rendered
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // When: User clicks Actions button
      await user.click(screen.getByLabelText('Table actions'))

      // Then: Menu should be visible
      expect(screen.getByTestId('actions-menu')).toBeInTheDocument()
    })

    it('should display Edit Schema menu item', async () => {
      // Given: Menu is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))

      // Then: Edit option should be visible
      expect(screen.getByText('Edit Schema')).toBeInTheDocument()
    })

    it('should display Export Data menu item', async () => {
      // Given: Menu is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))

      // Then: Export option should be visible
      expect(screen.getByText('Export Data')).toBeInTheDocument()
    })

    it('should display Delete Table menu item', async () => {
      // Given: Menu is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))

      // Then: Delete option should be visible
      expect(screen.getByText('Delete Table')).toBeInTheDocument()
    })

    it('should hide menu when Actions button is clicked again', async () => {
      // Given: Menu is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))
      expect(screen.getByTestId('actions-menu')).toBeInTheDocument()

      // When: User clicks Actions button again
      await user.click(screen.getByLabelText('Table actions'))

      // Then: Menu should be hidden
      expect(screen.queryByTestId('actions-menu')).not.toBeInTheDocument()
    })
  })

  describe('Edit Action', () => {
    it('should call onEdit when Edit Schema is clicked', async () => {
      // Given: Menu is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))

      // When: User clicks Edit Schema
      await user.click(screen.getByText('Edit Schema'))

      // Then: onEdit should be called with table object
      expect(mockOnEdit).toHaveBeenCalledWith(mockTable)
    })

    it('should pass complete table object to onEdit', async () => {
      // Given: Menu is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))

      // When: User clicks Edit Schema
      await user.click(screen.getByText('Edit Schema'))

      // Then: Complete table object should be passed
      expect(mockOnEdit).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'table-1',
          name: 'users',
          schema: expect.any(Object),
        })
      )
    })
  })

  describe('Export Action', () => {
    it('should call onExport when Export Data is clicked', async () => {
      // Given: Menu is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))

      // When: User clicks Export Data
      await user.click(screen.getByText('Export Data'))

      // Then: onExport should be called with table ID
      expect(mockOnExport).toHaveBeenCalledWith('table-1')
    })
  })

  describe('Delete Action', () => {
    it('should show confirmation dialog when Delete is clicked', async () => {
      // Given: Menu is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))

      // When: User clicks Delete Table
      await user.click(screen.getByText('Delete Table'))

      // Then: Confirmation dialog should be visible
      expect(screen.getByTestId('delete-dialog')).toBeInTheDocument()
    })

    it('should display table name in confirmation dialog', async () => {
      // Given: Menu is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))
      await user.click(screen.getByText('Delete Table'))

      // Then: Table name should be in confirmation message
      expect(screen.getByText(/Are you sure you want to delete table "users"/i)).toBeInTheDocument()
    })

    it('should display warning message in confirmation dialog', async () => {
      // Given: Delete dialog is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))
      await user.click(screen.getByText('Delete Table'))

      // Then: Warning message should be visible
      expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument()
    })

    it('should call onDelete when confirmed', async () => {
      // Given: Delete dialog is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))
      await user.click(screen.getByText('Delete Table'))

      // When: User confirms deletion
      const deleteButtons = screen.getAllByText('Delete')
      await user.click(deleteButtons[deleteButtons.length - 1])

      // Then: onDelete should be called with table ID
      expect(mockOnDelete).toHaveBeenCalledWith('table-1')
    })

    it('should not call onDelete when cancelled', async () => {
      // Given: Delete dialog is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))
      await user.click(screen.getByText('Delete Table'))

      // When: User cancels deletion
      await user.click(screen.getByText('Cancel'))

      // Then: onDelete should not be called
      expect(mockOnDelete).not.toHaveBeenCalled()
    })

    it('should close dialog after cancelling', async () => {
      // Given: Delete dialog is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))
      await user.click(screen.getByText('Delete Table'))

      // When: User cancels
      await user.click(screen.getByText('Cancel'))

      // Then: Dialog should be closed
      expect(screen.queryByTestId('delete-dialog')).not.toBeInTheDocument()
    })

    it('should close dialog after confirming deletion', async () => {
      // Given: Delete dialog is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))
      await user.click(screen.getByText('Delete Table'))

      // When: User confirms deletion
      const deleteButtons = screen.getAllByText('Delete')
      await user.click(deleteButtons[deleteButtons.length - 1])

      // Then: Dialog should be closed
      expect(screen.queryByTestId('delete-dialog')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have proper heading hierarchy', () => {
      // Given: Table data
      // When: Component is rendered
      const { container } = render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: Heading levels should be correct
      expect(container.querySelector('h3')).toHaveTextContent('users')
      expect(container.querySelector('h4')).toHaveTextContent('Schema Preview')
    })

    it('should have role="menu" for actions menu', async () => {
      // Given: Menu is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))

      // Then: Menu should have proper role
      expect(screen.getByRole('menu')).toBeInTheDocument()
    })

    it('should have role="menuitem" for menu options', async () => {
      // Given: Menu is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))

      // Then: Menu items should have proper role
      const menuItems = screen.getAllByRole('menuitem')
      expect(menuItems).toHaveLength(3)
    })

    it('should have role="dialog" for delete confirmation', async () => {
      // Given: Delete dialog is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))
      await user.click(screen.getByText('Delete Table'))

      // Then: Dialog should have proper role
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('should have aria-label for delete dialog', async () => {
      // Given: Delete dialog is open
      const user = userEvent.setup()
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )
      await user.click(screen.getByLabelText('Table actions'))
      await user.click(screen.getByText('Delete Table'))

      // Then: Dialog should have aria-label
      expect(screen.getByLabelText('Confirm Delete')).toBeInTheDocument()
    })

    it('should have clickable buttons', () => {
      // Given: Card is rendered
      // When: Component loads
      render(
        <EnhancedTableCard
          table={mockTable}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onExport={mockOnExport}
          onViewData={mockOnViewData}
        />
      )

      // Then: All buttons should be in the document
      expect(screen.getByText('View Data').closest('button')).toBeInTheDocument()
      expect(screen.getByLabelText('Table actions').closest('button')).toBeInTheDocument()
    })
  })
})
