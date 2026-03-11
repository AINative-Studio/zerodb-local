'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Database, HardDrive, Activity, AlertCircle, CheckCircle } from 'lucide-react'
import { HeroSection } from '@/components/home/HeroSection'
import { FeatureCards } from '@/components/home/FeatureCards'
import { CodeExamplesSection } from '@/components/home/CodeExamplesSection'
import { QuickStats } from '@/components/home/QuickStats'

export default function DashboardPage(): JSX.Element {
  const { data: health, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 5000,
  })

  const getStatusColor = (status: string): 'success' | 'warning' | 'destructive' => {
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
    <div className="p-8 max-w-7xl mx-auto">
      {/* Hero Section */}
      <HeroSection />

      {/* Feature Cards */}
      <FeatureCards />

      {/* Quick Stats */}
      <QuickStats
        totalVectors={0}
        tablesCreated={0}
        filesStored={0}
      />

      {/* Code Examples */}
      <CodeExamplesSection />

      {/* System Status Overview */}
      <section className="mb-8" aria-labelledby="system-status-heading">
        <h2 id="system-status-heading" className="text-2xl font-bold mb-4 text-gray-900">
          System Status
        </h2>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Overall Health</CardTitle>
                <CardDescription>Real-time status of all services</CardDescription>
              </div>
              <Badge variant={getStatusColor(health?.status || 'unhealthy')}>
                {health?.status?.toUpperCase()}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-gray-600">
              {health?.summary.healthy} of {health?.summary.total} services operational
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Service Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <ServiceCard
          name="PostgreSQL"
          status={health?.services.postgres.status || 'unhealthy'}
          latency={health?.services.postgres.latency_ms}
          icon={<Database className="h-5 w-5" />}
          description="Primary database"
        />
        <ServiceCard
          name="Qdrant"
          status={health?.services.qdrant.status || 'unhealthy'}
          latency={health?.services.qdrant.latency_ms}
          icon={<Activity className="h-5 w-5" />}
          description="Vector search engine"
        />
        <ServiceCard
          name="MinIO"
          status={health?.services.minio.status || 'unhealthy'}
          latency={health?.services.minio.latency_ms}
          icon={<HardDrive className="h-5 w-5" />}
          description="Object storage"
        />
        <ServiceCard
          name="RedPanda"
          status={health?.services.redpanda.status || 'unhealthy'}
          latency={health?.services.redpanda.latency_ms}
          icon={<Activity className="h-5 w-5" />}
          description="Event streaming"
        />
        <ServiceCard
          name="Embeddings"
          status={health?.services.embeddings.status || 'unhealthy'}
          latency={health?.services.embeddings.latency_ms}
          icon={<Activity className="h-5 w-5" />}
          description="Local embeddings (BAAI BGE)"
        />
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

function ServiceCard({ name, status, latency, icon, description }: ServiceCardProps): JSX.Element {
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
