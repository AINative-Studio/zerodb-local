'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Copy, Check } from 'lucide-react'

interface CodeExample {
  id: string
  label: string
  language: string
  code: string
}

const codeExamples: CodeExample[] = [
  {
    id: 'python',
    label: 'Python',
    language: 'python',
    code: `import psycopg2
from qdrant_client import QdrantClient
from minio import Minio

# PostgreSQL Connection
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="zerodb",
    user="postgres",
    password="postgres"
)

# Qdrant Vector Search
qdrant = QdrantClient(
    host="localhost",
    port=6333
)

# MinIO Object Storage
minio_client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)`,
  },
  {
    id: 'javascript',
    label: 'JavaScript',
    language: 'javascript',
    code: `import { Client } from 'pg';
import { QdrantClient } from '@qdrant/js-client-rest';
import * as Minio from 'minio';

// PostgreSQL Connection
const client = new Client({
  host: 'localhost',
  port: 5432,
  database: 'zerodb',
  user: 'postgres',
  password: 'postgres'
});
await client.connect();

// Qdrant Vector Search
const qdrant = new QdrantClient({
  host: 'localhost',
  port: 6333
});

// MinIO Object Storage
const minioClient = new Minio.Client({
  endPoint: 'localhost',
  port: 9000,
  useSSL: false,
  accessKey: 'minioadmin',
  secretKey: 'minioadmin'
});`,
  },
  {
    id: 'curl',
    label: 'cURL',
    language: 'bash',
    code: `# Check Health Status
curl http://localhost:8000/health

# Qdrant Vector Search
curl http://localhost:6333/collections

# MinIO Object Storage (S3 API)
curl http://localhost:9000/

# RedPanda Event Streaming
curl http://localhost:8081/topics`,
  },
]

export function CodeExamplesSection(): JSX.Element {
  const [activeTab, setActiveTab] = useState('python')
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const activeExample = codeExamples.find((ex) => ex.id === activeTab) || codeExamples[0]

  const handleCopy = async (code: string, id: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(code)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy code:', err)
    }
  }

  return (
    <section className="mb-12" aria-labelledby="code-examples-heading">
      <Card>
        <CardHeader>
          <CardTitle id="code-examples-heading">Quick Start Code Examples</CardTitle>
          <CardDescription>
            Connect to your local ZeroDB services from any language
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div role="tablist" className="flex gap-2 border-b border-gray-200 pb-2">
              {codeExamples.map((example) => (
                <button
                  key={example.id}
                  role="tab"
                  aria-selected={activeTab === example.id}
                  aria-controls={`code-panel-${example.id}`}
                  id={`tab-${example.id}`}
                  onClick={() => setActiveTab(example.id)}
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    activeTab === example.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {example.label}
                </button>
              ))}
            </div>

            <div
              role="tabpanel"
              id={`code-panel-${activeExample.id}`}
              aria-labelledby={`tab-${activeExample.id}`}
              className="relative"
            >
              <div className="absolute top-3 right-3 z-10">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => { void handleCopy(activeExample.code, activeExample.id) }}
                  className="bg-gray-800 hover:bg-gray-700 text-white"
                  aria-label="Copy code to clipboard"
                >
                  {copiedId === activeExample.id ? (
                    <>
                      <Check className="h-4 w-4 mr-1" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4 mr-1" />
                      Copy
                    </>
                  )}
                </Button>
              </div>

              <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm leading-relaxed">
                <code className={`language-${activeExample.language}`}>
                  {activeExample.code}
                </code>
              </pre>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-900">
                <strong>Note:</strong> All services are running locally with default development credentials.
                Change these before deploying to production.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
