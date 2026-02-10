'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Search, Database, Filter } from 'lucide-react'
import { useState } from 'react'
import { formatRelativeTime } from '@/lib/utils'

export default function VectorsPage() {
  const [selectedProject, setSelectedProject] = useState<string>()
  const [searchQuery, setSearchQuery] = useState('')

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.listProjects(),
  })

  const { data: vectors, isLoading } = useQuery({
    queryKey: ['vectors', selectedProject],
    queryFn: () => selectedProject ? apiClient.listVectors(selectedProject) : Promise.resolve([]),
    enabled: !!selectedProject,
  })

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Vector Collections</h1>
        <p className="text-gray-600">
          Browse and search vector embeddings across your projects
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

      {/* Search Interface */}
      {selectedProject && (
        <>
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-lg">Semantic Search</CardTitle>
              <CardDescription>
                Search vectors by semantic similarity
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Enter search query..."
                  className="flex-1 px-4 py-2 border rounded-md"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <Button>
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Vector List */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Vector Embeddings</CardTitle>
                <Badge>{vectors?.length || 0} vectors</Badge>
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                </div>
              ) : vectors && vectors.length > 0 ? (
                <div className="space-y-4">
                  {vectors.map((vector) => (
                    <div
                      key={vector.id}
                      className="border rounded-lg p-4 hover:bg-gray-50"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-medium">{vector.collection}</div>
                        <Badge variant="outline">
                          {vector.vector.length}D
                        </Badge>
                      </div>
                      {vector.metadata && (
                        <div className="text-sm text-gray-600 mb-2">
                          {JSON.stringify(vector.metadata).substring(0, 100)}...
                        </div>
                      )}
                      <div className="text-xs text-gray-500">
                        {formatRelativeTime(vector.created_at)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  No vectors found in this project
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {!selectedProject && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Database className="h-12 w-12 text-gray-400 mb-4" />
            <p className="text-gray-500">Select a project to view vectors</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
