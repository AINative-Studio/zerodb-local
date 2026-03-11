'use client'

import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import { Table } from '@/types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Database, Plus, Loader2 } from 'lucide-react'
import {
  CreateTableDialog,
  EnhancedTableCard,
  TableDataBrowser,
  SearchFilter,
  FilterStatus,
  SortBy,
} from '@/components/tables'

export default function TablesPage() {
  const queryClient = useQueryClient()
  const [selectedProject, setSelectedProject] = useState<string>()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [browserDialogOpen, setBrowserDialogOpen] = useState(false)
  const [selectedTable, setSelectedTable] = useState<Table | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')
  const [sortBy, setSortBy] = useState<SortBy>('name')

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.listProjects(),
  })

  const { data: tables, isLoading } = useQuery({
    queryKey: ['tables', selectedProject],
    queryFn: () => selectedProject ? apiClient.listTables(selectedProject) : Promise.resolve([]),
    enabled: !!selectedProject,
  })

  const deleteTableMutation = useMutation({
    mutationFn: async (tableName: string) => {
      if (!selectedProject) throw new Error('No project selected')
      return apiClient.deleteTable(selectedProject, tableName)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tables', selectedProject] })
    },
  })

  const filteredAndSortedTables = useMemo(() => {
    if (!tables) return []

    let filtered = tables

    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter((table) =>
        table.name.toLowerCase().includes(query)
      )
    }

    if (filterStatus === 'has-data') {
      filtered = filtered.filter((table) => (table.row_count ?? 0) > 0)
    } else if (filterStatus === 'empty') {
      filtered = filtered.filter((table) => (table.row_count ?? 0) === 0)
    }

    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name)
        case 'created':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'updated':
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        case 'rows':
          return (b.row_count ?? 0) - (a.row_count ?? 0)
        default:
          return 0
      }
    })

    return sorted
  }, [tables, searchQuery, filterStatus, sortBy])

  const handleViewData = (table: Table) => {
    setSelectedTable(table)
    setBrowserDialogOpen(true)
  }

  const handleEditTable = (table: Table) => {
    console.log('Edit table:', table)
  }

  const handleDeleteTable = async (table: Table) => {
    if (confirm(`Are you sure you want to delete the table "${table.name}"? This action cannot be undone.`)) {
      try {
        await deleteTableMutation.mutateAsync(table.name)
      } catch (error) {
        console.error('Failed to delete table:', error)
      }
    }
  }

  const handleExportTable = (table: Table) => {
    console.log('Export table:', table)
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-3xl font-bold mb-2">NoSQL Tables</h1>
            <p className="text-gray-600">
              Browse and manage your document-based data collections
            </p>
          </div>
          {selectedProject && (
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Table
            </Button>
          )}
        </div>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">Select Project</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {projects && projects.length > 0 ? (
              projects.map((project) => (
                <Button
                  key={project.id}
                  variant={selectedProject === project.id ? 'default' : 'outline'}
                  onClick={() => setSelectedProject(project.id)}
                >
                  {project.name}
                </Button>
              ))
            ) : (
              <p className="text-gray-500">No projects available</p>
            )}
          </div>
        </CardContent>
      </Card>

      {selectedProject && (
        <>
          <div className="mb-6">
            <SearchFilter
              onSearchChange={setSearchQuery}
              onFilterChange={setFilterStatus}
              onSortChange={setSortBy}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {isLoading ? (
              <Card>
                <CardContent className="flex justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                </CardContent>
              </Card>
            ) : filteredAndSortedTables.length > 0 ? (
              filteredAndSortedTables.map((table) => (
                <EnhancedTableCard
                  key={table.id}
                  table={table}
                  onViewData={handleViewData}
                  onEdit={handleEditTable}
                  onDelete={handleDeleteTable}
                  onExport={handleExportTable}
                />
              ))
            ) : (
              <Card className="col-span-full">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Database className="h-12 w-12 text-gray-400 mb-4" />
                  <p className="text-gray-500">
                    {searchQuery || filterStatus !== 'all'
                      ? 'No tables match your filters'
                      : 'No tables in this project'}
                  </p>
                  {!searchQuery && filterStatus === 'all' && (
                    <Button
                      variant="outline"
                      className="mt-4"
                      onClick={() => setCreateDialogOpen(true)}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Create Your First Table
                    </Button>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </>
      )}

      {!selectedProject && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Database className="h-12 w-12 text-gray-400 mb-4" />
            <p className="text-gray-500">Select a project to view tables</p>
          </CardContent>
        </Card>
      )}

      {selectedProject && (
        <>
          <CreateTableDialog
            projectId={selectedProject}
            open={createDialogOpen}
            onOpenChange={setCreateDialogOpen}
          />

          {selectedTable && (
            <TableDataBrowser
              projectId={selectedProject}
              table={selectedTable}
              open={browserDialogOpen}
              onOpenChange={setBrowserDialogOpen}
            />
          )}
        </>
      )}
    </div>
  )
}
