'use client'

import { Card, CardContent } from '@/components/ui/card'
import { FileText } from 'lucide-react'

export default function FilesPage() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">File Storage</h1>
        <p className="text-gray-600">Browse and manage your stored files</p>
      </div>
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <FileText className="h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-500">File browser coming soon</p>
        </CardContent>
      </Card>
    </div>
  )
}
