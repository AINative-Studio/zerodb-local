# Dashboard Tables Page - Component Diagram

## Visual Component Hierarchy

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            TablesPage (page.tsx)                           │
│  State: selectedProject, searchQuery, filterBy, sortBy                    │
│  Hooks: useTables(), useProjects()                                        │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────────┐      ┌──────────────────────┐      ┌──────────────────┐
│  Header Section   │      │  Project Selector    │      │ Create Button    │
│  - Page Title     │      │  Props: projects[]   │      │ Opens Dialog     │
│  - Description    │      │  State: selected     │      │                  │
└───────────────────┘      └──────────────────────┘      └──────────────────┘
                                                                     │
                                                                     ▼
        ┌────────────────────────────────────────────────────────────────────┐
        │                    CreateTableDialog                               │
        │  Props: projectId, open, onSuccess                                │
        │  State: currentStep, formData, errors                             │
        │  Hook: useCreateTable()                                           │
        └────────────────────────────────────────────────────────────────────┘
                                      │
                  ┌───────────────────┼───────────────────┐
                  │                   │                   │
                  ▼                   ▼                   ▼
        ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │  Step 1: Basic  │  │ Step 2: Schema   │  │ Step 3: Indexes  │
        │  - Name input   │  │ - SchemaBuilder  │  │ - IndexBuilder   │
        │  - Description  │  │ - FieldRow[]     │  │ - IndexRow[]     │
        └─────────────────┘  └──────────────────┘  └──────────────────┘
                                      │
                                      ▼
                             ┌──────────────────┐
                             │  SchemaBuilder   │
                             │  Props: fields[] │
                             │  onChange()      │
                             └──────────────────┘
                                      │
                                      ▼
                             ┌──────────────────┐
                             │    FieldRow[]    │
                             │  Props: field    │
                             │  onRemove()      │
                             └──────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                          SearchFilterBar                                   │
│  Props: searchQuery, onSearchChange, filterBy, sortBy                     │
│  Components: Input, Select (filter), Select (sort)                        │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                            TablesGrid                                      │
│  Layout: grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3                  │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
          ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
          │EnhancedTableCard │ │EnhancedTableCard │ │EnhancedTableCard │
          │Props: table      │ │Props: table      │ │Props: table      │
          │      projectId   │ │      projectId   │ │      projectId   │
          │Callbacks:        │ │Callbacks:        │ │Callbacks:        │
          │ - onViewData     │ │ - onViewData     │ │ - onViewData     │
          │ - onDelete       │ │ - onDelete       │ │ - onDelete       │
          │ - onExport       │ │ - onExport       │ │ - onExport       │
          └──────────────────┘ └──────────────────┘ └──────────────────┘
                    │
                    │ onViewData()
                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         TableDataBrowser (Modal)                           │
│  Props: table, projectId, open, onOpenChange                              │
│  State: page, pageSize, sortColumn, sortDirection, filters, selectedRows  │
│  Hooks: useTableData(), useUpdateTableRow(), useDeleteTableRows()         │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌──────────────────┐      ┌──────────────────────┐      ┌──────────────────┐
│  BrowserHeader   │      │     DataGrid         │      │  Pagination      │
│  - Table name    │      │  ┌────────────────┐  │      │  - Page info     │
│  - Row count     │      │  │ ColumnHeader[] │  │      │  - Navigation    │
│  - Insert button │      │  │ (sortable)     │  │      │                  │
│  - Export button │      │  └────────────────┘  │      └──────────────────┘
└──────────────────┘      │  ┌────────────────┐  │
                          │  │   DataRow[]    │  │
                          │  │ ┌────────────┐ │  │
                          │  │ │EditableCell│ │  │
                          │  │ │EditableCell│ │  │
                          │  │ │EditableCell│ │  │
                          │  │ └────────────┘ │  │
                          │  │   RowActions   │  │
                          │  └────────────────┘  │
                          └──────────────────────┘
```

---

## Data Flow Diagram

```
┌───────────────┐
│     User      │
└───────┬───────┘
        │
        │ 1. Selects Project
        ▼
┌───────────────────────┐
│    TablesPage         │◄──────────┐
│  setSelectedProject() │           │
└───────┬───────────────┘           │
        │                           │
        │ 2. Fetch tables           │ 7. Invalidate query
        ▼                           │
┌───────────────────────┐           │
│  React Query          │           │
│  ['tables', projId]   │           │
└───────┬───────────────┘           │
        │                           │
        │ 3. HTTP GET               │
        ▼                           │
┌───────────────────────┐           │
│   apiClient.          │           │
│   listTables()        │           │
└───────┬───────────────┘           │
        │                           │
        │ 4. Return tables[]        │
        ▼                           │
┌───────────────────────┐           │
│  EnhancedTableCard[]  │           │
│  Display table data   │           │
└───────┬───────────────┘           │
        │                           │
        │ 5. User clicks            │
        │    "View Data"            │
        ▼                           │
┌───────────────────────┐           │
│  TableDataBrowser     │           │
│  Opens modal          │           │
└───────┬───────────────┘           │
        │                           │
        │ 6. Fetch rows             │
        ▼                           │
┌───────────────────────┐           │
│  React Query          │           │
│  ['table-data', ...]  │           │
└───────┬───────────────┘           │
        │                           │
        │ HTTP POST /query          │
        ▼                           │
┌───────────────────────┐           │
│   apiClient.          │           │
│   queryTableRows()    │           │
└───────┬───────────────┘           │
        │                           │
        │ Return rows[]             │
        ▼                           │
┌───────────────────────┐           │
│    DataGrid           │           │
│  Display rows         │           │
└───────┬───────────────┘           │
        │                           │
        │ 8. User edits cell        │
        ▼                           │
┌───────────────────────┐           │
│  useUpdateTableRow()  │           │
│  Optimistic update    │───────────┘
└───────────────────────┘
```

---

## State Management Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TablesPage State                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Local State:                                                       │
│  ┌──────────────────────────────────────────────────────┐          │
│  │ selectedProject: string | undefined                  │          │
│  │ searchQuery: string                                  │          │
│  │ filterBy: TableFilterType                            │          │
│  │ sortBy: TableSortType                                │          │
│  │ isCreateDialogOpen: boolean                          │          │
│  │ viewingTable: Table | null                           │          │
│  └──────────────────────────────────────────────────────┘          │
│                                                                     │
│  Server State (React Query):                                       │
│  ┌──────────────────────────────────────────────────────┐          │
│  │ projects: Project[]                                  │          │
│  │ tables: Table[]                                      │          │
│  └──────────────────────────────────────────────────────┘          │
│                                                                     │
│  Derived State (useMemo):                                          │
│  ┌──────────────────────────────────────────────────────┐          │
│  │ filteredTables = filter + search + sort(tables)      │          │
│  └──────────────────────────────────────────────────────┘          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Props down
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EnhancedTableCard Props                          │
├─────────────────────────────────────────────────────────────────────┤
│  table: Table                                                       │
│  projectId: string                                                  │
│  onViewData: (table: Table) => void                                │
│  onDelete: (tableId: string) => void                               │
│  onExport: (table: Table, format: 'json' | 'csv') => void         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Events up
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      TablesPage Handlers                            │
├─────────────────────────────────────────────────────────────────────┤
│  handleViewData = (table) => setViewingTable(table)                │
│  handleDelete = (id) => deleteMutation.mutate(id)                  │
│  handleExport = (table, format) => exportTable(table, format)      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    TableDataBrowser State                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Local State:                                                       │
│  ┌──────────────────────────────────────────────────────┐          │
│  │ page: number                                         │          │
│  │ pageSize: number                                     │          │
│  │ sortColumn: string                                   │          │
│  │ sortDirection: 'asc' | 'desc'                        │          │
│  │ filters: Record<string, any>                         │          │
│  │ selectedRows: Set<string>                            │          │
│  │ editingCell: {row: string, col: string} | null       │          │
│  └──────────────────────────────────────────────────────┘          │
│                                                                     │
│  URL State (Search Params):                                        │
│  ┌──────────────────────────────────────────────────────┐          │
│  │ ?page=1&sort=name&dir=asc&filter[name]=...          │          │
│  └──────────────────────────────────────────────────────┘          │
│                                                                     │
│  Server State (React Query):                                       │
│  ┌──────────────────────────────────────────────────────┐          │
│  │ tableData: { rows: TableRow[], total: number }      │          │
│  └──────────────────────────────────────────────────────┘          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Interaction Sequence Diagrams

### Create Table Flow

```
User          TablesPage       CreateTableDialog    SchemaBuilder     API
 │                │                    │                  │            │
 │ Click Create   │                    │                  │            │
 ├───────────────>│                    │                  │            │
 │                │ Open Dialog        │                  │            │
 │                ├───────────────────>│                  │            │
 │                │                    │                  │            │
 │ Enter name     │                    │                  │            │
 ├────────────────┴───────────────────>│                  │            │
 │                                     │                  │            │
 │ Click Next     │                    │                  │            │
 ├────────────────┴───────────────────>│                  │            │
 │                                     │ Render Builder   │            │
 │                                     ├─────────────────>│            │
 │                                     │                  │            │
 │ Add field      │                    │                  │            │
 ├────────────────┴───────────────────┴─────────────────>│            │
 │                                                        │            │
 │ Click Create   │                    │                  │            │
 ├────────────────┴───────────────────>│                  │            │
 │                                     │ Validate         │            │
 │                                     │                  │            │
 │                                     │ POST /tables     │            │
 │                                     ├──────────────────┴──────────>│
 │                                     │                               │
 │                                     │ Return table                  │
 │                                     │<──────────────────────────────┤
 │                                     │                               │
 │                                     │ onSuccess()                   │
 │                │<───────────────────┤                               │
 │                │ Invalidate query   │                               │
 │                │                    │                               │
 │ Close Dialog   │                    │                               │
 │<───────────────┤                    │                               │
 │                │                    │                               │
 │ See new table  │                    │                               │
 │<───────────────┤                    │                               │
```

### Edit Cell Flow

```
User          DataGrid        EditableCell      useMutation        API
 │                │                │                 │              │
 │ Double-click   │                │                 │              │
 ├───────────────>│                │                 │              │
 │                │ Enable edit    │                 │              │
 │                ├───────────────>│                 │              │
 │                │                │                 │              │
 │ Type value     │                │                 │              │
 ├────────────────┴───────────────>│                 │              │
 │                                 │                 │              │
 │ Press Enter    │                │                 │              │
 ├────────────────┴───────────────>│                 │              │
 │                                 │ mutate()        │              │
 │                                 ├────────────────>│              │
 │                                 │                 │              │
 │                                 │ onMutate        │              │
 │                                 │ (optimistic)    │              │
 │                                 │<────────────────┤              │
 │ See update     │<───────────────┤                 │              │
 │<───────────────┤                │                 │              │
 │                                 │                 │ PATCH /row   │
 │                                 │                 ├─────────────>│
 │                                 │                 │              │
 │                                 │                 │ Return row   │
 │                                 │                 │<─────────────┤
 │                                 │                 │              │
 │                                 │ onSuccess       │              │
 │                                 │<────────────────┤              │
 │                                 │                 │              │
 │ Confirmed      │<───────────────┤                 │              │
 │<───────────────┤                │                 │              │
```

### Delete Table Flow

```
User          TableCard       ConfirmDialog      useMutation        API
 │                │                │                 │              │
 │ Click menu     │                │                 │              │
 ├───────────────>│                │                 │              │
 │                │ Show menu      │                 │              │
 │<───────────────┤                │                 │              │
 │                │                │                 │              │
 │ Click Delete   │                │                 │              │
 ├───────────────>│                │                 │              │
 │                │ Open confirm   │                 │              │
 │                ├───────────────>│                 │              │
 │                │                │                 │              │
 │ Confirm        │                │                 │              │
 ├────────────────┴───────────────>│                 │              │
 │                                 │ mutate(id)      │              │
 │                                 ├────────────────>│              │
 │                                 │                 │ DELETE /table│
 │                                 │                 ├─────────────>│
 │                                 │                 │              │
 │                                 │                 │ 204 No Content│
 │                                 │                 │<─────────────┤
 │                                 │                 │              │
 │                                 │ onSuccess       │              │
 │                                 │<────────────────┤              │
 │                │<───────────────┤                 │              │
 │                │ Invalidate     │                 │              │
 │                │ tables query   │                 │              │
 │                │                │                 │              │
 │ Card removed   │                │                 │              │
 │<───────────────┤                │                 │              │
```

---

## Component Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                         External Dependencies                   │
├─────────────────────────────────────────────────────────────────┤
│  - React                    (UI library)                        │
│  - Next.js                  (Framework)                         │
│  - React Query              (Server state)                      │
│  - Tailwind CSS             (Styling)                           │
│  - shadcn/ui                (UI components)                     │
│  - date-fns                 (Date formatting)                   │
│  - axios                    (HTTP client)                       │
│  - lucide-react             (Icons)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Core Infrastructure                     │
├─────────────────────────────────────────────────────────────────┤
│  - types/index.ts           (Type definitions)                  │
│  - services/api-client.ts   (API wrapper)                       │
│  - lib/utils.ts             (Utilities)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Custom Hooks                            │
├─────────────────────────────────────────────────────────────────┤
│  - hooks/useTables.ts       (Table queries)                     │
│  - hooks/useDebounce.ts     (Debounce logic)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Reusable Components                        │
├─────────────────────────────────────────────────────────────────┤
│  - components/ui/*          (shadcn base components)            │
│  - SearchFilterBar          (Search & filters)                  │
│  - SchemaBuilder            (Schema editor)                     │
│  - FieldRow                 (Field config)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Feature Components                         │
├─────────────────────────────────────────────────────────────────┤
│  - EnhancedTableCard        (Table card)                        │
│  - CreateTableDialog        (Creation wizard)                   │
│  - TableDataBrowser         (Data viewer)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                           Pages                                 │
├─────────────────────────────────────────────────────────────────┤
│  - app/tables/page.tsx      (Main tables page)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Communication Patterns

### 1. Props Drilling Pattern

```
TablesPage
│
├─ prop: selectedProject
│  ├─> EnhancedTableCard
│  └─> CreateTableDialog
│
└─ callback: onViewData()
   └─> EnhancedTableCard.onClick
```

### 2. Context Pattern (Future Enhancement)

```
<TablesContext.Provider value={{ projectId, tables, refetch }}>
  <TablesPage>
    <EnhancedTableCard />  {/* Access via useTablesContext() */}
    <CreateTableDialog />  {/* Access via useTablesContext() */}
  </TablesPage>
</TablesContext.Provider>
```

### 3. React Query Global State

```
Component A                    React Query Cache                Component B
    │                                  │                             │
    │ useQuery(['tables'])             │                             │
    ├─────────────────────────────────>│                             │
    │                                  │                             │
    │ Return cached data               │                             │
    │<─────────────────────────────────┤                             │
    │                                  │                             │
    │ mutate()                         │                             │
    ├─────────────────────────────────>│                             │
    │                                  │                             │
    │ invalidateQueries()              │                             │
    ├─────────────────────────────────>│                             │
    │                                  │ Notify subscribers          │
    │                                  ├────────────────────────────>│
    │                                  │                             │
    │                                  │ useQuery(['tables'])        │
    │                                  │<────────────────────────────┤
    │                                  │                             │
    │                                  │ Return fresh data           │
    │                                  ├────────────────────────────>│
```

### 4. Event Handling Pattern

```
User Action
    │
    ▼
Event Handler (in Parent)
    │
    ├─> Validation
    ├─> Mutation
    ├─> Optimistic Update
    │
    ▼
React Query
    │
    ├─> API Call
    ├─> Cache Update
    └─> UI Refresh
```

---

## File Organization

```
dashboard/
│
├── app/
│   └── tables/
│       └── page.tsx                      [Page Container - Orchestration]
│
├── components/
│   └── tables/
│       ├── types.ts                      [Shared Component Types]
│       │
│       ├── EnhancedTableCard.tsx         [Presentational - Display]
│       ├── SearchFilterBar.tsx           [Controlled - Input]
│       │
│       ├── CreateTableDialog.tsx         [Container - Logic + UI]
│       │   ├── SchemaBuilder.tsx         [Controlled - Complex Input]
│       │   │   └── FieldRow.tsx          [Presentational - List Item]
│       │   └── IndexBuilder.tsx          [Controlled - Complex Input]
│       │
│       └── TableDataBrowser.tsx          [Container - Modal]
│           ├── DataGrid.tsx              [Presentational - Table]
│           │   ├── ColumnHeader.tsx      [Presentational - Sortable]
│           │   ├── DataRow.tsx           [Container - Row Logic]
│           │   └── EditableCell.tsx      [Controlled - Inline Edit]
│           │
│           ├── InsertRowDialog.tsx       [Container - Form]
│           └── ExportDialog.tsx          [Container - Export Logic]
│
├── hooks/
│   ├── useTables.ts                      [Data Fetching]
│   ├── useTableData.ts                   [Data Fetching + Pagination]
│   └── useDebounce.ts                    [Utility Hook]
│
├── services/
│   └── api-client.ts                     [HTTP Client]
│
└── types/
    └── index.ts                          [Global Types]
```

**Component Type Legend**:
- **Container**: Logic + state management + side effects
- **Presentational**: Pure UI display, no business logic
- **Controlled**: Receives value + onChange from parent
- **Page Container**: Top-level orchestration, routes, layout

---

## Key Architectural Decisions

### 1. Modal vs Separate Page for Data Browser

**Decision**: Use modal (Dialog) initially, with option for full-page view

**Rationale**:
- Faster navigation (no route change)
- Maintains context of tables list
- Easier to implement
- Can add "Open in new tab" later

### 2. Optimistic Updates vs Pessimistic

**Decision**: Optimistic updates with rollback for edit operations

**Rationale**:
- Better perceived performance
- React Query supports rollback out of the box
- Table edits are common and should feel instant

### 3. Schema Validation Location

**Decision**: Both client-side and server-side validation

**Rationale**:
- Client: Immediate feedback, better UX
- Server: Security, data integrity, authoritative source
- Duplicate some logic but worth the trade-off

### 4. State Management: Local vs Context vs Redux

**Decision**: Local state + React Query, no global state library

**Rationale**:
- React Query handles server state perfectly
- Local state sufficient for UI state
- Avoid complexity of Redux for this feature
- Can migrate to Context if needed later

### 5. TypeScript Strictness

**Decision**: Strict mode enabled, explicit types for all props/state

**Rationale**:
- Catch bugs at compile time
- Better IDE autocomplete
- Self-documenting code
- Aligns with existing dashboard standards

---

**Document Version**: 1.0
**Last Updated**: 2026-03-07
**Companion to**: DASHBOARD_TABLES_PAGE_ARCHITECTURE.md
