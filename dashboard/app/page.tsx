'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Database, HardDrive, Activity, AlertCircle, CheckCircle, FolderOpen } from 'lucide-react'

// Lite mode (SQLite + FAISS + filesystem, zero-infrastructure default) and
// full mode (PostgreSQL + Qdrant + MinIO + RedPanda + embeddings, Docker
// stack) report entirely different service keys in /health -- render
// whichever set actually matches `backend` instead of assuming full mode.
const FULL_MODE_SERVICES = [
  { key: 'postgres', name: 'PostgreSQL', icon: Database, description: 'Primary database' },
  { key: 'qdrant', name: 'Qdrant', icon: Activity, description: 'Vector search engine' },
  { key: 'minio', name: 'MinIO', icon: HardDrive, description: 'Object storage' },
  { key: 'redpanda', name: 'RedPanda', icon: Activity, description: 'Event streaming' },
  { key: 'embeddings', name: 'Embeddings', icon: Activity, description: 'Local embeddings (BAAI BGE)' },
] as const

const LITE_MODE_SERVICES = [
  { key: 'sqlite', name: 'SQLite', icon: Database, description: 'Primary database' },
  { key: 'faiss', name: 'FAISS', icon: Activity, description: 'Vector search engine' },
  { key: 'filesystem', name: 'Filesystem', icon: FolderOpen, description: 'Local file storage' },
] as const

export default function DashboardPage() {
  const { data: health, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 5000,
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success'
      case 'degraded':
        return 'warning'
      default:
        return 'destructive'
    }
  }

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-800 flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Connection Error
            </CardTitle>
            <CardDescription className="text-red-600">
              Unable to connect to ZeroDB API at localhost:8000
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-red-700">{error?.message || 'Unknown error'}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">ZeroLocal Dashboard</h1>
        <p className="text-gray-600">Monitor your self-hosted AI database</p>
      </div>

      {/* System Status Overview */}
      <div className="mb-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>System Status</CardTitle>
                <CardDescription>Overall health of all services</CardDescription>
              </div>
              <Badge variant={getStatusColor(health?.status || 'unhealthy')}>
                {health?.status?.toUpperCase()}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-gray-600">
              {health?.summary?.healthy ?? 0} of {health?.summary?.total ?? 0} services operational
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Service Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {(health?.backend === 'full' ? FULL_MODE_SERVICES : LITE_MODE_SERVICES).map((service) => (
          <ServiceCard
            key={service.key}
            name={service.name}
            status={health?.services?.[service.key]?.status || 'unhealthy'}
            latency={health?.services?.[service.key]?.latency_ms}
            icon={<service.icon className="h-5 w-5" />}
            description={service.description}
          />
        ))}
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>API Endpoint</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">localhost:8000</div>
            <p className="text-xs text-gray-500 mt-1">Local development</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Dashboard</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">localhost:3000</div>
            <p className="text-xs text-gray-500 mt-1">This interface</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Version</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1.0.0</div>
            <p className="text-xs text-gray-500 mt-1">ZeroLocal</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Mode</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Local</div>
            <p className="text-xs text-gray-500 mt-1">No API costs</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

interface ServiceCardProps {
  name: string
  status: string
  latency?: number
  icon: React.ReactNode
  description: string
}

function ServiceCard({ name, status, latency, icon, description }: ServiceCardProps) {
  const isHealthy = status === 'healthy'

  return (
    <Card className={isHealthy ? 'border-green-200' : 'border-red-200'}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {icon}
            <CardTitle className="text-lg">{name}</CardTitle>
          </div>
          {isHealthy ? (
            <CheckCircle className="h-5 w-5 text-green-600" />
          ) : (
            <AlertCircle className="h-5 w-5 text-red-600" />
          )}
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <Badge variant={isHealthy ? 'success' : 'destructive'}>
            {status}
          </Badge>
          {latency && (
            <span className="text-xs text-gray-500">{latency}ms</span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
