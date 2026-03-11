# Dashboard Tables Page Architecture

## Executive Summary

This document defines the enhanced architecture for the ZeroDB Local Dashboard Tables page, transforming it from a basic table listing view into a comprehensive NoSQL table management interface with full CRUD capabilities, schema management, and data browsing features.

### Key Enhancements
- Create tables with custom schemas and indexes
- Browse and edit table data inline
- Advanced search and filtering
- Export capabilities (JSON/CSV)
- Real-time status indicators
- Responsive multi-step dialogs

### Technology Stack
- Next.js 14 (App Router)
- React Query for server state
- TypeScript for type safety
- Tailwind CSS + shadcn/ui components
- date-fns for date formatting

---

## 1. Component Hierarchy

```
TablesPage (page.tsx)
├── Header Section
│   ├── Title + Description
│   └── CreateTableDialog (trigger button)
├── ProjectSelector (existing)
│   └── Button[] (project chips)
├── SearchFilterBar
│   ├── SearchInput
│   ├── FilterDropdown
│   └── SortDropdown
└── TablesGrid
    ├── EmptyState (when no tables)
    └── EnhancedTableCard[] (table list)
        ├── CardHeader (name, status, actions menu)
        ├── CardContent (stats, schema preview)
        └── CardFooter (action buttons)

CreateTableDialog
├── DialogTrigger (+ Create Table button)
└── DialogContent (multi-step form)
    ├── Step 1: Basic Info (name, description)
    ├── Step 2: Schema Builder
    │   └── FieldRow[] (name, type, constraints)
    ├── Step 3: Index Configuration
    │   └── IndexRow[] (fields, index type)
    └── DialogFooter (Back, Next, Create)

TableDataBrowser (new modal/page)
├── BrowserHeader
│   ├── Table name + stats
│   ├── InsertRowButton
│   └── ExportButton
├── DataGrid
│   ├── ColumnHeaders[] (sortable)
│   ├── DataRow[]
│   │   ├── Cell[] (editable)
│   │   └── RowActions (edit, delete)
│   └── Pagination
└── SearchFilterPanel
    ├── ColumnSearchInputs
    └── FilterBuilder
```

---

## 2. Data Models and TypeScript Interfaces

### Enhanced Table Type

```typescript
// Extend existing Table type in types/index.ts
export interface Table {
  id: string
  project_id: string
  name: string
  description?: string
  schema: TableSchema
  indexes: TableIndex[]
  row_count: number
  size_bytes: number
  status: TableStatus
  created_at: string
  updated_at: string
  last_modified_at: string
}

export interface TableSchema {
  fields: TableField[]
  version: number
}

export interface TableField {
  name: string
  type: FieldType
  required: boolean
  unique: boolean
  default?: any
  description?: string
}

export enum FieldType {
  STRING = 'string',
  NUMBER = 'number',
  BOOLEAN = 'boolean',
  OBJECT = 'object',
  ARRAY = 'array',
  DATE = 'date',
  JSON = 'json'
}

export interface TableIndex {
  name: string
  fields: string[]
  type: IndexType
  unique: boolean
}

export enum IndexType {
  BTREE = 'btree',
  HASH = 'hash',
  GIN = 'gin'
}

export enum TableStatus {
  READY = 'ready',
  SYNCING = 'syncing',
  ERROR = 'error',
  CREATING = 'creating'
}

export interface TableRow {
  _id: string
  [key: string]: any
}

export interface TableQueryResult {
  rows: TableRow[]
  total: number
  page: number
  page_size: number
}
```

### Component Props Interfaces

```typescript
// components/tables/types.ts

export interface EnhancedTableCardProps {
  table: Table
  projectId: string
  onEdit: (table: Table) => void
  onDelete: (tableId: string) => void
  onViewData: (table: Table) => void
  onExport: (table: Table, format: 'json' | 'csv') => void
}

export interface CreateTableDialogProps {
  projectId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (table: Table) => void
}

export interface SchemaBuilderProps {
  fields: TableField[]
  onChange: (fields: TableField[]) => void
  errors?: Record<string, string>
}

export interface TableDataBrowserProps {
  table: Table
  projectId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export interface SearchFilterBarProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  filterBy: TableFilterType
  onFilterChange: (filter: TableFilterType) => void
  sortBy: TableSortType
  onSortChange: (sort: TableSortType) => void
}

export enum TableFilterType {
  ALL = 'all',
  HAS_DATA = 'has_data',
  EMPTY = 'empty',
  RECENT = 'recent'
}

export enum TableSortType {
  NAME_ASC = 'name_asc',
  NAME_DESC = 'name_desc',
  CREATED_DESC = 'created_desc',
  CREATED_ASC = 'created_asc',
  ROWS_DESC = 'rows_desc',
  ROWS_ASC = 'rows_asc'
}
```

---

## 3. Component Specifications

### 3.1 EnhancedTableCard Component

**Location**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/EnhancedTableCard.tsx`

**Purpose**: Display table metadata with enhanced information and action menu.

**Features**:
- Status indicator badge (ready, syncing, error)
- Schema preview (field count, types summary)
- Size and last modified information
- Dropdown actions menu (Edit, Delete, Export, View Data)
- Hover effects and animations

**State Management**:
- Local state for dropdown menu open/close
- No internal mutations - all actions via callbacks

**Visual Design**:
```
┌─────────────────────────────────────┐
│ [Status] Table Name          [Menu] │
│ NoSQL collection                    │
├─────────────────────────────────────┤
│ Fields: 5 (3 required)              │
│ Rows: 1,234                         │
│ Size: 2.3 MB                        │
│ Modified: 2 hours ago               │
├─────────────────────────────────────┤
│ [View Data] [Export ▼]              │
└─────────────────────────────────────┘
```

**Implementation Notes**:
- Use `Card`, `CardHeader`, `CardContent`, `CardFooter` from shadcn/ui
- Status badge colors: green (ready), blue (syncing), red (error), gray (creating)
- Dropdown menu with `DropdownMenu` component
- Export button with submenu for JSON/CSV options

---

### 3.2 CreateTableDialog Component

**Location**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/CreateTableDialog.tsx`

**Purpose**: Multi-step modal for creating new tables with schema definition.

**Steps**:
1. Basic Information (name, description)
2. Schema Builder (fields with types and constraints)
3. Index Configuration (optional indexes)
4. Review and Create

**State Management**:
```typescript
const [currentStep, setCurrentStep] = useState(1)
const [formData, setFormData] = useState<CreateTableFormData>({
  name: '',
  description: '',
  fields: [
    { name: 'id', type: FieldType.STRING, required: true, unique: true }
  ],
  indexes: []
})
const [errors, setErrors] = useState<Record<string, string>>({})
```

**Validation Rules**:
- Table name: Required, 3-50 chars, alphanumeric + underscores
- At least one field required
- Field names must be unique
- At least one field must be `id` or have unique constraint

**API Integration**:
```typescript
const createTableMutation = useMutation({
  mutationFn: (data: CreateTableFormData) =>
    apiClient.createTable(projectId, data),
  onSuccess: (table) => {
    queryClient.invalidateQueries(['tables', projectId])
    onSuccess(table)
    onOpenChange(false)
  },
  onError: (error) => {
    setErrors({ submit: error.message })
  }
})
```

**Visual Flow**:
```
Step 1: Basic Info          Step 2: Schema Builder
┌──────────────────┐       ┌──────────────────────────┐
│ Table Name*      │       │ Field Name | Type | Opts │
│ [_________]      │  →    │ id         | str  | [✓✓] │
│                  │       │ name       | str  | [✓ ] │
│ Description      │       │ age        | num  | [ ✓] │
│ [_________]      │       │ + Add Field              │
└──────────────────┘       └──────────────────────────┘
     [Next >]                   [< Back] [Next >]

Step 3: Indexes             Step 4: Review
┌──────────────────────────┐  ┌──────────────────┐
│ Index Name | Fields      │  │ Summary:         │
│ idx_name   | name        │  │ - 4 fields       │
│ + Add Index             │  │ - 1 index        │
└──────────────────────────┘  │ [Create Table]   │
     [< Back] [Review >]       └──────────────────┘
```

---

### 3.3 SchemaBuilder Component

**Location**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/SchemaBuilder.tsx`

**Purpose**: Interactive field editor for table schema definition.

**Features**:
- Add/remove fields dynamically
- Field type selector (dropdown)
- Constraint checkboxes (required, unique)
- Default value input (type-specific)
- Inline validation feedback
- Drag-to-reorder fields (future enhancement)

**Field Row Structure**:
```typescript
interface FieldRowProps {
  field: TableField
  index: number
  onChange: (index: number, field: TableField) => void
  onRemove: (index: number) => void
  canRemove: boolean
  error?: string
}
```

**Visual Design**:
```
┌────────────────────────────────────────────────────┐
│ Field Name    Type        Required  Unique  Actions│
├────────────────────────────────────────────────────┤
│ [id_______]  [String ▼]    [✓]      [✓]     [×]   │
│ [name_____]  [String ▼]    [✓]      [ ]     [×]   │
│ [age______]  [Number ▼]    [ ]      [ ]     [×]   │
│ [metadata_]  [JSON ▼]      [ ]      [ ]     [×]   │
├────────────────────────────────────────────────────┤
│              [+ Add Field]                         │
└────────────────────────────────────────────────────┘
```

**Type-Specific Inputs**:
- STRING: Max length option
- NUMBER: Min/max range options
- DATE: Format selector
- ARRAY: Item type selector
- OBJECT/JSON: Schema validator (future)

---

### 3.4 TableDataBrowser Component

**Location**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/TableDataBrowser.tsx`

**Purpose**: Full-featured data grid for browsing and editing table rows.

**Features**:
- Paginated data grid
- Sortable columns
- Search per column
- Inline editing (double-click cell)
- Row selection
- Bulk actions (delete selected)
- Export visible/all data

**State Management**:
```typescript
const [page, setPage] = useState(1)
const [pageSize, setPageSize] = useState(50)
const [sortColumn, setSortColumn] = useState<string>('_id')
const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
const [filters, setFilters] = useState<Record<string, any>>({})
const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set())
const [editingCell, setEditingCell] = useState<{row: string, col: string} | null>(null)
```

**API Integration**:
```typescript
// Query with pagination and filters
const { data, isLoading } = useQuery({
  queryKey: ['table-data', projectId, table.id, page, pageSize, sortColumn, sortDirection, filters],
  queryFn: () => apiClient.queryTable(projectId, table.name, {
    page,
    page_size: pageSize,
    sort_by: sortColumn,
    sort_direction: sortDirection,
    filters
  })
})

// Update mutation
const updateRowMutation = useMutation({
  mutationFn: ({ rowId, field, value }: UpdateRowParams) =>
    apiClient.updateTableRow(projectId, table.name, rowId, { [field]: value }),
  onSuccess: () => {
    queryClient.invalidateQueries(['table-data', projectId, table.id])
  }
})

// Delete mutation
const deleteRowsMutation = useMutation({
  mutationFn: (rowIds: string[]) =>
    apiClient.deleteTableRows(projectId, table.name, rowIds),
  onSuccess: () => {
    queryClient.invalidateQueries(['table-data', projectId, table.id])
    setSelectedRows(new Set())
  }
})
```

**Visual Design**:
```
┌───────────────────────────────────────────────────────┐
│ users Table - 1,234 rows          [+ Insert] [Export]│
├───────────────────────────────────────────────────────┤
│ [×] Search: [________]  Filter: [All ▼]  Clear       │
├─┬──────────┬──────────────┬─────────┬────────────────┤
│☐│ id ▲     │ name ▼       │ age     │ created_at     │
├─┼──────────┼──────────────┼─────────┼────────────────┤
│☐│ u_001    │ Alice Smith  │ 28      │ 2024-01-15     │
│☐│ u_002    │ Bob Jones    │ 34      │ 2024-01-16     │
│☐│ u_003    │ Carol White  │ 45      │ 2024-01-17     │
├─┴──────────┴──────────────┴─────────┴────────────────┤
│ Selected: 0   [Delete Selected]    Page 1 of 25 › » │
└───────────────────────────────────────────────────────┘
```

**Cell Editing Behavior**:
- Double-click to edit
- Type-appropriate input (text, number, date picker, checkbox)
- Auto-save on blur or Enter key
- Escape to cancel
- Visual feedback (loading spinner, success checkmark, error highlight)

---

### 3.5 SearchFilterBar Component

**Location**: `/Users/aideveloper/core/zerodb-local/dashboard/components/tables/SearchFilterBar.tsx`

**Purpose**: Provide search and filtering controls for table list.

**Features**:
- Real-time search (debounced 300ms)
- Filter by table state (all, has data, empty, recent)
- Sort options (name, created date, row count)
- Clear all button

**State Management**:
- Controlled inputs via props
- Local debounce hook for search

**Visual Design**:
```
┌──────────────────────────────────────────────────────┐
│ [🔍 Search tables...]  Filter: [All ▼]  Sort: [Name ▼] │
└──────────────────────────────────────────────────────┘
```

**Filter Options**:
- All: Show all tables
- Has Data: row_count > 0
- Empty: row_count === 0
- Recent: created_at within last 7 days

**Sort Options**:
- Name (A-Z)
- Name (Z-A)
- Created (Newest)
- Created (Oldest)
- Rows (Most)
- Rows (Least)

---

## 4. API Integration Patterns

### Required API Endpoints

Add these methods to `/Users/aideveloper/core/zerodb-local/dashboard/services/api-client.ts`:

```typescript
class ApiClient {
  // ... existing methods ...

  // Tables - Enhanced
  async createTable(
    projectId: string,
    data: {
      name: string
      description?: string
      schema: TableSchema
      indexes?: TableIndex[]
    }
  ): Promise<Table> {
    const response = await this.client.post<Table>(
      `/v1/projects/${projectId}/database/tables`,
      data
    )
    return response.data
  }

  async updateTableSchema(
    projectId: string,
    tableName: string,
    schema: TableSchema
  ): Promise<Table> {
    const response = await this.client.patch<Table>(
      `/v1/projects/${projectId}/database/tables/${tableName}/schema`,
      { schema }
    )
    return response.data
  }

  async deleteTable(projectId: string, tableName: string): Promise<void> {
    await this.client.delete(
      `/v1/projects/${projectId}/database/tables/${tableName}`
    )
  }

  async queryTableRows(
    projectId: string,
    tableName: string,
    params: {
      page?: number
      page_size?: number
      sort_by?: string
      sort_direction?: 'asc' | 'desc'
      filters?: Record<string, any>
    }
  ): Promise<TableQueryResult> {
    const response = await this.client.post<TableQueryResult>(
      `/v1/projects/${projectId}/database/tables/${tableName}/query`,
      params
    )
    return response.data
  }

  async insertTableRow(
    projectId: string,
    tableName: string,
    row: Record<string, any>
  ): Promise<TableRow> {
    const response = await this.client.post<TableRow>(
      `/v1/projects/${projectId}/database/tables/${tableName}/rows`,
      row
    )
    return response.data
  }

  async updateTableRow(
    projectId: string,
    tableName: string,
    rowId: string,
    updates: Record<string, any>
  ): Promise<TableRow> {
    const response = await this.client.patch<TableRow>(
      `/v1/projects/${projectId}/database/tables/${tableName}/rows/${rowId}`,
      updates
    )
    return response.data
  }

  async deleteTableRows(
    projectId: string,
    tableName: string,
    rowIds: string[]
  ): Promise<{ deleted: number }> {
    const response = await this.client.post<{ deleted: number }>(
      `/v1/projects/${projectId}/database/tables/${tableName}/rows/delete`,
      { row_ids: rowIds }
    )
    return response.data
  }

  async exportTableData(
    projectId: string,
    tableName: string,
    format: 'json' | 'csv',
    filters?: Record<string, any>
  ): Promise<Blob> {
    const response = await this.client.post(
      `/v1/projects/${projectId}/database/tables/${tableName}/export`,
      { format, filters },
      { responseType: 'blob' }
    )
    return response.data
  }
}
```

### React Query Hooks

Create `/Users/aideveloper/core/zerodb-local/dashboard/hooks/useTables.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import type { Table, TableSchema, TableQueryResult } from '@/types'

export function useTables(projectId: string | undefined) {
  return useQuery({
    queryKey: ['tables', projectId],
    queryFn: () => projectId ? apiClient.listTables(projectId) : Promise.resolve([]),
    enabled: !!projectId
  })
}

export function useTable(projectId: string, tableName: string) {
  return useQuery({
    queryKey: ['table', projectId, tableName],
    queryFn: () => apiClient.getTable(projectId, tableName),
    enabled: !!projectId && !!tableName
  })
}

export function useCreateTable(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { name: string; description?: string; schema: TableSchema }) =>
      apiClient.createTable(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['tables', projectId])
    }
  })
}

export function useDeleteTable(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (tableName: string) => apiClient.deleteTable(projectId, tableName),
    onSuccess: () => {
      queryClient.invalidateQueries(['tables', projectId])
    }
  })
}

export function useTableData(
  projectId: string,
  tableName: string,
  params: {
    page: number
    pageSize: number
    sortBy?: string
    sortDirection?: 'asc' | 'desc'
    filters?: Record<string, any>
  }
) {
  return useQuery({
    queryKey: ['table-data', projectId, tableName, params],
    queryFn: () => apiClient.queryTableRows(projectId, tableName, {
      page: params.page,
      page_size: params.pageSize,
      sort_by: params.sortBy,
      sort_direction: params.sortDirection,
      filters: params.filters
    }),
    enabled: !!projectId && !!tableName,
    keepPreviousData: true
  })
}

export function useUpdateTableRow(projectId: string, tableName: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ rowId, updates }: { rowId: string; updates: Record<string, any> }) =>
      apiClient.updateTableRow(projectId, tableName, rowId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries(['table-data', projectId, tableName])
    }
  })
}

export function useDeleteTableRows(projectId: string, tableName: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (rowIds: string[]) => apiClient.deleteTableRows(projectId, tableName, rowIds),
    onSuccess: () => {
      queryClient.invalidateQueries(['table-data', projectId, tableName])
    }
  })
}
```

---

## 5. State Management Strategy

### Page-Level State (TablesPage)

**Local State**:
```typescript
const [selectedProject, setSelectedProject] = useState<string>()
const [searchQuery, setSearchQuery] = useState('')
const [filterBy, setFilterBy] = useState<TableFilterType>(TableFilterType.ALL)
const [sortBy, setSortBy] = useState<TableSortType>(TableSortType.NAME_ASC)
const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
const [viewingTable, setViewingTable] = useState<Table | null>(null)
```

**Derived State**:
```typescript
const filteredTables = useMemo(() => {
  if (!tables) return []

  let result = [...tables]

  // Apply search
  if (searchQuery) {
    result = result.filter(t =>
      t.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }

  // Apply filter
  switch (filterBy) {
    case TableFilterType.HAS_DATA:
      result = result.filter(t => t.row_count > 0)
      break
    case TableFilterType.EMPTY:
      result = result.filter(t => t.row_count === 0)
      break
    case TableFilterType.RECENT:
      const sevenDaysAgo = new Date()
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
      result = result.filter(t => new Date(t.created_at) > sevenDaysAgo)
      break
  }

  // Apply sort
  switch (sortBy) {
    case TableSortType.NAME_ASC:
      result.sort((a, b) => a.name.localeCompare(b.name))
      break
    case TableSortType.NAME_DESC:
      result.sort((a, b) => b.name.localeCompare(a.name))
      break
    case TableSortType.CREATED_DESC:
      result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      break
    case TableSortType.CREATED_ASC:
      result.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      break
    case TableSortType.ROWS_DESC:
      result.sort((a, b) => b.row_count - a.row_count)
      break
    case TableSortType.ROWS_ASC:
      result.sort((a, b) => a.row_count - b.row_count)
      break
  }

  return result
}, [tables, searchQuery, filterBy, sortBy])
```

### Dialog State Management

**CreateTableDialog**:
- Internal state for multi-step form
- Validation errors stored in local state
- Reset on close or successful creation

**TableDataBrowser**:
- URL search params for pagination, sorting, filters
- Enables deep linking to specific table views
- Persists state across browser back/forward

```typescript
// In TableDataBrowser
const searchParams = useSearchParams()
const router = useRouter()

const page = parseInt(searchParams.get('page') || '1')
const sortBy = searchParams.get('sort') || '_id'
const sortDir = (searchParams.get('dir') || 'asc') as 'asc' | 'desc'

const updateParams = (updates: Record<string, string>) => {
  const params = new URLSearchParams(searchParams)
  Object.entries(updates).forEach(([key, value]) => {
    if (value) params.set(key, value)
    else params.delete(key)
  })
  router.push(`?${params.toString()}`)
}
```

### Optimistic Updates

For better UX, implement optimistic updates for row edits:

```typescript
const updateRowMutation = useMutation({
  mutationFn: ({ rowId, field, value }) =>
    apiClient.updateTableRow(projectId, tableName, rowId, { [field]: value }),
  onMutate: async ({ rowId, field, value }) => {
    // Cancel outgoing queries
    await queryClient.cancelQueries(['table-data', projectId, tableName])

    // Snapshot previous value
    const previous = queryClient.getQueryData(['table-data', projectId, tableName])

    // Optimistically update
    queryClient.setQueryData(['table-data', projectId, tableName], (old: any) => {
      if (!old) return old
      return {
        ...old,
        rows: old.rows.map((row: TableRow) =>
          row._id === rowId ? { ...row, [field]: value } : row
        )
      }
    })

    return { previous }
  },
  onError: (err, variables, context) => {
    // Rollback on error
    if (context?.previous) {
      queryClient.setQueryData(['table-data', projectId, tableName], context.previous)
    }
  },
  onSettled: () => {
    // Refetch to ensure consistency
    queryClient.invalidateQueries(['table-data', projectId, tableName])
  }
})
```

---

## 6. Error Handling Patterns

### API Error Handling

```typescript
// In api-client.ts, enhance error interceptor
this.client.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response) {
      const apiError = error.response.data

      // Map API errors to user-friendly messages
      const errorMessages: Record<number, string> = {
        400: 'Invalid request. Please check your input.',
        401: 'Authentication required.',
        403: 'You do not have permission to perform this action.',
        404: 'The requested resource was not found.',
        409: 'A table with this name already exists.',
        500: 'Server error. Please try again later.'
      }

      const message = apiError.detail || errorMessages[error.response.status] || 'Request failed'
      throw new Error(message)
    } else if (error.request) {
      throw new Error('Unable to reach the server. Check your connection.')
    } else {
      throw new Error(error.message || 'Request failed')
    }
  }
)
```

### Component-Level Error Display

Use toast notifications for non-blocking errors:

```typescript
import { useToast } from '@/components/ui/use-toast'

const { toast } = useToast()

const deleteMutation = useMutation({
  mutationFn: (tableName: string) => apiClient.deleteTable(projectId, tableName),
  onSuccess: () => {
    toast({
      title: 'Table deleted',
      description: 'The table has been successfully deleted.'
    })
  },
  onError: (error: Error) => {
    toast({
      variant: 'destructive',
      title: 'Delete failed',
      description: error.message
    })
  }
})
```

Use inline errors for form validation:

```typescript
// In CreateTableDialog
const [errors, setErrors] = useState<Record<string, string>>({})

const validateForm = (): boolean => {
  const newErrors: Record<string, string> = {}

  if (!formData.name.trim()) {
    newErrors.name = 'Table name is required'
  } else if (!/^[a-zA-Z0-9_]+$/.test(formData.name)) {
    newErrors.name = 'Table name can only contain letters, numbers, and underscores'
  }

  if (formData.fields.length === 0) {
    newErrors.fields = 'At least one field is required'
  }

  const fieldNames = formData.fields.map(f => f.name)
  const duplicates = fieldNames.filter((name, idx) => fieldNames.indexOf(name) !== idx)
  if (duplicates.length > 0) {
    newErrors.fields = `Duplicate field names: ${duplicates.join(', ')}`
  }

  setErrors(newErrors)
  return Object.keys(newErrors).length === 0
}
```

### Loading States

Show skeleton loaders during initial load:

```typescript
// In TablesPage
{isLoading ? (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    {[1, 2, 3].map((i) => (
      <Card key={i}>
        <CardHeader>
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    ))}
  </div>
) : (
  // ... render tables
)}
```

---

## 7. Performance Optimizations

### Pagination and Virtual Scrolling

For large datasets in TableDataBrowser:
- Server-side pagination (50 rows per page default)
- Consider virtual scrolling for 100+ columns
- Lazy load dropdown options in filters

### Debounced Search

```typescript
import { useDebouncedValue } from '@/hooks/useDebounce'

// In SearchFilterBar
const [searchInput, setSearchInput] = useState('')
const debouncedSearch = useDebouncedValue(searchInput, 300)

useEffect(() => {
  onSearchChange(debouncedSearch)
}, [debouncedSearch, onSearchChange])
```

### Query Caching

```typescript
// In React Query setup
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
      retry: 1
    }
  }
})
```

### Code Splitting

```typescript
// Lazy load heavy components
const TableDataBrowser = dynamic(
  () => import('@/components/tables/TableDataBrowser'),
  { loading: () => <LoadingSpinner /> }
)
```

---

## 8. Accessibility Considerations

### Keyboard Navigation

- Dialog: Escape to close, Tab to navigate
- Table cards: Enter to view data, Menu key for actions
- Data grid: Arrow keys to navigate cells, Enter to edit
- Form inputs: Clear labels, error announcements

### ARIA Labels

```typescript
<Button
  aria-label="Create new table"
  onClick={() => setIsCreateDialogOpen(true)}
>
  <Plus className="h-4 w-4 mr-2" />
  Create Table
</Button>

<Table aria-label="Table data grid" aria-describedby="table-description">
  <caption id="table-description">
    Displaying {rows.length} of {total} rows
  </caption>
  {/* ... */}
</Table>
```

### Screen Reader Support

- Announce loading states
- Announce success/error actions
- Provide descriptive button labels
- Use semantic HTML (table, form, dialog)

---

## 9. Testing Strategy

### Unit Tests

Test individual components in isolation:

```typescript
// EnhancedTableCard.test.tsx
describe('EnhancedTableCard', () => {
  it('displays table information correctly', () => {
    const table = mockTable({ name: 'users', row_count: 100 })
    render(<EnhancedTableCard table={table} {...mockProps} />)

    expect(screen.getByText('users')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument()
  })

  it('calls onDelete when delete action clicked', async () => {
    const onDelete = jest.fn()
    render(<EnhancedTableCard {...mockProps} onDelete={onDelete} />)

    await userEvent.click(screen.getByRole('button', { name: /menu/i }))
    await userEvent.click(screen.getByText('Delete'))

    expect(onDelete).toHaveBeenCalledWith(mockProps.table.id)
  })
})
```

### Integration Tests

Test component interactions and data flow:

```typescript
// CreateTableDialog.test.tsx
describe('CreateTableDialog', () => {
  it('completes multi-step form and creates table', async () => {
    const onSuccess = jest.fn()
    render(<CreateTableDialog open onSuccess={onSuccess} {...mockProps} />)

    // Step 1: Basic info
    await userEvent.type(screen.getByLabelText('Table Name'), 'products')
    await userEvent.click(screen.getByText('Next'))

    // Step 2: Add fields
    await userEvent.type(screen.getByLabelText('Field Name'), 'name')
    await userEvent.selectOptions(screen.getByLabelText('Type'), 'string')
    await userEvent.click(screen.getByText('Add Field'))
    await userEvent.click(screen.getByText('Next'))

    // Step 3: Review and create
    await userEvent.click(screen.getByText('Create Table'))

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(expect.objectContaining({
        name: 'products'
      }))
    })
  })
})
```

### E2E Tests

Test full user workflows with Playwright:

```typescript
// tables.spec.ts
test('user can create table and add data', async ({ page }) => {
  await page.goto('/tables')

  // Select project
  await page.click('text=Test Project')

  // Create table
  await page.click('text=Create Table')
  await page.fill('[name="name"]', 'test_table')
  await page.click('text=Next')

  // Add field
  await page.fill('[name="fieldName"]', 'email')
  await page.selectOption('[name="fieldType"]', 'string')
  await page.check('[name="required"]')
  await page.click('text=Add Field')
  await page.click('text=Create')

  // Verify table created
  await expect(page.locator('text=test_table')).toBeVisible()

  // Open data browser
  await page.click('text=View Data')
  await page.waitForSelector('[aria-label="Table data grid"]')

  // Add row
  await page.click('text=Insert Row')
  await page.fill('[name="email"]', 'test@example.com')
  await page.click('text=Save')

  // Verify row added
  await expect(page.locator('text=test@example.com')).toBeVisible()
})
```

---

## 10. Implementation Checklist

### Phase 1: Foundation (Week 1)

- [ ] Update type definitions in `types/index.ts`
  - [ ] Enhance `Table` interface
  - [ ] Add `TableSchema`, `TableField`, `TableIndex` types
  - [ ] Add `TableRow`, `TableQueryResult` types
  - [ ] Add enums: `FieldType`, `IndexType`, `TableStatus`

- [ ] Extend API client in `services/api-client.ts`
  - [ ] `createTable()`
  - [ ] `updateTableSchema()`
  - [ ] `deleteTable()`
  - [ ] `queryTableRows()`
  - [ ] `insertTableRow()`
  - [ ] `updateTableRow()`
  - [ ] `deleteTableRows()`
  - [ ] `exportTableData()`

- [ ] Create React Query hooks in `hooks/useTables.ts`
  - [ ] `useTables()`
  - [ ] `useTable()`
  - [ ] `useCreateTable()`
  - [ ] `useDeleteTable()`
  - [ ] `useTableData()`
  - [ ] `useUpdateTableRow()`
  - [ ] `useDeleteTableRows()`

### Phase 2: Core Components (Week 2)

- [ ] Create `components/tables/` directory structure
  ```
  components/tables/
  ├── EnhancedTableCard.tsx
  ├── CreateTableDialog.tsx
  ├── SchemaBuilder.tsx
  ├── FieldRow.tsx
  ├── IndexBuilder.tsx
  ├── SearchFilterBar.tsx
  ├── TableDataBrowser.tsx
  └── types.ts
  ```

- [ ] Implement `EnhancedTableCard`
  - [ ] Basic card layout with status badge
  - [ ] Schema preview section
  - [ ] Actions dropdown menu
  - [ ] Export functionality

- [ ] Implement `SearchFilterBar`
  - [ ] Search input with debounce
  - [ ] Filter dropdown
  - [ ] Sort dropdown
  - [ ] Clear filters button

### Phase 3: Table Creation (Week 3)

- [ ] Implement `CreateTableDialog`
  - [ ] Multi-step wizard navigation
  - [ ] Step 1: Basic information form
  - [ ] Step 2: Schema builder integration
  - [ ] Step 3: Index configuration
  - [ ] Step 4: Review and submit
  - [ ] Form validation
  - [ ] Error handling and display

- [ ] Implement `SchemaBuilder`
  - [ ] Field list display
  - [ ] Add/remove field buttons
  - [ ] Field type selector
  - [ ] Constraint checkboxes
  - [ ] Validation feedback

- [ ] Implement `FieldRow`
  - [ ] Input fields for field configuration
  - [ ] Type-specific options
  - [ ] Remove field button

### Phase 4: Data Browser (Week 4)

- [ ] Implement `TableDataBrowser` modal
  - [ ] Header with table info and actions
  - [ ] Data grid with virtualization
  - [ ] Column headers with sort indicators
  - [ ] Row selection checkboxes
  - [ ] Pagination controls

- [ ] Implement cell editing
  - [ ] Double-click to edit
  - [ ] Type-specific inputs
  - [ ] Auto-save on blur
  - [ ] Optimistic updates
  - [ ] Error rollback

- [ ] Implement row operations
  - [ ] Insert row dialog
  - [ ] Delete selected rows
  - [ ] Bulk actions menu

### Phase 5: Advanced Features (Week 5)

- [ ] Export functionality
  - [ ] JSON export
  - [ ] CSV export
  - [ ] Export filtered/selected data
  - [ ] Download trigger

- [ ] Search and filtering in data browser
  - [ ] Per-column search
  - [ ] Advanced filter builder
  - [ ] Filter persistence in URL

- [ ] Performance optimizations
  - [ ] Virtual scrolling for large tables
  - [ ] Query caching tuning
  - [ ] Lazy loading images/blobs

### Phase 6: Polish and Testing (Week 6)

- [ ] Accessibility audit
  - [ ] Keyboard navigation
  - [ ] ARIA labels
  - [ ] Screen reader testing
  - [ ] Color contrast verification

- [ ] Responsive design
  - [ ] Mobile layout for cards
  - [ ] Tablet layout for data browser
  - [ ] Touch-friendly controls

- [ ] Error handling
  - [ ] Toast notifications
  - [ ] Inline error messages
  - [ ] Network error recovery
  - [ ] Validation error display

- [ ] Unit tests
  - [ ] Component rendering
  - [ ] User interactions
  - [ ] Form validation
  - [ ] API integration

- [ ] Integration tests
  - [ ] Multi-step flows
  - [ ] Data mutations
  - [ ] Error scenarios

- [ ] E2E tests
  - [ ] Create table flow
  - [ ] Edit data flow
  - [ ] Delete operations
  - [ ] Export functionality

### Phase 7: Documentation and Deployment

- [ ] Update component documentation
  - [ ] Props interfaces
  - [ ] Usage examples
  - [ ] Storybook stories (if applicable)

- [ ] Update user documentation
  - [ ] Feature overview
  - [ ] How-to guides
  - [ ] Screenshots/GIFs

- [ ] Performance testing
  - [ ] Load testing with large datasets
  - [ ] Browser compatibility
  - [ ] Lighthouse audit

- [ ] Deploy to staging
  - [ ] Feature flag rollout
  - [ ] User acceptance testing
  - [ ] Bug fixes

- [ ] Production deployment
  - [ ] Gradual rollout
  - [ ] Monitoring and alerts
  - [ ] User feedback collection

---

## 11. Future Enhancements

### Planned Features

1. **Schema Evolution**
   - Add/remove columns from existing tables
   - Change column types with data migration
   - Schema version history

2. **Advanced Querying**
   - Visual query builder
   - Saved queries
   - Query templates
   - SQL-like query language

3. **Data Visualization**
   - Chart builder for numeric data
   - Pivot tables
   - Data summaries and aggregations

4. **Collaboration**
   - Real-time multi-user editing
   - Row-level comments
   - Change history/audit log
   - Permissions per table

5. **Import/Export**
   - Import from CSV/JSON
   - Import from external databases
   - Scheduled exports
   - Webhook integration

6. **Performance**
   - Query plan visualization
   - Index recommendations
   - Query optimization suggestions

### Technical Debt to Address

- Implement proper error boundaries
- Add Sentry or error tracking
- Optimize bundle size (code splitting)
- Add service worker for offline support
- Implement WebSocket for real-time updates

---

## 12. Risk Assessment

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Large dataset performance issues | High | Medium | Implement virtual scrolling, server-side pagination, query optimization |
| Complex schema validation | Medium | High | Use JSON Schema for validation, comprehensive tests |
| Browser compatibility | Medium | Low | Test in all major browsers, use polyfills |
| Concurrent editing conflicts | High | Medium | Implement optimistic locking, conflict resolution UI |

### UX Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Complex schema builder overwhelming users | High | High | Add guided tour, templates, tooltips |
| Data grid confusing for non-technical users | Medium | Medium | Provide contextual help, keyboard shortcuts guide |
| Export large datasets timing out | High | Low | Background jobs for large exports, progress indicators |

### Security Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| SQL injection via query builder | Critical | Low | Parameterized queries, input sanitization |
| Unauthorized table access | High | Medium | Enforce project-level permissions on backend |
| XSS via user-generated content | High | Low | Sanitize all rendered data, use React's built-in escaping |

---

## 13. Success Metrics

### Quantitative Metrics

- **Page Load Time**: < 2 seconds for table list
- **Data Grid Load Time**: < 1 second for 50 rows
- **Search Response Time**: < 300ms (perceived instant)
- **Error Rate**: < 1% of API requests
- **Uptime**: > 99.5%

### Qualitative Metrics

- User can create a table in < 2 minutes (tested with 5 users)
- User can find and edit data in < 30 seconds (task analysis)
- Users rate interface 4.5+ / 5 for usability
- Zero critical accessibility issues (WCAG 2.1 AA)

### Adoption Metrics

- 80% of active projects use tables feature within 30 days
- Average 10+ tables created per project
- 50% of users return to edit data weekly
- Export feature used by 30% of table creators

---

## Appendix A: File Structure

```
/Users/aideveloper/core/zerodb-local/dashboard/
├── app/
│   └── tables/
│       └── page.tsx                     # Main tables page (enhanced)
├── components/
│   ├── tables/
│   │   ├── CreateTableDialog.tsx       # New: Table creation wizard
│   │   ├── EnhancedTableCard.tsx       # New: Enhanced table card
│   │   ├── SchemaBuilder.tsx           # New: Schema editor
│   │   ├── FieldRow.tsx                # New: Field configuration row
│   │   ├── IndexBuilder.tsx            # New: Index configuration
│   │   ├── SearchFilterBar.tsx         # New: Search and filter controls
│   │   ├── TableDataBrowser.tsx        # New: Data grid browser
│   │   ├── DataGrid.tsx                # New: Table data grid
│   │   ├── EditableCell.tsx            # New: Inline editable cell
│   │   ├── InsertRowDialog.tsx         # New: Insert row form
│   │   ├── ExportDialog.tsx            # New: Export options
│   │   └── types.ts                     # New: Component type definitions
│   └── ui/
│       ├── dialog.tsx                   # shadcn/ui dialog
│       ├── dropdown-menu.tsx            # shadcn/ui dropdown
│       ├── select.tsx                   # shadcn/ui select
│       ├── checkbox.tsx                 # shadcn/ui checkbox
│       ├── badge.tsx                    # shadcn/ui badge
│       └── table.tsx                    # shadcn/ui table
├── hooks/
│   ├── useTables.ts                    # New: Table-related hooks
│   ├── useDebounce.ts                  # New: Debounce hook
│   └── useTableData.ts                 # New: Data grid hooks
├── services/
│   └── api-client.ts                   # Updated: Extended with table methods
├── types/
│   └── index.ts                        # Updated: Added table types
└── lib/
    └── utils.ts                        # Existing: Utility functions
```

---

## Appendix B: Design Tokens

### Colors

```typescript
// Status colors
const statusColors = {
  ready: 'bg-green-100 text-green-800 border-green-200',
  syncing: 'bg-blue-100 text-blue-800 border-blue-200',
  error: 'bg-red-100 text-red-800 border-red-200',
  creating: 'bg-gray-100 text-gray-800 border-gray-200'
}

// Field type colors
const typeColors = {
  string: 'text-purple-600',
  number: 'text-blue-600',
  boolean: 'text-green-600',
  object: 'text-orange-600',
  array: 'text-pink-600',
  date: 'text-indigo-600',
  json: 'text-teal-600'
}
```

### Typography

```typescript
const typography = {
  pageTitle: 'text-3xl font-bold',
  cardTitle: 'text-xl font-semibold',
  sectionTitle: 'text-lg font-medium',
  label: 'text-sm font-medium',
  body: 'text-base',
  caption: 'text-sm text-gray-600',
  code: 'font-mono text-sm'
}
```

### Spacing

```typescript
const spacing = {
  cardPadding: 'p-6',
  cardGap: 'gap-6',
  sectionGap: 'gap-4',
  formGap: 'gap-3',
  iconTextGap: 'gap-2'
}
```

---

## Appendix C: References

- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Next.js 14 Documentation](https://nextjs.org/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)
- [ZeroDB API Documentation](internal reference)

---

**Document Version**: 1.0
**Last Updated**: 2026-03-07
**Author**: System Architect
**Status**: Ready for Implementation
