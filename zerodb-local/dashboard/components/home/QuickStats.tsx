'use client'

import { Card, CardContent, CardDescription, CardHeader } from '@/components/ui/card'
import { Database, Layers, FileText, Package } from 'lucide-react'

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: string
  description: string
}

function StatCard({ icon, label, value, description }: StatCardProps): JSX.Element {
  return (
    <Card className="border-gray-200 hover:border-blue-300 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2 mb-1">
          {icon}
          <CardDescription className="font-medium">{label}</CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-gray-900">{value}</div>
        <p className="text-xs text-gray-500 mt-1">{description}</p>
      </CardContent>
    </Card>
  )
}

interface QuickStatsProps {
  totalVectors?: number
  tablesCreated?: number
  filesStored?: number
}

export function QuickStats({
  totalVectors = 0,
  tablesCreated = 0,
  filesStored = 0
}: QuickStatsProps): JSX.Element {
  return (
    <section className="mb-12" aria-labelledby="quick-stats-heading">
      <h2 id="quick-stats-heading" className="text-2xl font-bold mb-4 text-gray-900">
        Quick Stats
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Database className="h-5 w-5 text-blue-600" aria-hidden="true" />}
          label="API Endpoint"
          value="localhost:8000"
          description="Local development"
        />
        <StatCard
          icon={<Layers className="h-5 w-5 text-green-600" aria-hidden="true" />}
          label="Total Vectors"
          value={totalVectors.toLocaleString()}
          description="Embeddings stored"
        />
        <StatCard
          icon={<FileText className="h-5 w-5 text-purple-600" aria-hidden="true" />}
          label="Tables Created"
          value={tablesCreated.toString()}
          description="Database tables"
        />
        <StatCard
          icon={<Package className="h-5 w-5 text-orange-600" aria-hidden="true" />}
          label="Files Stored"
          value={filesStored.toLocaleString()}
          description="Object storage"
        />
      </div>
    </section>
  )
}
