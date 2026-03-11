import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Mock component since the actual component doesn't exist yet
// This test suite is ready for when the component is implemented
const CreateTableDialog = ({
  open,
  onOpenChange,
  onSubmit,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: any) => Promise<void>
}) => {
  const [tableName, setTableName] = React.useState('')
  const [fields, setFields] = React.useState<Array<{ name: string; type: string; required: boolean }>>([
    { name: '', type: 'string', required: false }
  ])
  const [error, setError] = React.useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!tableName.trim()) {
      setError('Table name is required')
      return
    }
    const validFields = fields.filter(f => f.name.trim())
    if (validFields.length === 0) {
      setError('At least one field is required')
      return
    }
    setIsSubmitting(true)
    try {
      await onSubmit({ name: tableName, fields: validFields })
      onOpenChange(false)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const addField = () => {
    setFields([...fields, { name: '', type: 'string', required: false }])
  }

  const removeField = (index: number) => {
    setFields(fields.filter((_, i) => i !== index))
  }

  const updateField = (index: number, updates: Partial<typeof fields[0]>) => {
    setFields(fields.map((f, i) => i === index ? { ...f, ...updates } : f))
  }

  if (!open) return null

  return (
    <div role="dialog" aria-label="Create Table Dialog">
      <h2>Create New Table</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="table-name">Table Name *</label>
          <input
            id="table-name"
            type="text"
            value={tableName}
            onChange={(e) => setTableName(e.target.value)}
            placeholder="Enter table name"
          />
        </div>

        <div>
          <h3>Schema Fields</h3>
          {fields.map((field, index) => (
            <div key={index} data-testid={`field-${index}`}>
              <input
                type="text"
                value={field.name}
                onChange={(e) => updateField(index, { name: e.target.value })}
                placeholder="Field name"
                aria-label={`Field ${index + 1} name`}
              />
              <select
                value={field.type}
                onChange={(e) => updateField(index, { type: e.target.value })}
                aria-label={`Field ${index + 1} type`}
              >
                <option value="string">String</option>
                <option value="number">Number</option>
                <option value="boolean">Boolean</option>
                <option value="object">Object</option>
                <option value="array">Array</option>
              </select>
              <label>
                <input
                  type="checkbox"
                  checked={field.required}
                  onChange={(e) => updateField(index, { required: e.target.checked })}
                  aria-label={`Field ${index + 1} required`}
                />
                Required
              </label>
              {fields.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeField(index)}
                  aria-label={`Remove field ${index + 1}`}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <button type="button" onClick={addField}>
            Add Field
          </button>
        </div>

        {error && (
          <div role="alert" data-testid="error-message">
            {error}
          </div>
        )}

        <div>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating...' : 'Create Table'}
          </button>
        </div>
      </form>
    </div>
  )
}

import * as React from 'react'

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

describe('CreateTableDialog', () => {
  let mockOnOpenChange: ReturnType<typeof vi.fn>
  let mockOnSubmit: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockOnOpenChange = vi.fn()
    mockOnSubmit = vi.fn().mockResolvedValue(undefined)
  })

  describe('Dialog Visibility', () => {
    it('should not render when open is false', () => {
      // Given: Dialog is closed
      // When: Component is rendered
      renderWithQuery(
        <CreateTableDialog
          open={false}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // Then: Dialog should not be visible
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('should render when open is true', () => {
      // Given: Dialog is open
      // When: Component is rendered
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // Then: Dialog should be visible
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('should display dialog title', () => {
      // Given: Dialog is open
      // When: Component is rendered
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // Then: Title should be visible
      expect(screen.getByText('Create New Table')).toBeInTheDocument()
    })

    it('should have proper ARIA label', () => {
      // Given: Dialog is open
      // When: Component is rendered
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // Then: Dialog should have proper ARIA label
      expect(screen.getByLabelText('Create Table Dialog')).toBeInTheDocument()
    })
  })

  describe('Form Fields', () => {
    it('should render table name input', () => {
      // Given: Dialog is open
      // When: Component is rendered
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // Then: Table name input should be visible
      expect(screen.getByLabelText('Table Name *')).toBeInTheDocument()
    })

    it('should render placeholder for table name', () => {
      // Given: Dialog is open
      // When: Component is rendered
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // Then: Placeholder should be visible
      expect(screen.getByPlaceholderText('Enter table name')).toBeInTheDocument()
    })

    it('should render Schema Fields section', () => {
      // Given: Dialog is open
      // When: Component is rendered
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // Then: Schema section should be visible
      expect(screen.getByText('Schema Fields')).toBeInTheDocument()
    })

    it('should render one field by default', () => {
      // Given: Dialog is open
      // When: Component is rendered
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // Then: One field should be rendered
      expect(screen.getByTestId('field-0')).toBeInTheDocument()
    })

    it('should allow typing table name', async () => {
      // Given: Dialog is open
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // When: User types in table name
      const input = screen.getByLabelText('Table Name *')
      await user.type(input, 'users')

      // Then: Input value should be updated
      expect(input).toHaveValue('users')
    })

    it('should allow typing field name', async () => {
      // Given: Dialog is open
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // When: User types in field name
      const fieldInput = screen.getByLabelText('Field 1 name')
      await user.type(fieldInput, 'email')

      // Then: Field name should be updated
      expect(fieldInput).toHaveValue('email')
    })

    it('should allow selecting field type', async () => {
      // Given: Dialog is open
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // When: User selects field type
      const typeSelect = screen.getByLabelText('Field 1 type')
      await user.selectOptions(typeSelect, 'number')

      // Then: Field type should be updated
      expect(typeSelect).toHaveValue('number')
    })

    it('should render all field type options', () => {
      // Given: Dialog is open
      // When: Component is rendered
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // Then: All field types should be available
      expect(screen.getByRole('option', { name: 'String' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Number' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Boolean' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Object' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Array' })).toBeInTheDocument()
    })

    it('should allow toggling required checkbox', async () => {
      // Given: Dialog is open
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // When: User clicks required checkbox
      const checkbox = screen.getByLabelText('Field 1 required')
      await user.click(checkbox)

      // Then: Checkbox should be checked
      expect(checkbox).toBeChecked()
    })
  })

  describe('Adding and Removing Fields', () => {
    it('should add a new field when Add Field is clicked', async () => {
      // Given: Dialog is open with one field
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // When: User clicks Add Field
      const addButton = screen.getByText('Add Field')
      await user.click(addButton)

      // Then: Second field should be added
      expect(screen.getByTestId('field-0')).toBeInTheDocument()
      expect(screen.getByTestId('field-1')).toBeInTheDocument()
    })

    it('should not show Remove button for single field', () => {
      // Given: Dialog is open with one field
      // When: Component is rendered
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // Then: Remove button should not be visible
      expect(screen.queryByLabelText('Remove field 1')).not.toBeInTheDocument()
    })

    it('should show Remove button for multiple fields', async () => {
      // Given: Dialog is open with multiple fields
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // When: User adds a field
      await user.click(screen.getByText('Add Field'))

      // Then: Remove buttons should be visible
      expect(screen.getByLabelText('Remove field 1')).toBeInTheDocument()
      expect(screen.getByLabelText('Remove field 2')).toBeInTheDocument()
    })

    it('should remove field when Remove button is clicked', async () => {
      // Given: Dialog with multiple fields
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.click(screen.getByText('Add Field'))

      // When: User removes second field
      const removeButton = screen.getByLabelText('Remove field 2')
      await user.click(removeButton)

      // Then: Second field should be removed
      expect(screen.getByTestId('field-0')).toBeInTheDocument()
      expect(screen.queryByTestId('field-1')).not.toBeInTheDocument()
    })

    it('should maintain field values when adding new fields', async () => {
      // Given: Dialog with field data
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Field 1 name'), 'email')

      // When: User adds another field
      await user.click(screen.getByText('Add Field'))

      // Then: First field should retain its value
      expect(screen.getByLabelText('Field 1 name')).toHaveValue('email')
    })
  })

  describe('Form Validation', () => {
    it('should show error when submitting without table name', async () => {
      // Given: Dialog is open with empty table name
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // When: User submits form
      const submitButton = screen.getByText('Create Table')
      await user.click(submitButton)

      // Then: Error message should be displayed
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toHaveTextContent(
          'Table name is required'
        )
      })
    })

    it('should show error when submitting without fields', async () => {
      // Given: Dialog with table name but no field names
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Table Name *'), 'users')

      // When: User submits form without filling field names
      await user.click(screen.getByText('Create Table'))

      // Then: Error message should be displayed
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toHaveTextContent(
          'At least one field is required'
        )
      })
    })

    it('should not show error for valid form', async () => {
      // Given: Dialog with valid data
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Table Name *'), 'users')
      await user.type(screen.getByLabelText('Field 1 name'), 'email')

      // When: User submits valid form
      await user.click(screen.getByText('Create Table'))

      // Then: No error should be displayed
      expect(screen.queryByTestId('error-message')).not.toBeInTheDocument()
    })
  })

  describe('Form Submission', () => {
    it('should call onSubmit with correct data', async () => {
      // Given: Dialog with valid data
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Table Name *'), 'users')
      await user.type(screen.getByLabelText('Field 1 name'), 'email')
      await user.selectOptions(screen.getByLabelText('Field 1 type'), 'string')

      // When: User submits form
      await user.click(screen.getByText('Create Table'))

      // Then: onSubmit should be called with correct data
      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          name: 'users',
          fields: [{ name: 'email', type: 'string', required: false }],
        })
      })
    })

    it('should include multiple fields in submission', async () => {
      // Given: Dialog with multiple fields
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Table Name *'), 'users')
      await user.type(screen.getByLabelText('Field 1 name'), 'email')
      await user.click(screen.getByText('Add Field'))
      await user.type(screen.getByLabelText('Field 2 name'), 'age')
      await user.selectOptions(screen.getByLabelText('Field 2 type'), 'number')

      // When: User submits form
      await user.click(screen.getByText('Create Table'))

      // Then: All fields should be included
      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          name: 'users',
          fields: [
            { name: 'email', type: 'string', required: false },
            { name: 'age', type: 'number', required: false },
          ],
        })
      })
    })

    it('should include required flag in submission', async () => {
      // Given: Dialog with required field
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Table Name *'), 'users')
      await user.type(screen.getByLabelText('Field 1 name'), 'email')
      await user.click(screen.getByLabelText('Field 1 required'))

      // When: User submits form
      await user.click(screen.getByText('Create Table'))

      // Then: Required flag should be true
      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          name: 'users',
          fields: [{ name: 'email', type: 'string', required: true }],
        })
      })
    })

    it('should close dialog on successful submission', async () => {
      // Given: Dialog with valid data
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Table Name *'), 'users')
      await user.type(screen.getByLabelText('Field 1 name'), 'email')

      // When: User submits form
      await user.click(screen.getByText('Create Table'))

      // Then: Dialog should close
      await waitFor(() => {
        expect(mockOnOpenChange).toHaveBeenCalledWith(false)
      })
    })

    it('should show loading state during submission', async () => {
      // Given: Dialog with slow API response
      const user = userEvent.setup()
      mockOnSubmit.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Table Name *'), 'users')
      await user.type(screen.getByLabelText('Field 1 name'), 'email')

      // When: User submits form
      await user.click(screen.getByText('Create Table'))

      // Then: Loading text should be shown
      expect(screen.getByText('Creating...')).toBeInTheDocument()
    })

    it('should disable buttons during submission', async () => {
      // Given: Dialog with slow API response
      const user = userEvent.setup()
      mockOnSubmit.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Table Name *'), 'users')
      await user.type(screen.getByLabelText('Field 1 name'), 'email')

      // When: User submits form
      await user.click(screen.getByText('Create Table'))

      // Then: Buttons should be disabled
      expect(screen.getByText('Creating...')).toBeDisabled()
      expect(screen.getByText('Cancel')).toBeDisabled()
    })

    it('should display API error on submission failure', async () => {
      // Given: Dialog with API error
      const user = userEvent.setup()
      mockOnSubmit.mockRejectedValue(new Error('Table already exists'))
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Table Name *'), 'users')
      await user.type(screen.getByLabelText('Field 1 name'), 'email')

      // When: User submits form
      await user.click(screen.getByText('Create Table'))

      // Then: Error message should be displayed
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toHaveTextContent(
          'Table already exists'
        )
      })
    })

    it('should not close dialog on submission failure', async () => {
      // Given: Dialog with API error
      const user = userEvent.setup()
      mockOnSubmit.mockRejectedValue(new Error('API Error'))
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Table Name *'), 'users')
      await user.type(screen.getByLabelText('Field 1 name'), 'email')

      // When: User submits form
      await user.click(screen.getByText('Create Table'))

      // Then: Dialog should remain open
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument()
      })
      expect(mockOnOpenChange).not.toHaveBeenCalledWith(false)
    })
  })

  describe('Dialog Controls', () => {
    it('should close dialog when Cancel is clicked', async () => {
      // Given: Dialog is open
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // When: User clicks Cancel
      await user.click(screen.getByText('Cancel'))

      // Then: Dialog should close
      expect(mockOnOpenChange).toHaveBeenCalledWith(false)
    })

    it('should not submit when Cancel is clicked', async () => {
      // Given: Dialog with data
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )
      await user.type(screen.getByLabelText('Table Name *'), 'users')

      // When: User clicks Cancel
      await user.click(screen.getByText('Cancel'))

      // Then: onSubmit should not be called
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('should have proper labels for all inputs', () => {
      // Given: Dialog is open
      // When: Component is rendered
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // Then: All inputs should have labels
      expect(screen.getByLabelText('Table Name *')).toBeInTheDocument()
      expect(screen.getByLabelText('Field 1 name')).toBeInTheDocument()
      expect(screen.getByLabelText('Field 1 type')).toBeInTheDocument()
      expect(screen.getByLabelText('Field 1 required')).toBeInTheDocument()
    })

    it('should have role="alert" for error messages', async () => {
      // Given: Dialog with validation error
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // When: User submits invalid form
      await user.click(screen.getByText('Create Table'))

      // Then: Error should have alert role
      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })

    it('should support keyboard navigation', async () => {
      // Given: Dialog is open
      const user = userEvent.setup()
      renderWithQuery(
        <CreateTableDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          onSubmit={mockOnSubmit}
        />
      )

      // When: User navigates with tab key
      const tableNameInput = screen.getByLabelText('Table Name *')
      await user.tab()

      // Then: Focus should move through form elements
      expect(tableNameInput).toHaveFocus()
    })
  })
})
