'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table as TableIcon, Database, FileJson } from 'lucide-react'
import { useState } from 'react'
import { formatRelativeTime, formatNumber } from '@/lib/utils'

export default function TablesPage() {
  const [selectedProject, setSelectedProject] = useState<string>()

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.listProjects(),
  })

  const { data: tables, isLoading } = useQuery({
    queryKey: ['tables', selectedProject],
    queryFn: () => selectedProject ? apiClient.listTables(selectedProject) : Promise.resolve([]),
    enabled: !!selectedProject,
  })

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">NoSQL Tables</h1>
        <p className="text-gray-600">
          Browse and manage your document-based data collections
        </p>
      </div>

      {/* Project Selector */}
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

      {/* Tables List */}
      {selectedProject && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {isLoading ? (
            <Card>
              <CardContent className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
              </CardContent>
            </Card>
          ) : tables && tables.length > 0 ? (
            tables.map((table) => (
              <Card key={table.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-xl mb-1">{table.name}</CardTitle>
                      <CardDescription>NoSQL collection</CardDescription>
                    </div>
                    <TableIcon className="h-5 w-5 text-gray-400" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Rows</span>
                      <span className="font-medium">{formatNumber(table.row_count)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Created</span>
                      <span className="font-medium">{formatRelativeTime(table.created_at)}</span>
                    </div>
                  </div>
                  <Button variant="outline" className="w-full" size="sm">
                    <FileJson className="h-3 w-3 mr-2" />
                    View Data
                  </Button>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card className="col-span-full">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <TableIcon className="h-12 w-12 text-gray-400 mb-4" />
                <p className="text-gray-500">No tables in this project</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {!selectedProject && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Database className="h-12 w-12 text-gray-400 mb-4" />
            <p className="text-gray-500">Select a project to view tables</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
