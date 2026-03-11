'use client'

import { Button } from '@/components/ui/button'
import { BookOpen, Plus } from 'lucide-react'
import Link from 'next/link'

export function HeroSection(): JSX.Element {
  return (
    <section
      className="relative bg-gradient-to-br from-blue-600 via-blue-700 to-blue-800 text-white py-16 px-8 rounded-xl mb-8"
      role="banner"
    >
      <div className="max-w-4xl mx-auto text-center">
        <h1 className="text-4xl md:text-5xl font-bold mb-4">
          ZeroDB Local - Self-Hosted AI Database Stack
        </h1>

        <p className="text-xl md:text-2xl text-blue-100 mb-8 max-w-3xl mx-auto">
          Complete PostgreSQL, Vector Search, Object Storage, and Event Streaming - All Running Locally
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <Button
            size="lg"
            variant="secondary"
            className="bg-white text-blue-700 hover:bg-blue-50 font-semibold"
            asChild
          >
            <Link href="/docs" className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              View Documentation
            </Link>
          </Button>

          <Button
            size="lg"
            className="bg-white text-blue-700 hover:bg-blue-50 border-2 border-white font-semibold"
            asChild
          >
            <Link href="/projects" className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              Create Project
            </Link>
          </Button>
        </div>
      </div>

      <div className="absolute inset-0 bg-grid-white/5 pointer-events-none rounded-xl" aria-hidden="true" />
    </section>
  )
}
