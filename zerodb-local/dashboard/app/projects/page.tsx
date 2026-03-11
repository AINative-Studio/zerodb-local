'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, Database, Trash2, ExternalLink } from 'lucide-react'
import { formatRelativeTime, formatNumber } from '@/lib/utils'
import Link from 'next/link'
import type { Project } from '@/types'

export default function ProjectsPage() {
  const queryClient = useQueryClient()

  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.listProjects(),
  })

  const deleteMutation = useMutation({
    mutationFn: (projectId: string) => apiClient.deleteProject(projectId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Projects</h1>
          <p className="text-gray-600">
            Manage your ZeroDB projects and collections
          </p>
        </div>
        <Button disabled title="Create project modal coming soon">
          <Plus className="h-4 w-4 mr-2" />
          New Project
        </Button>
      </div>

      {/* Projects Grid */}
      {projects && projects.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onDelete={() => deleteMutation.mutate(project.id)}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Database className="h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium mb-2">No projects yet</h3>
            <p className="text-gray-500 text-center mb-4">
              Create your first project to start using ZeroLocal
            </p>
            <Button disabled title="Create project modal coming soon">
              <Plus className="h-4 w-4 mr-2" />
              Create Project
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Create Project Modal would go here */}
    </div>
  )
}

interface ProjectCardProps {
  project: Project
  onDelete: () => void
}

function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const { data: stats } = useQuery({
    queryKey: ['project-stats', project.id],
    queryFn: () => apiClient.getProjectStats(project.id),
  })

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-xl mb-1">{project.name}</CardTitle>
            <CardDescription>
              {project.description || 'No description'}
            </CardDescription>
          </div>
          <Badge variant="outline">Active</Badge>
        </div>
      </CardHeader>
      <CardContent>
        {/* Stats */}
        {stats && (
          <div className="space-y-2 mb-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Vectors</span>
              <span className="font-medium">{formatNumber(stats.vector_count)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Tables</span>
              <span className="font-medium">{formatNumber(stats.table_count)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Files</span>
              <span className="font-medium">{formatNumber(stats.file_count)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Events</span>
              <span className="font-medium">{formatNumber(stats.event_count)}</span>
            </div>
          </div>
        )}

        {/* Metadata */}
        <div className="text-xs text-gray-500 mb-4">
          Created {formatRelativeTime(project.created_at)}
        </div>

        {/* Actions */}
        <div className="flex gap-2 justify-end">
          <Button
            variant="destructive"
            size="sm"
            onClick={onDelete}
            title="Delete project"
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
