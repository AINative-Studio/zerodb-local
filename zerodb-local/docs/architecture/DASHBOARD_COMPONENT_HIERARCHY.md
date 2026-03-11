# ZeroDB Local Dashboard - Component Hierarchy Diagram

**Document Version:** 1.0.0
**Date:** 2026-03-07
**Related:** DASHBOARD_HOMEPAGE_ARCHITECTURE.md

---

## Visual Component Tree

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DashboardPage                                   │
│                        (app/page.tsx)                                    │
│                                                                           │
│  Data Fetching: useQuery(['health']) → apiClient.getHealth()            │
│  State: { health, isLoading, error }                                     │
│  Auto-refresh: 5 seconds                                                 │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌────────────────────┐        ┌────────────────────────┐
        │  if (isLoading)    │        │    if (error)          │
        │  LoadingState      │        │    ErrorState          │
        │  ├─ Spinner        │        │    ├─ AlertCircle     │
        │  └─ Message        │        │    ├─ Error Message   │
        └────────────────────┘        │    └─ Retry Button    │
                                      └────────────────────────┘
                                                │
                                                ▼
                    ┌───────────────────────────────────────────┐
                    │         Main Content Layout               │
                    │         (if health data loaded)           │
                    └───────────────┬───────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌──────────────┐          ┌──────────────────┐      ┌────────────────┐
│  HeroSection │          │ FeaturesSection  │      │CodeExamples    │
│   (NEW)      │          │     (NEW)        │      │Section (NEW)   │
└──────┬───────┘          └────────┬─────────┘      └───────┬────────┘
       │                           │                        │
       ├─► HeroHeading             ├─► FeatureGrid         ├─► Tabs
       │   ├─ H1: Title            │   └─► FeatureCard (×3)│   ├─ TabsList
       │   └─ P: Subtitle          │       ├─ Icon         │   │  ├─ Python
       │                            │       ├─ Title        │   │  ├─ JavaScript
       ├─► HeroDescription         │       └─ Description  │   │  └─ cURL
       │                            │                       │   │
       └─► HeroActions              │                       │   └─ TabsContent
           ├─ Button (Primary)      │                       │       └─► CodeBlock (×3)
           └─ Button (Secondary)    │                       │           ├─ Header
                                    │                       │           │  ├─ Description
                                    │                       │           │  └─ CopyButton
                                    │                       │           │
                                    │                       │           └─ SyntaxHighlighter
                                    │                       │
        ┌───────────────────────────┼───────────────────────────────────┐
        │                           │                                   │
        ▼                           ▼                                   ▼
┌─────────────────┐      ┌──────────────────┐           ┌──────────────────┐
│SystemStatus     │      │ServiceHealth     │           │QuickStatsSection │
│Section          │      │Section           │           │  (REFACTORED)    │
│(REFACTORED)     │      │(REFACTORED)      │           └────────┬─────────┘
└────────┬────────┘      └────────┬─────────┘                    │
         │                        │                              │
         │                        │                              ▼
         ▼                        ▼                    ┌─────────────────┐
┌──────────────┐        ┌──────────────────┐         │   StatsGrid     │
│  StatusCard  │        │  ServiceGrid     │         └────────┬────────┘
├──────────────┤        ├──────────────────┤                  │
│ CardHeader   │        │ ServiceCard (×5) │         ┌────────┴────────┐
│ ├─ Title     │        │                  │         │                 │
│ ├─ Desc      │        │ 1. PostgreSQL    │         ▼                 ▼
│ └─ Badge     │        │    ├─ CardHeader │    StatCard (×4)      StatCard
│              │        │    │  ├─ Icon    │    ├─ API Endpoint   ├─ Version
│ CardContent  │        │    │  ├─ Name    │    ├─ Dashboard URL  └─ Mode
│ └─ Summary   │        │    │  └─ Health  │    └─ Icon
│   Health/    │        │    │     Indicator│
│   Total      │        │    │             │
└──────────────┘        │    ├─ CardDesc   │
                        │    │             │
                        │    └─ CardContent│
                        │       ├─ Status  │
                        │       └─ Latency │
                        │                  │
                        │ 2. Qdrant       │
                        │ 3. MinIO        │
                        │ 4. RedPanda     │
                        │ 5. Embeddings   │
                        └──────────────────┘

```

---

## Component Interaction Flow

```
User Action                   Component Response                Data Flow
────────────────────────────────────────────────────────────────────────

1. Page Load
   │
   ├─► DashboardPage mounts
   │    └─► useQuery triggers
   │         └─► apiClient.getHealth()
   │              └─► axios.get('/health')
   │                   │
   │                   ├─► [Loading] → LoadingState renders
   │                   │                └─► Spinner + "Connecting..."
   │                   │
   │                   ├─► [Error] → ErrorState renders
   │                   │              └─► AlertCircle + Error message + Retry
   │                   │
   │                   └─► [Success] → Main content renders
   │                                    │
   │                                    ├─► HeroSection (static)
   │                                    ├─► FeaturesSection (static)
   │                                    ├─► CodeExamplesSection (static)
   │                                    │
   │                                    ├─► SystemStatusSection
   │                                    │    └─► Props: { health }
   │                                    │         └─► health.status, health.summary
   │                                    │
   │                                    ├─► ServiceHealthSection
   │                                    │    └─► Props: { health }
   │                                    │         └─► Maps over SERVICE_CONFIG
   │                                    │              └─► ServiceCard (×5)
   │                                    │                   └─► health.services[key]
   │                                    │
   │                                    └─► QuickStatsSection (static)

2. User Clicks "Copy Code"
   │
   ├─► CodeBlock: handleCopy()
   │    └─► navigator.clipboard.writeText(code)
   │         └─► setState: { copied: true }
   │              └─► Button text: "Copy" → "Copied"
   │                   └─► setTimeout(2000) → { copied: false }

3. User Switches Code Tab
   │
   ├─► TabsTrigger: onClick
   │    └─► Tabs: onChange(value)
   │         └─► activeTab: "python" → "javascript"
   │              └─► TabsContent renders new code
   │                   └─► CodeBlock with JavaScript code

4. User Clicks Retry (on error)
   │
   ├─► ErrorState: retry()
   │    └─► refetch() (from useQuery)
   │         └─► apiClient.getHealth() (retry request)
   │              └─► [Loading state] → [Success/Error]

5. Auto-Refresh (every 5 seconds)
   │
   ├─► useQuery: refetchInterval fires
   │    └─► apiClient.getHealth()
   │         └─► health data updates
   │              └─► Components re-render with new data
   │                   ├─► StatusBadge color changes
   │                   ├─► Latency values update
   │                   └─► Health indicators update

6. User Clicks Hero CTA
   │
   ├─► HeroActions: onPrimaryClick()
   │    └─► Navigate to /docs/quickstart (example)
   │         OR open external documentation

```

---

## Data Dependencies Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                      API Client Layer                          │
│                   (services/api-client.ts)                     │
│                                                                 │
│  apiClient.getHealth() → axios.get('/health')                 │
│                           │                                     │
│                           └─► Returns: HealthStatus            │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                     React Query Cache                          │
│                  (@tanstack/react-query)                       │
│                                                                 │
│  queryKey: ['health']                                          │
│  data: HealthStatus | undefined                                │
│  isLoading: boolean                                            │
│  error: Error | null                                           │
│  refetchInterval: 5000ms                                       │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                      DashboardPage                             │
│                                                                 │
│  Destructures: { data: health, isLoading, error }             │
└───────────────────┬────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┬────────────────────────┐
        │                       │                        │
        ▼                       ▼                        ▼
┌──────────────┐      ┌──────────────────┐     ┌────────────────┐
│ HeroSection  │      │SystemStatus      │     │ServiceHealth   │
│              │      │Section           │     │Section         │
│ NO DATA      │      │                  │     │                │
│ NEEDED       │      │ Props:           │     │ Props:         │
│ (static)     │      │ ├─ health        │     │ ├─ health      │
│              │      │ │  ├─ status     │     │ │  └─ services │
│              │      │ │  └─ summary    │     │ │      ├─postgres│
└──────────────┘      │ │     ├─ healthy │     │ │      ├─qdrant │
                      │ │     └─ total   │     │ │      ├─minio  │
┌──────────────┐      │ │                │     │ │      ├─redpanda│
│ Features     │      │ └─► StatusCard   │     │ │      └─embeddings│
│ Section      │      │     ├─ Badge     │     │ │                │
│              │      │     └─ Text      │     │ └─► ServiceCard │
│ NO DATA      │      └──────────────────┘     │     (×5)        │
│ NEEDED       │                               │     ├─ status   │
│ (static)     │                               │     ├─ latency  │
└──────────────┘                               │     └─ error    │
                                               └────────────────┘
┌──────────────┐
│ CodeExamples │      ┌──────────────────┐
│ Section      │      │ QuickStats       │
│              │      │ Section          │
│ NO DATA      │      │                  │
│ NEEDED       │      │ NO DATA NEEDED   │
│ (static)     │      │ (static config)  │
└──────────────┘      └──────────────────┘
```

---

## Component Props Interface Map

```typescript
// Type: No Props (Static Components)
┌────────────────────────────────┐
│ HeroSection                    │
│ FeaturesSection                │
│ CodeExamplesSection            │
│ QuickStatsSection              │
└────────────────────────────────┘

// Type: Health Data Consumers
┌────────────────────────────────┐
│ SystemStatusSection            │
│ Props: {                       │
│   health: HealthStatus         │
│   className?: string           │
│ }                              │
└────────────────────────────────┘

┌────────────────────────────────┐
│ ServiceHealthSection           │
│ Props: {                       │
│   health: HealthStatus         │
│   className?: string           │
│ }                              │
└────────────────────────────────┘

┌────────────────────────────────┐
│ ServiceCard                    │
│ Props: {                       │
│   name: string                 │
│   status: 'healthy'|'unhealthy'│
│   latency?: number             │
│   icon: ReactNode              │
│   description: string          │
│   error?: string               │
│   className?: string           │
│ }                              │
└────────────────────────────────┘

// Type: Configuration/Content Props
┌────────────────────────────────┐
│ HeroActions                    │
│ Props: {                       │
│   primaryLabel?: string        │
│   primaryHref?: string         │
│   secondaryLabel?: string      │
│   secondaryHref?: string       │
│   onPrimaryClick?: () => void  │
│   onSecondaryClick?: () => void│
│   className?: string           │
│ }                              │
└────────────────────────────────┘

┌────────────────────────────────┐
│ CodeBlock                      │
│ Props: {                       │
│   code: string                 │
│   language: string             │
│   description?: string         │
│   showLineNumbers?: boolean    │
│   className?: string           │
│ }                              │
└────────────────────────────────┘

// Type: Utility Components
┌────────────────────────────────┐
│ LoadingState                   │
│ Props: {                       │
│   message?: string             │
│   className?: string           │
│ }                              │
└────────────────────────────────┘

┌────────────────────────────────┐
│ ErrorState                     │
│ Props: {                       │
│   title?: string               │
│   message: string              │
│   retry?: () => void           │
│   className?: string           │
│ }                              │
└────────────────────────────────┘
```

---

## Render Cycle Flow

```
Initial Render
──────────────

1. DashboardPage mounts
   └─► useQuery('health') initializes
        ├─► isLoading: true
        ├─► data: undefined
        └─► error: null

2. Component renders with isLoading=true
   └─► <LoadingState /> renders
        └─► Spinner animation
        └─► "Connecting to ZeroDB..." message

3. API request completes (success)
   └─► useQuery updates
        ├─► isLoading: false
        ├─► data: HealthStatus {...}
        └─► error: null

4. Re-render triggered
   └─► LoadingState unmounts
   └─► Main content renders
        ├─► HeroSection (static - fast render)
        ├─► FeaturesSection (static - fast render)
        ├─► CodeExamplesSection (static - fast render)
        ├─► SystemStatusSection (props: health)
        ├─► ServiceHealthSection (props: health)
        └─► QuickStatsSection (static - fast render)


Subsequent Renders (Auto-Refresh)
──────────────────────────────────

Every 5 seconds:

1. useQuery refetchInterval fires
   └─► API request in background
        └─► isLoading stays false (background refetch)

2. API response received
   └─► useQuery updates data
        └─► health: {...new data}

3. Re-render triggered (only data-dependent components)
   ├─► HeroSection (no re-render - no props)
   ├─► FeaturesSection (no re-render - no props)
   ├─► CodeExamplesSection (no re-render - no props)
   ├─► SystemStatusSection (re-renders with new health)
   │    └─► StatusCard updates
   │         ├─► Badge color changes (if status changed)
   │         └─► Summary text updates
   │
   ├─► ServiceHealthSection (re-renders with new health)
   │    └─► ServiceCard (×5) update
   │         ├─► Status badges update
   │         ├─► Latency values update
   │         └─► Health indicators update
   │
   └─► QuickStatsSection (no re-render - static)


Error Handling Flow
───────────────────

1. API request fails
   └─► useQuery updates
        ├─► isLoading: false
        ├─► data: undefined
        └─► error: Error {...}

2. Component re-renders
   └─► ErrorState renders
        ├─► AlertCircle icon
        ├─► "Connection Error" title
        ├─► Error message
        └─► Retry button

3. User clicks Retry
   └─► refetch() called
        └─► Repeat from "Initial Render"


User Interaction Flow
─────────────────────

Copy Code Button:
1. User clicks "Copy" button
   └─► CodeBlock: handleCopy()
        └─► navigator.clipboard.writeText(code)
             └─► setState({ copied: true })
                  ├─► Button text changes: "Copy" → "Copied"
                  └─► setTimeout(2000)
                       └─► setState({ copied: false })
                            └─► Button text changes: "Copied" → "Copy"

Tab Switching:
1. User clicks "JavaScript" tab
   └─► Tabs: onChange("javascript")
        └─► activeTab: "python" → "javascript"
             └─► TabsContent unmounts (Python)
             └─► TabsContent mounts (JavaScript)
                  └─► CodeBlock renders with JS code
                       └─► SyntaxHighlighter initializes

Hero CTA Button:
1. User clicks "Quick Start Guide"
   └─► HeroActions: onPrimaryClick()
        └─► Navigate to /docs/quickstart
             OR window.open(docs_url)
```

---

## Component Lifecycle Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    Component Lifecycle                          │
└─────────────────────────────────────────────────────────────────┘

Static Components (No Props)
─────────────────────────────
  Mount Once → Render Once → Never Re-render (unless forced)

  Examples:
  - HeroSection
  - FeaturesSection
  - CodeExamplesSection (except internal state for tabs)
  - QuickStatsSection

Data-Dependent Components
─────────────────────────────
  Mount → Initial Render → Re-render on data change (every 5s)

  Examples:
  - SystemStatusSection (health)
  - ServiceHealthSection (health)
  - ServiceCard (×5) (health.services[key])

Interactive Components
──────────────────────
  Mount → Render → Re-render on local state change

  Examples:
  - CodeBlock (copied state)
  - Tabs (activeTab state)

Conditional Components
──────────────────────
  Mount/Unmount based on conditions

  Examples:
  - LoadingState (if isLoading)
  - ErrorState (if error)
  - Main Content (if !isLoading && !error)
```

---

## Performance Optimization Points

```
┌─────────────────────────────────────────────────────────────────┐
│               Optimization Strategy                             │
└─────────────────────────────────────────────────────────────────┘

1. Static Components (No Re-renders)
   ──────────────────────────────────
   ✓ HeroSection: Pure static content
   ✓ FeaturesSection: Pure static content
   ✓ QuickStatsSection: Pure static content

   → No memoization needed
   → No prop drilling
   → Fast initial render

2. Data Components (Smart Re-renders)
   ───────────────────────────────────
   ✓ Use React.memo() for ServiceCard
   ✓ Props comparison: status, latency (primitives)
   ✓ Only re-render when health data changes

   → Prevents unnecessary renders
   → Shallow comparison efficient

3. Heavy Components (Lazy Loading)
   ────────────────────────────────
   ✓ Dynamic import for SyntaxHighlighter
   ✓ Load only when CodeExamplesSection visible
   ✓ SSR: false (client-side only)

   → Reduces initial bundle size
   → Faster time-to-interactive

4. List Components (Efficient Mapping)
   ────────────────────────────────────
   ✓ ServiceCard: Use stable keys (service.name)
   ✓ FeatureCard: Use stable keys (feature.id)
   ✓ StatCard: Use stable keys (stat.label)

   → React can efficiently diff lists
   → No unnecessary DOM mutations

5. Icon Components (Optimized Imports)
   ────────────────────────────────────
   ✓ Import only used icons:
     import { Database, Activity } from 'lucide-react'
   ✗ Avoid: import * as Icons from 'lucide-react'

   → Reduces bundle size significantly
   → Enables tree-shaking
```

---

## Component Testing Matrix

```
┌─────────────────────────────────────────────────────────────────┐
│                    Testing Strategy                             │
└─────────────────────────────────────────────────────────────────┘

Component              Unit Tests    A11y Tests   Integration
──────────────────────────────────────────────────────────────────
HeroSection            ✓ Renders     ✓ axe-core   ✓ Click CTAs
HeroActions            ✓ Callbacks   ✓ Keyboard   ✓ Navigation
FeaturesSection        ✓ Grid        ✓ Screen     -
FeatureCard            ✓ Props       ✓ ARIA       -
CodeExamplesSection    ✓ Tabs        ✓ Tab nav    ✓ Tab switch
CodeBlock              ✓ Copy func   ✓ Button     ✓ Clipboard
SystemStatusSection    ✓ Health data ✓ Live       ✓ API mock
ServiceHealthSection   ✓ Service map ✓ List       ✓ API mock
ServiceCard            ✓ Status      ✓ Status     -
QuickStatsSection      ✓ Stats grid  ✓ List       -
StatCard               ✓ Display     ✓ Label      -
LoadingState           ✓ Spinner     ✓ Status     -
ErrorState             ✓ Retry       ✓ Alert      ✓ Refetch
DashboardPage          ✓ Routing     ✓ Full page  ✓ E2E

Coverage Target: ≥ 80% lines, ≥ 75% branches
```

---

## Component File Size Budget

```
┌─────────────────────────────────────────────────────────────────┐
│                     Bundle Size Analysis                        │
└─────────────────────────────────────────────────────────────────┘

Component/Module              Size (gzipped)    Priority
──────────────────────────────────────────────────────────────────
HeroSection.tsx               ~2 KB             High
FeaturesSection.tsx           ~3 KB             High
CodeExamplesSection.tsx       ~4 KB             Medium
CodeBlock.tsx                 ~3 KB             Medium
react-syntax-highlighter      ~25 KB            Low (lazy)
SystemStatusSection.tsx       ~2 KB             High
ServiceHealthSection.tsx      ~3 KB             High
ServiceCard.tsx               ~2 KB             High
QuickStatsSection.tsx         ~2 KB             High
StatCard.tsx                  ~1 KB             High
LoadingState.tsx              ~1 KB             High
ErrorState.tsx                ~2 KB             High

Total Estimated Addition:     ~50 KB            Target: < 50 KB
──────────────────────────────────────────────────────────────────

Optimization Strategies:
1. Lazy load react-syntax-highlighter (saves ~25 KB on initial load)
2. Use dynamic imports for CodeExamplesSection if below fold
3. Tree-shake lucide-react icons (import only used icons)
4. Enable Next.js code splitting (automatic)
```

---

**End of Diagram Document**
