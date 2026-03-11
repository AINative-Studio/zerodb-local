# ZeroDB Local Dashboard - Enhanced Homepage Architecture

**Document Version:** 1.0.0
**Date:** 2026-03-07
**Author:** System Architect
**Location:** `/Users/aideveloper/core/zerodb-local/dashboard/app/page.tsx`

---

## 1. Executive Summary

This document outlines the component architecture for an enhanced ZeroDB Local dashboard homepage that combines existing service monitoring capabilities with new marketing-focused features including a hero section, feature highlights, interactive code examples, and activity statistics.

### Key Architectural Decisions

1. **Component-Based Architecture**: Modular React components with clear separation of concerns
2. **Type Safety**: Full TypeScript coverage with strict typing
3. **API Integration**: Maintain existing React Query integration with `apiClient.getHealth()`
4. **Design System**: Leverage existing Tailwind CSS and shadcn/ui components
5. **Accessibility First**: Semantic HTML with proper ARIA labels throughout
6. **Testability**: Each component designed for isolated unit testing

---

## 2. Requirements Analysis

### 2.1 Functional Requirements

**FR-1: Preserve Existing Features**
- Service health monitoring cards (PostgreSQL, Qdrant, MinIO, RedPanda, Embeddings)
- System status overview with health percentage
- Quick stats cards (API endpoint, version, mode)
- 5-second auto-refresh for health data
- Error states and loading states

**FR-2: Hero Section**
- Compelling tagline showcasing ZeroDB Local value proposition
- Primary CTA button (e.g., "View Documentation")
- Secondary CTA button (e.g., "Quick Start Guide")
- Visually distinct from service monitoring section

**FR-3: Feature Cards Section**
- Three feature cards highlighting local development benefits:
  1. Zero API Costs
  2. Full Privacy Control
  3. Offline Development
- Each card includes icon, title, description
- Responsive grid layout

**FR-4: Code Examples Section**
- Tabbed interface for multiple languages
- Support for Python, JavaScript, cURL examples
- Syntax highlighting for code blocks
- Copy-to-clipboard functionality
- Demonstrates common API usage patterns

**FR-5: Activity Statistics**
- Recent usage metrics (optional - based on API availability)
- Visual representation of activity trends
- Links to detailed views in other dashboard sections

### 2.2 Non-Functional Requirements

**NFR-1: Performance**
- Initial page load < 2 seconds
- Component render time < 100ms
- Minimal bundle size increase (< 50KB gzipped)

**NFR-2: Accessibility**
- WCAG 2.1 Level AA compliance
- Keyboard navigation support
- Screen reader compatibility
- Color contrast ratios > 4.5:1

**NFR-3: Maintainability**
- Component reusability score > 80%
- Test coverage > 80%
- Clear component interfaces (TypeScript)
- Self-documenting code with JSDoc comments

**NFR-4: Responsiveness**
- Mobile-first design
- Breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px)
- Touch-friendly interactive elements (min 44x44px)

---

## 3. Component Hierarchy

```
DashboardPage (page.tsx)
├── DashboardLayout
│   ├── HeroSection
│   │   ├── HeroHeading
│   │   ├── HeroDescription
│   │   └── HeroActions
│   │       ├── Button (Primary CTA)
│   │       └── Button (Secondary CTA)
│   │
│   ├── FeaturesSection
│   │   └── FeatureGrid
│   │       ├── FeatureCard (Zero API Costs)
│   │       ├── FeatureCard (Full Privacy)
│   │       └── FeatureCard (Offline Development)
│   │
│   ├── CodeExamplesSection
│   │   ├── SectionHeader
│   │   ├── TabsRoot (@radix-ui/react-tabs)
│   │   │   ├── TabsList
│   │   │   │   ├── TabsTrigger (Python)
│   │   │   │   ├── TabsTrigger (JavaScript)
│   │   │   │   └── TabsTrigger (cURL)
│   │   │   └── TabsContent
│   │   │       └── CodeBlock
│   │   │           ├── CodeDisplay (with syntax highlighting)
│   │   │           └── CopyButton
│   │
│   ├── SystemStatusSection (EXISTING)
│   │   └── StatusCard
│   │       ├── CardHeader
│   │       ├── CardContent
│   │       └── Badge (status indicator)
│   │
│   ├── ServiceHealthSection (EXISTING)
│   │   └── ServiceGrid
│   │       └── ServiceCard (x5)
│   │           ├── CardHeader
│   │           │   ├── ServiceIcon
│   │           │   ├── ServiceName
│   │           │   └── HealthIndicator
│   │           └── CardContent
│   │               ├── StatusBadge
│   │               └── LatencyDisplay
│   │
│   ├── QuickStatsSection (EXISTING - ENHANCED)
│   │   └── StatsGrid
│   │       ├── StatCard (API Endpoint)
│   │       ├── StatCard (Dashboard URL)
│   │       ├── StatCard (Version)
│   │       └── StatCard (Mode)
│   │
│   └── ActivitySection (NEW - OPTIONAL)
│       ├── SectionHeader
│       └── ActivityGrid
│           ├── ActivityCard (Recent Vectors)
│           ├── ActivityCard (Recent Queries)
│           └── ActivityCard (Storage Usage)
```

---

## 4. Component Specifications

### 4.1 Page Layout Components

#### 4.1.1 DashboardPage (Main Page Component)

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/app/page.tsx`

**Purpose:** Root page component managing data fetching and layout orchestration

**Props:** None (Route component)

**State Management:**
```typescript
// React Query for health data
const { data: health, isLoading, error } = useQuery({
  queryKey: ['health'],
  queryFn: () => apiClient.getHealth(),
  refetchInterval: 5000,
})
```

**Responsibilities:**
- Fetch health data via React Query
- Handle loading and error states
- Orchestrate layout sections
- Pass health data to child components

**Exports:**
```typescript
export default function DashboardPage(): JSX.Element
```

---

### 4.2 Hero Section Components

#### 4.2.1 HeroSection

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/homepage/HeroSection.tsx`

**Purpose:** Marketing-focused hero section introducing ZeroDB Local

**Props:**
```typescript
interface HeroSectionProps {
  className?: string
}
```

**Structure:**
```tsx
<section
  className="py-16 px-4 text-center bg-gradient-to-br from-blue-50 to-indigo-50"
  aria-labelledby="hero-heading"
>
  <HeroHeading />
  <HeroDescription />
  <HeroActions />
</section>
```

**Accessibility:**
- Semantic `<section>` element
- `aria-labelledby` linking to heading
- Focus management for CTA buttons

---

#### 4.2.2 HeroHeading

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/homepage/HeroHeading.tsx`

**Purpose:** Display main tagline

**Props:**
```typescript
interface HeroHeadingProps {
  title?: string
  subtitle?: string
  className?: string
}
```

**Default Content:**
```
Title: "Self-Hosted AI Database"
Subtitle: "Zero API Costs • Full Privacy • Offline Development"
```

**Implementation:**
```tsx
<div className="max-w-4xl mx-auto mb-8">
  <h1
    id="hero-heading"
    className="text-5xl md:text-6xl font-bold text-gray-900 mb-4"
  >
    {title || "Self-Hosted AI Database"}
  </h1>
  <p className="text-xl md:text-2xl text-gray-600">
    {subtitle || "Zero API Costs • Full Privacy • Offline Development"}
  </p>
</div>
```

---

#### 4.2.3 HeroActions

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/homepage/HeroActions.tsx`

**Purpose:** Primary and secondary CTAs

**Props:**
```typescript
interface HeroActionsProps {
  primaryLabel?: string
  primaryHref?: string
  secondaryLabel?: string
  secondaryHref?: string
  onPrimaryClick?: () => void
  onSecondaryClick?: () => void
  className?: string
}
```

**Implementation:**
```tsx
import { Button } from '@/components/ui/button'
import { BookOpen, Rocket } from 'lucide-react'

<div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
  <Button
    size="lg"
    onClick={onPrimaryClick}
    aria-label={primaryLabel}
    className="text-lg px-8 py-6"
  >
    <Rocket className="mr-2 h-5 w-5" aria-hidden="true" />
    {primaryLabel || "Quick Start Guide"}
  </Button>

  <Button
    size="lg"
    variant="outline"
    onClick={onSecondaryClick}
    aria-label={secondaryLabel}
    className="text-lg px-8 py-6"
  >
    <BookOpen className="mr-2 h-5 w-5" aria-hidden="true" />
    {secondaryLabel || "View Documentation"}
  </Button>
</div>
```

---

### 4.3 Features Section Components

#### 4.3.1 FeaturesSection

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/homepage/FeaturesSection.tsx`

**Purpose:** Highlight key benefits of ZeroDB Local

**Props:**
```typescript
interface FeaturesSectionProps {
  features?: Feature[]
  className?: string
}

interface Feature {
  id: string
  icon: React.ReactNode
  title: string
  description: string
  iconColor?: string
}
```

**Default Features:**
```typescript
const DEFAULT_FEATURES: Feature[] = [
  {
    id: 'zero-costs',
    icon: <DollarSign className="h-8 w-8" />,
    title: 'Zero API Costs',
    description: 'Run vector embeddings locally with BAAI BGE models. No external API calls, no usage fees.',
    iconColor: 'text-green-600'
  },
  {
    id: 'full-privacy',
    icon: <Lock className="h-8 w-8" />,
    title: 'Full Privacy Control',
    description: 'Your data never leaves your machine. Complete control over your AI infrastructure.',
    iconColor: 'text-blue-600'
  },
  {
    id: 'offline-dev',
    icon: <Wifi className="h-8 w-8" />,
    title: 'Offline Development',
    description: 'Develop without internet connectivity. Perfect for secure environments and travel.',
    iconColor: 'text-purple-600'
  }
]
```

**Implementation:**
```tsx
<section
  className="py-12 px-4"
  aria-labelledby="features-heading"
>
  <h2
    id="features-heading"
    className="text-3xl font-bold text-center mb-10"
  >
    Why Choose ZeroDB Local?
  </h2>
  <FeatureGrid features={features || DEFAULT_FEATURES} />
</section>
```

---

#### 4.3.2 FeatureCard

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/homepage/FeatureCard.tsx`

**Purpose:** Individual feature highlight card

**Props:**
```typescript
interface FeatureCardProps {
  icon: React.ReactNode
  title: string
  description: string
  iconColor?: string
  className?: string
}
```

**Implementation:**
```tsx
import { Card, CardHeader, CardContent, CardTitle, CardDescription } from '@/components/ui/card'

<Card
  className={cn("hover:shadow-lg transition-shadow duration-200", className)}
  role="article"
  aria-labelledby={`feature-${title.toLowerCase().replace(/\s+/g, '-')}`}
>
  <CardHeader className="text-center">
    <div
      className={cn("mx-auto mb-4 p-3 bg-gray-100 rounded-full w-fit", iconColor)}
      aria-hidden="true"
    >
      {icon}
    </div>
    <CardTitle
      id={`feature-${title.toLowerCase().replace(/\s+/g, '-')}`}
      className="text-xl"
    >
      {title}
    </CardTitle>
  </CardHeader>
  <CardContent>
    <CardDescription className="text-center text-base">
      {description}
    </CardDescription>
  </CardContent>
</Card>
```

---

### 4.4 Code Examples Section Components

#### 4.4.1 CodeExamplesSection

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/homepage/CodeExamplesSection.tsx`

**Purpose:** Tabbed code examples for multiple languages

**Props:**
```typescript
interface CodeExamplesSectionProps {
  examples?: CodeExample[]
  defaultTab?: string
  className?: string
}

interface CodeExample {
  language: string
  label: string
  code: string
  description?: string
}
```

**Default Examples:**
```typescript
const DEFAULT_EXAMPLES: CodeExample[] = [
  {
    language: 'python',
    label: 'Python',
    code: `import requests

# Store a vector embedding
response = requests.post(
    "http://localhost:8000/v1/projects/my-project/database/vectors",
    json={
        "vector": [0.1, 0.2, 0.3, ...],
        "metadata": {"source": "document.pdf"}
    }
)

print(response.json())`,
    description: 'Python SDK example for storing vector embeddings'
  },
  {
    language: 'javascript',
    label: 'JavaScript',
    code: `const response = await fetch(
  'http://localhost:8000/v1/projects/my-project/database/vectors',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      vector: [0.1, 0.2, 0.3, ...],
      metadata: { source: 'document.pdf' }
    })
  }
);

const data = await response.json();
console.log(data);`,
    description: 'JavaScript fetch API example'
  },
  {
    language: 'bash',
    label: 'cURL',
    code: `curl -X POST http://localhost:8000/v1/projects/my-project/database/vectors \\
  -H "Content-Type: application/json" \\
  -d '{
    "vector": [0.1, 0.2, 0.3],
    "metadata": {"source": "document.pdf"}
  }'`,
    description: 'cURL command for API testing'
  }
]
```

**Implementation:**
```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CodeBlock } from '@/components/homepage/CodeBlock'

<section
  className="py-12 px-4 bg-gray-50"
  aria-labelledby="code-examples-heading"
>
  <div className="max-w-4xl mx-auto">
    <h2
      id="code-examples-heading"
      className="text-3xl font-bold text-center mb-8"
    >
      Get Started in Seconds
    </h2>

    <Tabs defaultValue={defaultTab || 'python'} className="w-full">
      <TabsList
        className="grid w-full grid-cols-3 mb-6"
        aria-label="Programming language examples"
      >
        {examples.map(example => (
          <TabsTrigger
            key={example.language}
            value={example.language}
            aria-label={`${example.label} example`}
          >
            {example.label}
          </TabsTrigger>
        ))}
      </TabsList>

      {examples.map(example => (
        <TabsContent
          key={example.language}
          value={example.language}
          role="tabpanel"
          aria-labelledby={`${example.language}-tab`}
        >
          <CodeBlock
            code={example.code}
            language={example.language}
            description={example.description}
          />
        </TabsContent>
      ))}
    </Tabs>
  </div>
</section>
```

---

#### 4.4.2 CodeBlock

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/homepage/CodeBlock.tsx`

**Purpose:** Syntax-highlighted code display with copy functionality

**Props:**
```typescript
interface CodeBlockProps {
  code: string
  language: string
  description?: string
  showLineNumbers?: boolean
  className?: string
}
```

**Dependencies:**
```json
{
  "react-syntax-highlighter": "^15.5.0",
  "@types/react-syntax-highlighter": "^15.5.11"
}
```

**Implementation:**
```tsx
'use client'

import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism'
import { Button } from '@/components/ui/button'
import { Check, Copy } from 'lucide-react'
import { Card } from '@/components/ui/card'

export function CodeBlock({
  code,
  language,
  description,
  showLineNumbers = true,
  className
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Card className={cn("overflow-hidden", className)}>
      <div className="flex justify-between items-center px-4 py-2 bg-gray-800 border-b border-gray-700">
        <span className="text-sm text-gray-300">
          {description || `${language} example`}
        </span>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleCopy}
          className="text-gray-300 hover:text-white hover:bg-gray-700"
          aria-label={copied ? 'Copied to clipboard' : 'Copy code to clipboard'}
        >
          {copied ? (
            <>
              <Check className="h-4 w-4 mr-1" aria-hidden="true" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-4 w-4 mr-1" aria-hidden="true" />
              Copy
            </>
          )}
        </Button>
      </div>
      <div className="relative">
        <SyntaxHighlighter
          language={language}
          style={vscDarkPlus}
          showLineNumbers={showLineNumbers}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            fontSize: '14px',
            padding: '1rem'
          }}
          codeTagProps={{
            style: { fontFamily: 'var(--font-mono, monospace)' }
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </Card>
  )
}
```

---

### 4.5 Service Monitoring Components (Enhanced Existing)

#### 4.5.1 SystemStatusSection

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/monitoring/SystemStatusSection.tsx`

**Purpose:** Overall system health overview (REFACTORED FROM EXISTING)

**Props:**
```typescript
interface SystemStatusSectionProps {
  health: HealthStatus | undefined
  className?: string
}
```

**Implementation:**
```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export function SystemStatusSection({ health, className }: SystemStatusSectionProps) {
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'healthy': return 'success'
      case 'degraded': return 'warning'
      default: return 'destructive'
    }
  }

  return (
    <section
      className={cn("mb-8", className)}
      aria-labelledby="system-status-heading"
    >
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle id="system-status-heading">
                System Status
              </CardTitle>
              <CardDescription>
                Overall health of all services
              </CardDescription>
            </div>
            <Badge
              variant={getStatusVariant(health?.status || 'unhealthy')}
              aria-label={`System status: ${health?.status || 'unhealthy'}`}
            >
              {health?.status?.toUpperCase()}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-gray-600">
            <span aria-live="polite">
              {health?.summary.healthy} of {health?.summary.total} services operational
            </span>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
```

---

#### 4.5.2 ServiceHealthSection

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/monitoring/ServiceHealthSection.tsx`

**Purpose:** Grid of individual service health cards (REFACTORED FROM EXISTING)

**Props:**
```typescript
interface ServiceHealthSectionProps {
  health: HealthStatus | undefined
  className?: string
}
```

**Implementation:**
```tsx
import { ServiceCard } from './ServiceCard'
import { Database, HardDrive, Activity } from 'lucide-react'

const SERVICE_CONFIG = [
  {
    name: 'PostgreSQL',
    key: 'postgres' as const,
    icon: <Database className="h-5 w-5" />,
    description: 'Primary database'
  },
  {
    name: 'Qdrant',
    key: 'qdrant' as const,
    icon: <Activity className="h-5 w-5" />,
    description: 'Vector search engine'
  },
  {
    name: 'MinIO',
    key: 'minio' as const,
    icon: <HardDrive className="h-5 w-5" />,
    description: 'Object storage'
  },
  {
    name: 'RedPanda',
    key: 'redpanda' as const,
    icon: <Activity className="h-5 w-5" />,
    description: 'Event streaming'
  },
  {
    name: 'Embeddings',
    key: 'embeddings' as const,
    icon: <Activity className="h-5 w-5" />,
    description: 'Local embeddings (BAAI BGE)'
  }
]

export function ServiceHealthSection({ health, className }: ServiceHealthSectionProps) {
  return (
    <section
      className={cn("mb-8", className)}
      aria-labelledby="service-health-heading"
    >
      <h2
        id="service-health-heading"
        className="text-2xl font-bold mb-4"
      >
        Service Health
      </h2>
      <div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        role="list"
        aria-label="Service health status"
      >
        {SERVICE_CONFIG.map(service => (
          <ServiceCard
            key={service.key}
            name={service.name}
            status={health?.services[service.key].status || 'unhealthy'}
            latency={health?.services[service.key].latency_ms}
            icon={service.icon}
            description={service.description}
            error={health?.services[service.key].error}
          />
        ))}
      </div>
    </section>
  )
}
```

---

#### 4.5.3 ServiceCard

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/monitoring/ServiceCard.tsx`

**Purpose:** Individual service health indicator (ENHANCED FROM EXISTING)

**Props:**
```typescript
interface ServiceCardProps {
  name: string
  status: 'healthy' | 'unhealthy'
  latency?: number
  icon: React.ReactNode
  description: string
  error?: string
  className?: string
}
```

**Implementation:**
```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export function ServiceCard({
  name,
  status,
  latency,
  icon,
  description,
  error,
  className
}: ServiceCardProps) {
  const isHealthy = status === 'healthy'
  const cardId = `service-${name.toLowerCase().replace(/\s+/g, '-')}`

  return (
    <Card
      className={cn(
        "transition-colors duration-200",
        isHealthy ? 'border-green-200 hover:border-green-300' : 'border-red-200 hover:border-red-300',
        className
      )}
      role="listitem"
      aria-labelledby={cardId}
    >
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div aria-hidden="true">{icon}</div>
            <CardTitle id={cardId} className="text-lg">
              {name}
            </CardTitle>
          </div>
          {isHealthy ? (
            <CheckCircle
              className="h-5 w-5 text-green-600"
              aria-label="Service is healthy"
            />
          ) : (
            <AlertCircle
              className="h-5 w-5 text-red-600"
              aria-label="Service is unhealthy"
            />
          )}
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <Badge
            variant={isHealthy ? 'success' : 'destructive'}
            aria-label={`Status: ${status}`}
          >
            {status}
          </Badge>
          {latency !== undefined && (
            <span
              className="text-xs text-gray-500"
              aria-label={`Response time: ${latency} milliseconds`}
            >
              {latency}ms
            </span>
          )}
        </div>
        {error && (
          <p
            className="text-xs text-red-600 mt-2"
            role="alert"
            aria-live="polite"
          >
            {error}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
```

---

### 4.6 Quick Stats Components (Enhanced)

#### 4.6.1 QuickStatsSection

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/stats/QuickStatsSection.tsx`

**Purpose:** Display key system information (REFACTORED FROM EXISTING)

**Props:**
```typescript
interface QuickStatsSectionProps {
  stats?: QuickStat[]
  className?: string
}

interface QuickStat {
  label: string
  value: string
  description: string
  icon?: React.ReactNode
}
```

**Default Stats:**
```typescript
const DEFAULT_STATS: QuickStat[] = [
  {
    label: 'API Endpoint',
    value: 'localhost:8000',
    description: 'Local development',
    icon: <Server className="h-5 w-5" />
  },
  {
    label: 'Dashboard',
    value: 'localhost:3000',
    description: 'This interface',
    icon: <Monitor className="h-5 w-5" />
  },
  {
    label: 'Version',
    value: '1.0.0',
    description: 'ZeroLocal',
    icon: <Package className="h-5 w-5" />
  },
  {
    label: 'Mode',
    value: 'Local',
    description: 'No API costs',
    icon: <Zap className="h-5 w-5" />
  }
]
```

**Implementation:**
```tsx
import { StatCard } from './StatCard'

export function QuickStatsSection({ stats, className }: QuickStatsSectionProps) {
  const displayStats = stats || DEFAULT_STATS

  return (
    <section
      className={cn("mb-8", className)}
      aria-labelledby="quick-stats-heading"
    >
      <h2
        id="quick-stats-heading"
        className="text-2xl font-bold mb-4"
      >
        Quick Stats
      </h2>
      <div
        className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4"
        role="list"
        aria-label="System statistics"
      >
        {displayStats.map(stat => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>
    </section>
  )
}
```

---

#### 4.6.2 StatCard

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/stats/StatCard.tsx`

**Purpose:** Individual stat display card

**Props:**
```typescript
interface StatCardProps {
  label: string
  value: string
  description: string
  icon?: React.ReactNode
  className?: string
}
```

**Implementation:**
```tsx
import { Card, CardContent, CardDescription, CardHeader } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export function StatCard({ label, value, description, icon, className }: StatCardProps) {
  const cardId = `stat-${label.toLowerCase().replace(/\s+/g, '-')}`

  return (
    <Card
      className={cn("hover:shadow-md transition-shadow duration-200", className)}
      role="listitem"
      aria-labelledby={cardId}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardDescription id={cardId}>{label}</CardDescription>
          {icon && (
            <div className="text-gray-500" aria-hidden="true">
              {icon}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold mb-1" aria-label={`${label}: ${value}`}>
          {value}
        </div>
        <p className="text-xs text-gray-500">{description}</p>
      </CardContent>
    </Card>
  )
}
```

---

### 4.7 Activity Section Components (Optional)

#### 4.7.1 ActivitySection

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/activity/ActivitySection.tsx`

**Purpose:** Display recent activity metrics (FUTURE ENHANCEMENT)

**Props:**
```typescript
interface ActivitySectionProps {
  projectId?: string
  className?: string
}
```

**Implementation:**
```tsx
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import { ActivityCard } from './ActivityCard'

export function ActivitySection({ projectId, className }: ActivitySectionProps) {
  const { data: stats } = useQuery({
    queryKey: ['project-stats', projectId],
    queryFn: () => apiClient.getProjectStats(projectId || 'default'),
    enabled: !!projectId,
  })

  if (!stats) return null

  return (
    <section
      className={cn("py-8", className)}
      aria-labelledby="activity-heading"
    >
      <h2
        id="activity-heading"
        className="text-2xl font-bold mb-4"
      >
        Recent Activity
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ActivityCard
          title="Vector Embeddings"
          value={stats.vector_count}
          description="Total stored"
          trend="+12% this week"
        />
        <ActivityCard
          title="Memory Entries"
          value={stats.memory_count}
          description="Conversation history"
          trend="+8% this week"
        />
        <ActivityCard
          title="Storage Used"
          value={`${(stats.storage_bytes / 1024 / 1024).toFixed(2)} MB`}
          description="Total storage"
          trend="+15% this week"
        />
      </div>
    </section>
  )
}
```

---

### 4.8 Utility Components

#### 4.8.1 LoadingState

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/common/LoadingState.tsx`

**Purpose:** Reusable loading indicator

**Props:**
```typescript
interface LoadingStateProps {
  message?: string
  className?: string
}
```

**Implementation:**
```tsx
export function LoadingState({ message, className }: LoadingStateProps) {
  return (
    <div
      className={cn("flex items-center justify-center h-64", className)}
      role="status"
      aria-live="polite"
      aria-label={message || "Loading content"}
    >
      <div className="text-center">
        <div
          className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto mb-4"
          aria-hidden="true"
        />
        {message && (
          <p className="text-gray-600">{message}</p>
        )}
      </div>
    </div>
  )
}
```

---

#### 4.8.2 ErrorState

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/components/common/ErrorState.tsx`

**Purpose:** Reusable error display

**Props:**
```typescript
interface ErrorStateProps {
  title?: string
  message: string
  retry?: () => void
  className?: string
}
```

**Implementation:**
```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { AlertCircle, RefreshCw } from 'lucide-react'

export function ErrorState({
  title = "Connection Error",
  message,
  retry,
  className
}: ErrorStateProps) {
  return (
    <Card
      className={cn("border-red-200 bg-red-50", className)}
      role="alert"
      aria-live="assertive"
    >
      <CardHeader>
        <CardTitle className="text-red-800 flex items-center gap-2">
          <AlertCircle className="h-5 w-5" aria-hidden="true" />
          {title}
        </CardTitle>
        <CardDescription className="text-red-600">
          Unable to connect to ZeroDB API at localhost:8000
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-red-700 mb-4">{message}</p>
        {retry && (
          <Button
            onClick={retry}
            variant="outline"
            className="border-red-300 text-red-700 hover:bg-red-100"
            aria-label="Retry connection"
          >
            <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
            Retry Connection
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
```

---

## 5. Data Flow Architecture

### 5.1 Data Fetching Strategy

```typescript
// Health data fetching (existing pattern)
const { data: health, isLoading, error, refetch } = useQuery({
  queryKey: ['health'],
  queryFn: () => apiClient.getHealth(),
  refetchInterval: 5000,        // Auto-refresh every 5 seconds
  staleTime: 4000,               // Consider fresh for 4 seconds
  retry: 3,                      // Retry failed requests 3 times
  retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000)
})
```

### 5.2 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       DashboardPage                          │
│  (page.tsx - Data Orchestration Layer)                      │
│                                                               │
│  useQuery('health') ──> apiClient.getHealth()               │
│         │                       │                             │
│         │                       ▼                             │
│         │          axios.get('/health')                      │
│         │                       │                             │
│         ▼                       ▼                             │
│  {health, isLoading, error}  HTTP Response                  │
└────────────┬────────────────────────────────────────────────┘
             │
             │ Props Flow
             │
             ├──────────────────┬──────────────────┬──────────────────┐
             ▼                  ▼                  ▼                  ▼
     ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
     │  HeroSection  │  │FeaturesSection│  │CodeExamples   │  │SystemStatus   │
     │  (static)     │  │   (static)    │  │Section        │  │Section        │
     │               │  │               │  │   (static)    │  │               │
     │  No props     │  │  No props     │  │  No props     │  │  health prop  │
     └───────────────┘  └───────────────┘  └───────────────┘  └───────┬───────┘
                                                                       │
                                                                       ▼
                                                            ┌──────────────────┐
                                                            │ServiceHealthGrid │
                                                            │                  │
                                                            │ health.services  │
                                                            └────────┬─────────┘
                                                                     │
                                                         ┌───────────┴───────────┐
                                                         ▼                       ▼
                                                   ServiceCard (×5)      ServiceCard
                                                   status, latency       (per service)
```

### 5.3 State Management

**React Query Cache:**
```typescript
// Centralized cache configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true,    // Refetch on tab focus
      refetchOnReconnect: true,      // Refetch on network reconnect
      staleTime: 4000,               // 4 seconds
      cacheTime: 5 * 60 * 1000,      // 5 minutes
    },
  },
})
```

**Component State:**
- Minimal local state (e.g., `copied` state in CodeBlock)
- No global state management needed (Redux, Zustand, etc.)
- All server state managed by React Query

---

## 6. File Structure

```
/Users/aideveloper/core/zerodb-local/dashboard/
├── app/
│   ├── page.tsx                          # Main dashboard page (ENHANCED)
│   ├── layout.tsx                        # Root layout
│   └── globals.css                       # Global styles
│
├── components/
│   ├── homepage/                         # NEW: Homepage-specific components
│   │   ├── HeroSection.tsx
│   │   ├── HeroHeading.tsx
│   │   ├── HeroActions.tsx
│   │   ├── FeaturesSection.tsx
│   │   ├── FeatureCard.tsx
│   │   ├── CodeExamplesSection.tsx
│   │   └── CodeBlock.tsx
│   │
│   ├── monitoring/                       # REFACTORED: Service monitoring
│   │   ├── SystemStatusSection.tsx
│   │   ├── ServiceHealthSection.tsx
│   │   └── ServiceCard.tsx
│   │
│   ├── stats/                            # REFACTORED: Statistics components
│   │   ├── QuickStatsSection.tsx
│   │   └── StatCard.tsx
│   │
│   ├── activity/                         # NEW: Activity components (optional)
│   │   ├── ActivitySection.tsx
│   │   └── ActivityCard.tsx
│   │
│   ├── common/                           # NEW: Shared utility components
│   │   ├── LoadingState.tsx
│   │   └── ErrorState.tsx
│   │
│   └── ui/                               # EXISTING: shadcn/ui primitives
│       ├── card.tsx
│       ├── badge.tsx
│       ├── button.tsx
│       ├── tabs.tsx
│       └── ...
│
├── services/
│   └── api-client.ts                     # EXISTING: API client
│
├── types/
│   └── index.ts                          # EXISTING: TypeScript types
│
├── lib/
│   └── utils.ts                          # EXISTING: Utility functions (cn)
│
└── tests/
    ├── components/
    │   ├── homepage/                     # NEW: Homepage component tests
    │   │   ├── HeroSection.test.tsx
    │   │   ├── FeaturesSection.test.tsx
    │   │   ├── CodeExamplesSection.test.tsx
    │   │   └── CodeBlock.test.tsx
    │   │
    │   ├── monitoring/                   # NEW: Monitoring component tests
    │   │   ├── SystemStatusSection.test.tsx
    │   │   ├── ServiceHealthSection.test.tsx
    │   │   └── ServiceCard.test.tsx
    │   │
    │   └── stats/                        # NEW: Stats component tests
    │       ├── QuickStatsSection.test.tsx
    │       └── StatCard.test.tsx
    │
    └── setup.ts                          # EXISTING: Test setup
```

---

## 7. Integration Strategy

### 7.1 Migration Approach

**Phase 1: Component Extraction (No Breaking Changes)**
```
1. Extract existing inline components to separate files:
   - Move ServiceCard to components/monitoring/ServiceCard.tsx
   - Move helper functions to lib/utils.ts

2. Create new section wrapper components:
   - SystemStatusSection (wraps existing Card)
   - ServiceHealthSection (wraps existing grid)
   - QuickStatsSection (wraps existing stats grid)

3. Update page.tsx imports:
   - Import section components
   - Replace inline JSX with component calls
   - Verify no visual changes
```

**Phase 2: Add New Sections (Additive Only)**
```
1. Implement HeroSection with all sub-components
2. Implement FeaturesSection with FeatureCard
3. Implement CodeExamplesSection with CodeBlock
4. Add utility components (LoadingState, ErrorState)

5. Import and render new sections in page.tsx:
   - Insert HeroSection at top
   - Insert FeaturesSection after hero
   - Insert CodeExamplesSection after features
   - Keep existing sections below (no changes)
```

**Phase 3: Testing & Refinement**
```
1. Write unit tests for all new components
2. Write integration tests for page.tsx
3. Accessibility audit with axe-core
4. Performance testing (Lighthouse)
5. Responsive design testing (multiple viewports)
```

### 7.2 Updated page.tsx Structure

```tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'

// New components
import { HeroSection } from '@/components/homepage/HeroSection'
import { FeaturesSection } from '@/components/homepage/FeaturesSection'
import { CodeExamplesSection } from '@/components/homepage/CodeExamplesSection'

// Refactored components
import { SystemStatusSection } from '@/components/monitoring/SystemStatusSection'
import { ServiceHealthSection } from '@/components/monitoring/ServiceHealthSection'
import { QuickStatsSection } from '@/components/stats/QuickStatsSection'

// Utility components
import { LoadingState } from '@/components/common/LoadingState'
import { ErrorState } from '@/components/common/ErrorState'

export default function DashboardPage() {
  const { data: health, isLoading, error, refetch } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 5000,
  })

  // Loading state
  if (isLoading) {
    return (
      <div className="p-8">
        <LoadingState message="Connecting to ZeroDB..." />
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="p-8">
        <ErrorState
          message={error?.message || 'Unknown error'}
          retry={refetch}
        />
      </div>
    )
  }

  // Main content
  return (
    <div className="min-h-screen bg-white">
      {/* Hero Section - NEW */}
      <HeroSection />

      {/* Features Section - NEW */}
      <FeaturesSection />

      {/* Code Examples Section - NEW */}
      <CodeExamplesSection />

      {/* Existing sections - REFACTORED */}
      <div className="p-8">
        <SystemStatusSection health={health} className="mb-8" />
        <ServiceHealthSection health={health} className="mb-8" />
        <QuickStatsSection className="mb-8" />
      </div>
    </div>
  )
}
```

---

## 8. TypeScript Type Definitions

### 8.1 New Types to Add

**File:** `/Users/aideveloper/core/zerodb-local/dashboard/types/homepage.ts`

```typescript
// Hero Section Types
export interface HeroSectionProps {
  className?: string
}

export interface HeroHeadingProps {
  title?: string
  subtitle?: string
  className?: string
}

export interface HeroActionsProps {
  primaryLabel?: string
  primaryHref?: string
  secondaryLabel?: string
  secondaryHref?: string
  onPrimaryClick?: () => void
  onSecondaryClick?: () => void
  className?: string
}

// Features Section Types
export interface Feature {
  id: string
  icon: React.ReactNode
  title: string
  description: string
  iconColor?: string
}

export interface FeaturesSectionProps {
  features?: Feature[]
  className?: string
}

export interface FeatureCardProps {
  icon: React.ReactNode
  title: string
  description: string
  iconColor?: string
  className?: string
}

// Code Examples Types
export interface CodeExample {
  language: string
  label: string
  code: string
  description?: string
}

export interface CodeExamplesSectionProps {
  examples?: CodeExample[]
  defaultTab?: string
  className?: string
}

export interface CodeBlockProps {
  code: string
  language: string
  description?: string
  showLineNumbers?: boolean
  className?: string
}

// Stats Types
export interface QuickStat {
  label: string
  value: string
  description: string
  icon?: React.ReactNode
}

export interface QuickStatsSectionProps {
  stats?: QuickStat[]
  className?: string
}

export interface StatCardProps {
  label: string
  value: string
  description: string
  icon?: React.ReactNode
  className?: string
}

// Activity Types (Future)
export interface ActivityMetric {
  title: string
  value: number | string
  description: string
  trend?: string
  trendDirection?: 'up' | 'down' | 'neutral'
}

export interface ActivitySectionProps {
  projectId?: string
  className?: string
}

export interface ActivityCardProps {
  title: string
  value: number | string
  description: string
  trend?: string
  trendDirection?: 'up' | 'down' | 'neutral'
  className?: string
}

// Common Component Types
export interface LoadingStateProps {
  message?: string
  className?: string
}

export interface ErrorStateProps {
  title?: string
  message: string
  retry?: () => void
  className?: string
}
```

### 8.2 Type Exports

**Update:** `/Users/aideveloper/core/zerodb-local/dashboard/types/index.ts`

```typescript
// Add to existing exports
export * from './homepage'
```

---

## 9. Testing Strategy

### 9.1 Unit Testing Requirements

**Testing Framework:** Vitest + React Testing Library

**Coverage Requirements:**
- Line coverage: ≥ 80%
- Branch coverage: ≥ 75%
- Function coverage: ≥ 80%

**Test Categories:**

1. **Component Rendering Tests**
   - Verify component renders without crashing
   - Check default props rendering
   - Validate custom props rendering

2. **Accessibility Tests**
   - ARIA labels present
   - Semantic HTML structure
   - Keyboard navigation
   - Color contrast (automated with axe)

3. **Interaction Tests**
   - Button clicks
   - Tab switching
   - Copy-to-clipboard functionality

4. **Integration Tests**
   - Data fetching with mocked API
   - Error state handling
   - Loading state transitions

### 9.2 Example Test Files

#### HeroSection.test.tsx

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HeroSection } from '@/components/homepage/HeroSection'

describe('HeroSection', () => {
  it('renders default heading and subtitle', () => {
    render(<HeroSection />)

    expect(screen.getByText('Self-Hosted AI Database')).toBeInTheDocument()
    expect(screen.getByText(/Zero API Costs/i)).toBeInTheDocument()
  })

  it('renders CTA buttons', () => {
    render(<HeroSection />)

    expect(screen.getByRole('button', { name: /quick start guide/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /view documentation/i })).toBeInTheDocument()
  })

  it('has proper accessibility attributes', () => {
    render(<HeroSection />)

    const heading = screen.getByRole('heading', { level: 1 })
    expect(heading).toHaveAttribute('id', 'hero-heading')

    const section = screen.getByRole('region', { name: /self-hosted ai database/i })
    expect(section).toHaveAttribute('aria-labelledby', 'hero-heading')
  })
})
```

#### CodeBlock.test.tsx

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { CodeBlock } from '@/components/homepage/CodeBlock'

describe('CodeBlock', () => {
  const mockCode = 'console.log("Hello World")'

  it('renders code with syntax highlighting', () => {
    render(<CodeBlock code={mockCode} language="javascript" />)

    expect(screen.getByText(/console\.log/i)).toBeInTheDocument()
  })

  it('copies code to clipboard when copy button clicked', async () => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })

    render(<CodeBlock code={mockCode} language="javascript" />)

    const copyButton = screen.getByRole('button', { name: /copy code/i })
    fireEvent.click(copyButton)

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockCode)
      expect(screen.getByText('Copied')).toBeInTheDocument()
    })
  })

  it('shows line numbers when enabled', () => {
    const { container } = render(
      <CodeBlock code={mockCode} language="javascript" showLineNumbers={true} />
    )

    // react-syntax-highlighter adds line numbers to the rendered output
    const lineNumbers = container.querySelector('.linenumber')
    expect(lineNumbers).toBeInTheDocument()
  })
})
```

#### ServiceCard.test.tsx

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ServiceCard } from '@/components/monitoring/ServiceCard'
import { Database } from 'lucide-react'

describe('ServiceCard', () => {
  const defaultProps = {
    name: 'PostgreSQL',
    status: 'healthy' as const,
    icon: <Database />,
    description: 'Primary database',
  }

  it('renders healthy service correctly', () => {
    render(<ServiceCard {...defaultProps} latency={15} />)

    expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
    expect(screen.getByText('Primary database')).toBeInTheDocument()
    expect(screen.getByText('healthy')).toBeInTheDocument()
    expect(screen.getByText('15ms')).toBeInTheDocument()
    expect(screen.getByLabelText('Service is healthy')).toBeInTheDocument()
  })

  it('renders unhealthy service with error message', () => {
    render(
      <ServiceCard
        {...defaultProps}
        status="unhealthy"
        error="Connection refused"
      />
    )

    expect(screen.getByText('unhealthy')).toBeInTheDocument()
    expect(screen.getByText('Connection refused')).toBeInTheDocument()
    expect(screen.getByLabelText('Service is unhealthy')).toBeInTheDocument()
  })

  it('applies correct border color based on status', () => {
    const { container, rerender } = render(<ServiceCard {...defaultProps} />)

    let card = container.firstChild
    expect(card).toHaveClass('border-green-200')

    rerender(<ServiceCard {...defaultProps} status="unhealthy" />)
    card = container.firstChild
    expect(card).toHaveClass('border-red-200')
  })
})
```

---

## 10. Accessibility Compliance

### 10.1 WCAG 2.1 Level AA Requirements

**Semantic HTML:**
- Use `<section>`, `<article>`, `<nav>`, `<main>` appropriately
- Heading hierarchy (h1 → h2 → h3)
- Proper landmark regions

**ARIA Labels:**
- All interactive elements have accessible names
- Status updates use `aria-live` regions
- Icons have `aria-hidden="true"` (decorative) or `aria-label` (functional)

**Keyboard Navigation:**
- All interactive elements reachable via Tab
- Logical tab order
- Visible focus indicators
- Escape key closes modals/dropdowns

**Color Contrast:**
- Normal text: 4.5:1 minimum
- Large text (18pt+): 3:1 minimum
- Interactive elements: 3:1 minimum

**Screen Reader Support:**
- Meaningful alt text for images
- Form labels properly associated
- Error messages announced
- Loading states announced

### 10.2 Accessibility Testing Checklist

```typescript
// Add to vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'tests/',
      ],
    },
  },
})
```

**Automated Testing:**
```bash
# Install axe-core for accessibility testing
npm install --save-dev @axe-core/react vitest-axe
```

**Example Accessibility Test:**
```typescript
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'vitest-axe'
import { HeroSection } from '@/components/homepage/HeroSection'

expect.extend(toHaveNoViolations)

describe('HeroSection Accessibility', () => {
  it('should not have any accessibility violations', async () => {
    const { container } = render(<HeroSection />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
```

---

## 11. Performance Optimization

### 11.1 Bundle Size Optimization

**Code Splitting:**
```typescript
// Dynamic imports for large dependencies
import dynamic from 'next/dynamic'

// Lazy load syntax highlighter (reduces initial bundle)
const SyntaxHighlighter = dynamic(
  () => import('react-syntax-highlighter').then(mod => mod.Prism),
  { ssr: false, loading: () => <div>Loading...</div> }
)
```

**Tree Shaking:**
```typescript
// Import only needed icons (not entire library)
import { Database, Activity, HardDrive, CheckCircle, AlertCircle } from 'lucide-react'

// Instead of:
// import * as Icons from 'lucide-react'
```

### 11.2 Rendering Optimization

**React.memo for Pure Components:**
```typescript
import { memo } from 'react'

export const ServiceCard = memo(function ServiceCard({
  name,
  status,
  latency,
  icon,
  description
}: ServiceCardProps) {
  // Component implementation
})
```

**useMemo for Expensive Computations:**
```typescript
const serviceConfig = useMemo(() => {
  return SERVICE_CONFIG.map(service => ({
    ...service,
    status: health?.services[service.key].status || 'unhealthy'
  }))
}, [health])
```

### 11.3 Image Optimization

**Next.js Image Component:**
```typescript
import Image from 'next/image'

<Image
  src="/logo.png"
  alt="ZeroDB Local Logo"
  width={200}
  height={50}
  priority // For hero section images
/>
```

---

## 12. Risk Assessment

### 12.1 Technical Risks

**Risk 1: Bundle Size Increase**
- **Impact:** HIGH
- **Probability:** MEDIUM
- **Mitigation:**
  - Implement code splitting for syntax highlighter
  - Use dynamic imports for heavy components
  - Monitor bundle size with `next/bundle-analyzer`
  - Target: < 50KB gzipped increase

**Risk 2: Performance Regression**
- **Impact:** MEDIUM
- **Probability:** LOW
- **Mitigation:**
  - Use React.memo for pure components
  - Implement virtualization if needed for long lists
  - Lighthouse performance audits (target score > 90)
  - Monitor Web Vitals (LCP, FID, CLS)

**Risk 3: Accessibility Violations**
- **Impact:** HIGH
- **Probability:** LOW
- **Mitigation:**
  - Automated axe-core testing in CI/CD
  - Manual screen reader testing
  - Keyboard navigation testing
  - Regular accessibility audits

**Risk 4: API Compatibility**
- **Impact:** LOW
- **Probability:** LOW
- **Mitigation:**
  - No changes to existing API client
  - All new sections use static content
  - Maintain existing health data fetching pattern

### 12.2 User Experience Risks

**Risk 1: Information Overload**
- **Impact:** MEDIUM
- **Probability:** MEDIUM
- **Mitigation:**
  - Clear visual hierarchy with sections
  - Collapsible sections (future enhancement)
  - Progressive disclosure of details
  - User testing for feedback

**Risk 2: Mobile Responsiveness Issues**
- **Impact:** HIGH
- **Probability:** LOW
- **Mitigation:**
  - Mobile-first design approach
  - Test on multiple viewport sizes
  - Touch-friendly interactive elements (min 44x44px)
  - Responsive grid layouts

---

## 13. Implementation Roadmap

### Phase 1: Foundation (Week 1)

**Day 1-2: Component Extraction**
- [ ] Extract ServiceCard to separate file
- [ ] Create SystemStatusSection wrapper
- [ ] Create ServiceHealthSection wrapper
- [ ] Create QuickStatsSection wrapper
- [ ] Update page.tsx imports
- [ ] Verify no visual changes
- [ ] Write unit tests for extracted components

**Day 3-4: Common Components**
- [ ] Implement LoadingState component
- [ ] Implement ErrorState component
- [ ] Update page.tsx to use new utility components
- [ ] Write unit tests
- [ ] Accessibility testing

**Day 5: Testing & Documentation**
- [ ] Integration tests for page.tsx
- [ ] Update Storybook (if used)
- [ ] Code review
- [ ] Merge Phase 1

### Phase 2: Hero & Features (Week 2)

**Day 1-2: Hero Section**
- [ ] Implement HeroSection component
- [ ] Implement HeroHeading component
- [ ] Implement HeroActions component
- [ ] Add to page.tsx
- [ ] Write unit tests
- [ ] Accessibility testing

**Day 3-4: Features Section**
- [ ] Implement FeaturesSection component
- [ ] Implement FeatureCard component
- [ ] Define default features content
- [ ] Add to page.tsx
- [ ] Write unit tests
- [ ] Accessibility testing

**Day 5: Testing & Review**
- [ ] Visual regression testing
- [ ] Mobile responsiveness testing
- [ ] Performance testing (Lighthouse)
- [ ] Code review
- [ ] Merge Phase 2

### Phase 3: Code Examples (Week 3)

**Day 1-2: Code Examples Section**
- [ ] Install react-syntax-highlighter
- [ ] Implement CodeBlock component with copy functionality
- [ ] Implement CodeExamplesSection with tabs
- [ ] Define default code examples (Python, JS, cURL)

**Day 3: Integration**
- [ ] Add CodeExamplesSection to page.tsx
- [ ] Test tab switching
- [ ] Test copy-to-clipboard
- [ ] Mobile responsiveness testing

**Day 4-5: Testing & Optimization**
- [ ] Write unit tests
- [ ] Accessibility testing
- [ ] Bundle size analysis
- [ ] Implement code splitting if needed
- [ ] Code review
- [ ] Merge Phase 3

### Phase 4: Polish & Launch (Week 4)

**Day 1-2: Final Testing**
- [ ] End-to-end testing
- [ ] Cross-browser testing
- [ ] Performance optimization
- [ ] Accessibility audit (axe-core)

**Day 3: Documentation**
- [ ] Update component documentation
- [ ] Add JSDoc comments
- [ ] Update README
- [ ] Create usage examples

**Day 4: Deployment**
- [ ] Final code review
- [ ] Merge to main branch
- [ ] Deploy to production
- [ ] Monitor for issues

**Day 5: Post-Launch**
- [ ] User feedback collection
- [ ] Performance monitoring
- [ ] Bug fixes if needed
- [ ] Plan future enhancements

### Optional Phase 5: Activity Section (Future)

**When:** After core features stable
- [ ] Design activity metrics API
- [ ] Implement ActivitySection component
- [ ] Implement ActivityCard component
- [ ] Add data fetching logic
- [ ] Write tests
- [ ] Deploy as feature flag

---

## 14. Success Metrics

### 14.1 Performance Metrics

| Metric | Target | Current Baseline | Measurement Tool |
|--------|--------|------------------|------------------|
| Initial Load Time | < 2s | TBD | Lighthouse |
| Largest Contentful Paint (LCP) | < 2.5s | TBD | Web Vitals |
| First Input Delay (FID) | < 100ms | TBD | Web Vitals |
| Cumulative Layout Shift (CLS) | < 0.1 | TBD | Web Vitals |
| Bundle Size Increase | < 50KB gzipped | 0KB (baseline) | webpack-bundle-analyzer |
| Lighthouse Performance Score | > 90 | TBD | Lighthouse |

### 14.2 Accessibility Metrics

| Metric | Target | Measurement Tool |
|--------|--------|------------------|
| WCAG 2.1 Level AA Compliance | 100% | axe-core |
| Keyboard Navigation | 100% functional | Manual testing |
| Screen Reader Compatibility | No blockers | NVDA/JAWS testing |
| Color Contrast Ratios | All pass (4.5:1+) | Contrast checker |

### 14.3 Code Quality Metrics

| Metric | Target | Measurement Tool |
|--------|--------|------------------|
| Test Coverage (Lines) | ≥ 80% | Vitest coverage |
| Test Coverage (Branches) | ≥ 75% | Vitest coverage |
| Test Coverage (Functions) | ≥ 80% | Vitest coverage |
| TypeScript Strict Mode | Enabled | tsconfig.json |
| ESLint Errors | 0 | ESLint |
| Component Reusability | > 80% | Code review |

### 14.4 User Experience Metrics (Post-Launch)

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Time to First Interaction | < 3s | User testing |
| User Satisfaction Score | > 4.5/5 | Survey |
| Mobile Usability Score | > 90 | Google Mobile-Friendly Test |
| Bounce Rate | < 30% | Analytics (if available) |

---

## 15. Rollback Strategy

### 15.1 Version Control Strategy

**Git Branching:**
```bash
main (production)
  ├── feature/homepage-phase-1-extraction
  ├── feature/homepage-phase-2-hero-features
  ├── feature/homepage-phase-3-code-examples
  └── feature/homepage-phase-4-polish
```

**Merge Strategy:**
- Each phase is a separate PR
- Require code review approval
- Require passing CI/CD checks
- Merge only after successful testing

### 15.2 Rollback Plan

**If Critical Issues Arise:**

1. **Immediate Rollback (< 5 minutes):**
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

2. **Partial Rollback (Remove Specific Section):**
   ```tsx
   // In page.tsx, comment out problematic section
   {/* <HeroSection /> */}
   ```

3. **Feature Flag (Future Enhancement):**
   ```typescript
   const FEATURE_FLAGS = {
     showHeroSection: process.env.NEXT_PUBLIC_SHOW_HERO === 'true',
     showCodeExamples: process.env.NEXT_PUBLIC_SHOW_CODE_EXAMPLES === 'true',
   }

   {FEATURE_FLAGS.showHeroSection && <HeroSection />}
   ```

### 15.3 Monitoring & Alerts

**Error Tracking:**
- Implement error boundary for new sections
- Log errors to console (development)
- Integrate with error tracking service (production - future)

**Example Error Boundary:**
```typescript
'use client'

import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback: ReactNode
}

interface State {
  hasError: boolean
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Component error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback
    }

    return this.props.children
  }
}

// Usage in page.tsx
<ErrorBoundary fallback={<ErrorState message="Failed to load hero section" />}>
  <HeroSection />
</ErrorBoundary>
```

---

## 16. Future Enhancements

### 16.1 Planned Enhancements (Post-MVP)

1. **Activity Section with Real Data**
   - Integrate with backend analytics API
   - Display charts/graphs for trends
   - Clickable cards linking to detailed views

2. **Dark Mode Support**
   - Theme toggle in navigation
   - Persistent theme preference
   - Dark mode optimized code syntax highlighting

3. **Interactive Service Status**
   - Click service card to view detailed logs
   - Real-time WebSocket updates
   - Service restart/management actions

4. **Customizable Dashboard**
   - Drag-and-drop section reordering
   - Toggle section visibility
   - Save preferences to local storage

5. **Onboarding Tour**
   - First-time user walkthrough
   - Feature highlights
   - Quick start wizard

### 16.2 Technical Debt Considerations

- **Component Library Migration:** Consider migrating from shadcn/ui components to a more mature library if needed (e.g., Radix UI directly, Chakra UI)
- **State Management:** Evaluate need for global state management if dashboard grows significantly
- **API Client Refactor:** Consider migrating to tRPC or similar for better type safety
- **E2E Testing:** Add Playwright or Cypress for comprehensive integration testing

---

## 17. Appendix

### 17.1 Related Documentation

- **ZeroDB API Documentation:** `/Users/aideveloper/core/zerodb-local/docs/Zero-DB/ZeroDB_Public_Developer_Guide.md`
- **Dashboard Architecture:** `/Users/aideveloper/core/zerodb-local/dashboard/README.md`
- **Testing Standards:** `/Users/aideveloper/core/zerodb-local/docs/database/DATABASE_TESTING_STANDARDS.md`
- **Tailwind Configuration:** `/Users/aideveloper/core/zerodb-local/dashboard/tailwind.config.ts`

### 17.2 Design System Reference

**Color Palette:**
```css
/* Primary Colors (from tailwind.config.ts) */
--primary: /* HSL value */
--secondary: /* HSL value */
--accent: /* HSL value */

/* Status Colors */
--success: green-600 (#16a34a)
--warning: yellow-600 (#ca8a04)
--destructive: red-600 (#dc2626)

/* Neutral Colors */
--gray-50: #f9fafb
--gray-100: #f3f4f6
--gray-600: #4b5563
--gray-900: #111827
```

**Typography:**
```css
/* Headings */
h1: text-5xl md:text-6xl font-bold (48px / 60px)
h2: text-3xl font-bold (30px)
h3: text-2xl font-semibold (24px)

/* Body Text */
body: text-base (16px)
small: text-sm (14px)
xs: text-xs (12px)

/* Font Weights */
normal: 400
medium: 500
semibold: 600
bold: 700
```

**Spacing Scale:**
```css
/* Padding/Margin */
p-4: 1rem (16px)
p-6: 1.5rem (24px)
p-8: 2rem (32px)
py-12: 3rem vertical (48px)
py-16: 4rem vertical (64px)

/* Gaps */
gap-2: 0.5rem (8px)
gap-4: 1rem (16px)
gap-8: 2rem (32px)
```

**Border Radius:**
```css
rounded-sm: 4px
rounded-md: 6px
rounded-lg: 8px
rounded-full: 9999px
```

### 17.3 Figma/Design Assets

**Note:** If design mockups exist, reference them here:
- Figma link: [TBD]
- Design system: [TBD]
- Component library: shadcn/ui + Radix UI

### 17.4 Browser Support

**Target Browsers:**
- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Mobile Safari (iOS 13+)
- Chrome Mobile (Android 8+)

**Polyfills:**
- Next.js handles most polyfills automatically
- No additional polyfills required for target browsers

---

## Document Control

**Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-03-07 | System Architect | Initial architecture document |

**Approvals:**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Lead Developer | [TBD] | [TBD] | [TBD] |
| UI/UX Designer | [TBD] | [TBD] | [TBD] |
| Product Owner | [TBD] | [TBD] | [TBD] |

**Review Schedule:**
- Quarterly architecture reviews
- Update after each major phase completion
- Annual comprehensive review

---

## Contact & Support

**Architecture Questions:**
- System Architect: [TBD]
- Tech Lead: [TBD]

**Implementation Support:**
- Frontend Team: [TBD]
- DevOps Team: [TBD]

**Documentation:**
- GitHub: `/Users/aideveloper/core/zerodb-local/docs/architecture/`
- Wiki: [TBD]

---

**End of Document**
