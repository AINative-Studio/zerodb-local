# Dashboard Tables Page - Implementation Checklist

This is a practical, step-by-step implementation guide for the enhanced Tables page. Follow this checklist sequentially to build the feature incrementally with working code at each step.

---

## Phase 1: Foundation (Days 1-2)

### Day 1: Type Definitions and API Client

#### 1.1 Update Type Definitions

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/types/index.ts`

- [ ] Add `TableSchema` interface
- [ ] Add `TableField` interface
- [ ] Add `TableIndex` interface
- [ ] Add `FieldType` enum (string, number, boolean, object, array, date, json)
- [ ] Add `IndexType` enum (btree, hash, gin)
- [ ] Add `TableStatus` enum (ready, syncing, error, creating)
- [ ] Enhance existing `Table` interface with new fields:
  - `description?: string`
  - `schema: TableSchema`
  - `indexes: TableIndex[]`
  - `size_bytes: number`
  - `status: TableStatus`
  - `last_modified_at: string`
- [ ] Add `TableRow` interface
- [ ] Add `TableQueryResult` interface

**Testing**: Run `npm run type-check` to ensure no TypeScript errors

#### 1.2 Extend API Client

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/services/api-client.ts`

Add these methods to the `ApiClient` class:

- [ ] `createTable(projectId, data)`
- [ ] `updateTableSchema(projectId, tableName, schema)`
- [ ] `deleteTable(projectId, tableName)`
- [ ] `queryTableRows(projectId, tableName, params)`
- [ ] `insertTableRow(projectId, tableName, row)`
- [ ] `updateTableRow(projectId, tableName, rowId, updates)`
- [ ] `deleteTableRows(projectId, tableName, rowIds)`
- [ ] `exportTableData(projectId, tableName, format, filters)`

**Testing**: Create a test file to verify API methods compile correctly

### Day 2: Custom Hooks

#### 2.1 Create Table Hooks

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/hooks/useTables.ts`

- [ ] `useTables(projectId)` - Query for tables list
- [ ] `useTable(projectId, tableName)` - Query for single table
- [ ] `useCreateTable(projectId)` - Mutation for creating table
- [ ] `useDeleteTable(projectId)` - Mutation for deleting table
- [ ] `useTableData(projectId, tableName, params)` - Query with pagination
- [ ] `useUpdateTableRow(projectId, tableName)` - Mutation for updating row
- [ ] `useDeleteTableRows(projectId, tableName)` - Mutation for deleting rows

**Testing**: Import hooks in a test component to verify they compile

#### 2.2 Create Utility Hooks

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/hooks/useDebounce.ts`

- [ ] Implement `useDebouncedValue(value, delay)` hook

**Testing**: Create a simple test component using the hook

---

## Phase 2: Component Structure (Days 3-5)

### Day 3: Component Types and Structure

#### 3.1 Create Component Types File

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/types.ts`

- [ ] Define `EnhancedTableCardProps`
- [ ] Define `CreateTableDialogProps`
- [ ] Define `SchemaBuilderProps`
- [ ] Define `FieldRowProps`
- [ ] Define `TableDataBrowserProps`
- [ ] Define `SearchFilterBarProps`
- [ ] Define `TableFilterType` enum
- [ ] Define `TableSortType` enum

#### 3.2 Create Component Files

Create empty component files with basic structure:

- [ ] `components/tables/EnhancedTableCard.tsx`
- [ ] `components/tables/SearchFilterBar.tsx`
- [ ] `components/tables/CreateTableDialog.tsx`
- [ ] `components/tables/SchemaBuilder.tsx`
- [ ] `components/tables/FieldRow.tsx`
- [ ] `components/tables/TableDataBrowser.tsx`

Each file should have:
```typescript
'use client'

import React from 'react'
import type { ComponentNameProps } from './types'

export function ComponentName(props: ComponentNameProps) {
  return <div>ComponentName placeholder</div>
}
```

**Testing**: Import all components in `page.tsx` to verify no import errors

### Day 4: SearchFilterBar Component

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/SearchFilterBar.tsx`

Implementation order:

- [ ] Add search input with icon
- [ ] Implement debounced onChange handler
- [ ] Add filter dropdown (All, Has Data, Empty, Recent)
- [ ] Add sort dropdown (Name, Created, Rows)
- [ ] Add clear button
- [ ] Style with Tailwind CSS
- [ ] Add responsive layout

**Testing**:
- [ ] Render in `page.tsx`
- [ ] Verify all dropdowns open
- [ ] Verify callbacks fire
- [ ] Test on mobile viewport

### Day 5: EnhancedTableCard Component

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/EnhancedTableCard.tsx`

Implementation order:

- [ ] Card layout with shadcn `Card` component
- [ ] Header with table name and status badge
- [ ] Content area with metadata (fields, rows, size, modified)
- [ ] Footer with action buttons
- [ ] Dropdown menu for actions (Edit, Delete, Export)
- [ ] Status badge with colors (green/blue/red/gray)
- [ ] Hover effects and transitions

**Components needed**:
```typescript
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '@/components/ui/dropdown-menu'
```

**Testing**:
- [ ] Render card with mock data
- [ ] Click all menu items
- [ ] Verify callbacks fire
- [ ] Check responsive design

---

## Phase 3: Table Creation (Days 6-9)

### Day 6: Basic CreateTableDialog Structure

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/CreateTableDialog.tsx`

- [ ] Dialog wrapper with trigger button
- [ ] Multi-step state management
- [ ] Step indicator (1/3, 2/3, 3/3)
- [ ] Navigation buttons (Back, Next, Create)
- [ ] Form data state
- [ ] Error state

**Components needed**:
```typescript
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
```

**Testing**:
- [ ] Open/close dialog
- [ ] Navigate between steps
- [ ] Cancel button resets state

### Day 7: Step 1 - Basic Information

**File**: Continue in `CreateTableDialog.tsx`

- [ ] Table name input with validation
- [ ] Description textarea
- [ ] Validation rules:
  - Name required, 3-50 chars, alphanumeric + underscores
  - Name uniqueness check (client-side against existing tables)
- [ ] Error display below inputs
- [ ] Next button enabled only when valid

**Testing**:
- [ ] Submit with empty name (should show error)
- [ ] Submit with invalid characters (should show error)
- [ ] Submit valid data (should advance to step 2)

### Day 8: Step 2 - Schema Builder

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/SchemaBuilder.tsx`

- [ ] Display list of fields
- [ ] Add field button
- [ ] Remove field button (disabled for last field)
- [ ] Default field: `{ name: 'id', type: 'string', required: true, unique: true }`

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/FieldRow.tsx`

- [ ] Field name input
- [ ] Type dropdown (string, number, boolean, object, array, date, json)
- [ ] Required checkbox
- [ ] Unique checkbox
- [ ] Remove button
- [ ] Validation:
  - Field name required
  - No duplicate field names
  - At least one field must be unique or named 'id'

**Testing**:
- [ ] Add 5 fields
- [ ] Remove fields
- [ ] Try duplicate field names (should show error)
- [ ] Try removing all fields (should prevent)

### Day 9: Step 3 - Review and Submit

**File**: Continue in `CreateTableDialog.tsx`

- [ ] Display summary of table configuration
- [ ] Show field count, required fields count
- [ ] Show indexes count (if indexes implemented)
- [ ] Create button triggers mutation
- [ ] Loading state during creation
- [ ] Success: close dialog, show toast, refresh tables
- [ ] Error: display error message, stay in dialog

**Testing**:
- [ ] Complete full flow with valid data
- [ ] Verify new table appears in list
- [ ] Test error handling (simulate API error)
- [ ] Verify dialog closes on success

---

## Phase 4: Data Browser (Days 10-14)

### Day 10: TableDataBrowser Modal Structure

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/TableDataBrowser.tsx`

- [ ] Dialog/modal wrapper (full-screen or large)
- [ ] Header with table name and stats
- [ ] Insert row button
- [ ] Export button with dropdown
- [ ] Close button
- [ ] State management:
  - `page`, `pageSize`
  - `sortColumn`, `sortDirection`
  - `filters`
  - `selectedRows`

**Testing**:
- [ ] Open browser from table card
- [ ] Verify header displays correct table info
- [ ] Close button works

### Day 11: DataGrid Component

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/DataGrid.tsx`

- [ ] Table element with semantic HTML
- [ ] Column headers from schema
- [ ] Sortable column headers (click to sort)
- [ ] Data rows from API
- [ ] Pagination controls (prev, next, page info)
- [ ] Empty state when no data
- [ ] Loading skeleton

**Components needed**:
```typescript
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
```

**Testing**:
- [ ] Display mock data (10 rows)
- [ ] Click column headers (verify sort callback)
- [ ] Navigate pages
- [ ] Test with empty data (show empty state)
- [ ] Test loading state

### Day 12: EditableCell Component

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/EditableCell.tsx`

- [ ] Display mode: show value
- [ ] Edit mode: show input (double-click to activate)
- [ ] Type-specific inputs:
  - String: text input
  - Number: number input
  - Boolean: checkbox
  - Date: date input
  - Object/JSON: textarea with validation
- [ ] Save on blur or Enter
- [ ] Cancel on Escape
- [ ] Optimistic update
- [ ] Error handling and rollback

**Testing**:
- [ ] Double-click cell to edit
- [ ] Change value and press Enter (should save)
- [ ] Change value and press Escape (should cancel)
- [ ] Edit and blur (should save)
- [ ] Test each data type

### Day 13: Row Selection and Bulk Actions

**File**: Continue in `TableDataBrowser.tsx` and `DataGrid.tsx`

- [ ] Checkbox column (first column)
- [ ] Select all checkbox in header
- [ ] Track selected rows in state (Set of IDs)
- [ ] Bulk actions bar (appears when rows selected)
- [ ] Delete selected button
- [ ] Confirmation dialog for bulk delete
- [ ] Clear selection after action

**Testing**:
- [ ] Select individual rows
- [ ] Select all rows
- [ ] Delete selected rows
- [ ] Verify selection cleared after delete

### Day 14: Insert Row Dialog

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/InsertRowDialog.tsx`

- [ ] Dialog with form fields based on schema
- [ ] Generate form inputs for each field
- [ ] Default values for fields
- [ ] Validation based on field constraints
- [ ] Submit button triggers insert mutation
- [ ] Success: close dialog, refresh data
- [ ] Error: display error message

**Testing**:
- [ ] Open insert dialog
- [ ] Fill in all fields
- [ ] Submit valid data (should add row)
- [ ] Submit invalid data (should show errors)
- [ ] Verify new row appears in grid

---

## Phase 5: Advanced Features (Days 15-17)

### Day 15: Export Functionality

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/ExportDialog.tsx`

- [ ] Export options: JSON or CSV
- [ ] Export all data or filtered data
- [ ] Export selected rows only (if applicable)
- [ ] Generate file blob
- [ ] Trigger download
- [ ] Loading state during export
- [ ] Error handling

**Implementation**:
```typescript
const handleExport = async (format: 'json' | 'csv') => {
  try {
    const blob = await apiClient.exportTableData(projectId, tableName, format, filters)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${tableName}.${format}`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    // Show error toast
  }
}
```

**Testing**:
- [ ] Export as JSON
- [ ] Export as CSV
- [ ] Open downloaded files
- [ ] Verify data correctness

### Day 16: Search and Filtering in Data Browser

**File**: Continue in `TableDataBrowser.tsx`

- [ ] Search input above grid
- [ ] Per-column filters (optional advanced feature)
- [ ] Filter state management
- [ ] Update query params with filters
- [ ] Clear filters button
- [ ] Apply filters to API query

**Testing**:
- [ ] Search for specific value
- [ ] Apply multiple filters
- [ ] Clear filters
- [ ] Verify URL updates with filter params

### Day 17: URL State Management

**File**: Continue in `TableDataBrowser.tsx`

- [ ] Use `useSearchParams` from Next.js
- [ ] Parse URL params on mount (page, sort, filters)
- [ ] Update URL when state changes
- [ ] Enable deep linking to specific views
- [ ] Enable browser back/forward navigation

**Implementation**:
```typescript
const searchParams = useSearchParams()
const router = useRouter()

const page = parseInt(searchParams.get('page') || '1')
const sortBy = searchParams.get('sort') || '_id'

const updateParams = (updates: Record<string, string>) => {
  const params = new URLSearchParams(searchParams)
  Object.entries(updates).forEach(([key, value]) => {
    if (value) params.set(key, value)
    else params.delete(key)
  })
  router.push(`?${params.toString()}`, { scroll: false })
}
```

**Testing**:
- [ ] Change page (URL updates)
- [ ] Sort column (URL updates)
- [ ] Copy URL and paste in new tab (state preserved)
- [ ] Use browser back button (state restored)

---

## Phase 6: Integration and Polish (Days 18-20)

### Day 18: Update Main Tables Page

**File**: `/Users/aideveloper/core/zerodb-local/dashboard/app/tables/page.tsx`

- [ ] Replace basic table cards with `EnhancedTableCard`
- [ ] Add `SearchFilterBar` above grid
- [ ] Implement search/filter/sort logic with `useMemo`
- [ ] Add `CreateTableDialog` trigger button in header
- [ ] Implement delete handler with confirmation
- [ ] Implement export handler
- [ ] Implement view data handler (opens `TableDataBrowser`)

**Testing**:
- [ ] Search for tables
- [ ] Filter tables (has data, empty, recent)
- [ ] Sort tables
- [ ] Create new table
- [ ] Delete table
- [ ] View table data

### Day 19: Error Handling and Loading States

**Files**: All components

- [ ] Add error boundaries to main page
- [ ] Implement toast notifications for actions
- [ ] Add loading skeletons for table cards
- [ ] Add loading spinner for data grid
- [ ] Handle network errors gracefully
- [ ] Display user-friendly error messages
- [ ] Implement retry logic for failed requests

**Components needed**:
```typescript
import { useToast } from '@/components/ui/use-toast'
import { Skeleton } from '@/components/ui/skeleton'
```

**Testing**:
- [ ] Simulate network error (disable internet)
- [ ] Simulate slow response (throttle network)
- [ ] Verify error messages display
- [ ] Verify retry works

### Day 20: Responsive Design and Mobile

**Files**: All components

- [ ] Test on mobile viewport (375px)
- [ ] Test on tablet viewport (768px)
- [ ] Adjust card grid for mobile (1 column)
- [ ] Make data browser scrollable on mobile
- [ ] Ensure touch targets are 44px minimum
- [ ] Test dialogs on small screens
- [ ] Adjust font sizes for readability

**Tailwind classes to review**:
- `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`
- `text-sm md:text-base`
- `p-4 md:p-6`
- `overflow-x-auto` for tables

**Testing**:
- [ ] Test all features on iPhone viewport
- [ ] Test all features on iPad viewport
- [ ] Verify scrolling works
- [ ] Verify buttons are tappable

---

## Phase 7: Testing (Days 21-23)

### Day 21: Unit Tests

Create test files:

- [ ] `EnhancedTableCard.test.tsx`
- [ ] `SearchFilterBar.test.tsx`
- [ ] `CreateTableDialog.test.tsx`
- [ ] `SchemaBuilder.test.tsx`
- [ ] `TableDataBrowser.test.tsx`

**Test patterns**:
```typescript
import { render, screen, userEvent } from '@testing-library/react'
import { EnhancedTableCard } from './EnhancedTableCard'

describe('EnhancedTableCard', () => {
  it('renders table information', () => {
    const table = mockTable()
    render(<EnhancedTableCard table={table} {...mockProps} />)
    expect(screen.getByText(table.name)).toBeInTheDocument()
  })

  it('calls onDelete when delete clicked', async () => {
    const onDelete = jest.fn()
    render(<EnhancedTableCard {...mockProps} onDelete={onDelete} />)

    await userEvent.click(screen.getByRole('button', { name: /menu/i }))
    await userEvent.click(screen.getByText('Delete'))

    expect(onDelete).toHaveBeenCalled()
  })
})
```

**Target coverage**: 80%

### Day 22: Integration Tests

Create integration test file:

- [ ] `tables-page.integration.test.tsx`

**Test scenarios**:
- [ ] User can create a table
- [ ] User can delete a table
- [ ] User can search tables
- [ ] User can filter and sort tables
- [ ] User can view table data
- [ ] User can edit a cell
- [ ] User can insert a row
- [ ] User can delete rows

### Day 23: E2E Tests with Playwright

Create E2E test file:

- [ ] `tests/e2e/tables.spec.ts`

**Test flows**:
```typescript
test('create table and add data', async ({ page }) => {
  await page.goto('/tables')
  await page.click('text=Test Project')
  await page.click('text=Create Table')

  // Fill form
  await page.fill('[name="name"]', 'products')
  await page.click('text=Next')

  // Add field
  await page.fill('[name="fieldName"]', 'name')
  await page.click('text=Create')

  // Verify created
  await expect(page.locator('text=products')).toBeVisible()

  // View data
  await page.click('text=View Data')

  // Insert row
  await page.click('text=Insert Row')
  await page.fill('[name="name"]', 'Product 1')
  await page.click('text=Save')

  // Verify row
  await expect(page.locator('text=Product 1')).toBeVisible()
})
```

---

## Phase 8: Documentation and Deployment (Days 24-25)

### Day 24: Documentation

- [ ] Add JSDoc comments to all components
- [ ] Create usage examples in Storybook (optional)
- [ ] Update user documentation
- [ ] Add screenshots to docs
- [ ] Create video walkthrough (optional)

### Day 25: Deployment

- [ ] Run full test suite
- [ ] Run Lighthouse audit
- [ ] Check accessibility with axe DevTools
- [ ] Build production bundle
- [ ] Test production build locally
- [ ] Deploy to staging environment
- [ ] Perform smoke tests on staging
- [ ] Get stakeholder approval
- [ ] Deploy to production
- [ ] Monitor error logs
- [ ] Collect user feedback

---

## Verification Checklist

Before marking complete, verify:

### Functionality
- [ ] Can create tables with custom schemas
- [ ] Can delete tables with confirmation
- [ ] Can view table data in grid
- [ ] Can edit cells inline
- [ ] Can insert new rows
- [ ] Can delete rows (single and bulk)
- [ ] Can search and filter tables
- [ ] Can sort tables by different fields
- [ ] Can export data as JSON/CSV
- [ ] Can navigate with keyboard
- [ ] All error states handled gracefully

### Performance
- [ ] Page load < 2 seconds
- [ ] Table list renders in < 500ms
- [ ] Data grid loads 50 rows in < 1 second
- [ ] Search is debounced and feels instant
- [ ] No unnecessary re-renders (use React DevTools Profiler)

### Accessibility
- [ ] All interactive elements keyboard accessible
- [ ] Focus indicators visible
- [ ] ARIA labels present
- [ ] Screen reader announces actions
- [ ] Color contrast meets WCAG AA
- [ ] Form errors announced
- [ ] No accessibility warnings in axe DevTools

### Responsive Design
- [ ] Works on mobile (375px)
- [ ] Works on tablet (768px)
- [ ] Works on desktop (1280px+)
- [ ] Touch targets minimum 44px
- [ ] No horizontal scrolling on mobile
- [ ] Readable text sizes

### Browser Compatibility
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

### Code Quality
- [ ] No TypeScript errors
- [ ] No ESLint warnings
- [ ] All tests passing
- [ ] Coverage >= 80%
- [ ] No console errors or warnings
- [ ] Code reviewed by peer

---

## Success Criteria

The implementation is complete when:

1. All checklist items are marked complete
2. All tests are passing (unit, integration, E2E)
3. Accessibility audit passes
4. Performance metrics meet targets
5. User testing completed with positive feedback
6. Deployed to production without critical issues

---

## Rollback Plan

If critical issues arise after deployment:

1. Revert to previous version via Git
2. Communicate issue to users
3. Fix issues in development
4. Re-test thoroughly
5. Re-deploy with fixes

**Rollback command**:
```bash
git revert [commit-hash]
git push origin main
```

---

## Support and Maintenance

After deployment:

- Monitor error tracking (Sentry or similar)
- Review user feedback weekly
- Address bugs within 48 hours
- Plan enhancements based on usage data

---

**Document Version**: 1.0
**Last Updated**: 2026-03-07
**Estimated Duration**: 25 working days (5 weeks)
**Priority**: High
