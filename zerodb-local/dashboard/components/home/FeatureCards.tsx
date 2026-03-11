'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Server, Zap, Shield, Check } from 'lucide-react'

interface Feature {
  title: string
  description: string
  icon: React.ReactNode
  points: string[]
}

const features: Feature[] = [
  {
    title: 'Local-First Development',
    description: 'Build AI applications without cloud dependencies',
    icon: <Server className="h-8 w-8 text-blue-600" />,
    points: [
      'No API costs',
      'Full data control',
      'Offline capable',
    ],
  },
  {
    title: 'Lightning Fast',
    description: 'Eliminate network latency for maximum performance',
    icon: <Zap className="h-8 w-8 text-yellow-600" />,
    points: [
      'Local latency',
      'No network overhead',
      'Instant responses',
    ],
  },
  {
    title: 'Production Ready',
    description: 'Use the same stack for development and production',
    icon: <Shield className="h-8 w-8 text-green-600" />,
    points: [
      'Same stack as cloud',
      'Easy migration',
      'Docker-based',
    ],
  },
]

export function FeatureCards(): JSX.Element {
  return (
    <section className="mb-12" aria-labelledby="features-heading">
      <h2 id="features-heading" className="sr-only">
        Key Features
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature) => (
          <Card key={feature.title} className="border-gray-200 hover:border-blue-300 transition-colors">
            <CardHeader>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-lg bg-gray-50">
                  {feature.icon}
                </div>
                <CardTitle className="text-xl">{feature.title}</CardTitle>
              </div>
              <CardDescription className="text-base">{feature.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2" role="list">
                {feature.points.map((point) => (
                  <li key={point} className="flex items-center gap-2 text-sm text-gray-700">
                    <Check className="h-4 w-4 text-green-600 flex-shrink-0" aria-hidden="true" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  )
}
