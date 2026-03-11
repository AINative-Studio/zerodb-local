# ZeroDB Local Dashboard - Quick Implementation Guide

**For:** Frontend UI Builder
**Project:** Enhanced Dashboard Homepage
**Related:** DASHBOARD_HOMEPAGE_ARCHITECTURE.md, DASHBOARD_COMPONENT_HIERARCHY.md

---

## Quick Start

### Step 1: Review Architecture Documents

1. Read `/Users/aideveloper/core/zerodb-local/docs/architecture/DASHBOARD_HOMEPAGE_ARCHITECTURE.md` (comprehensive specs)
2. Review `/Users/aideveloper/core/zerodb-local/docs/architecture/DASHBOARD_COMPONENT_HIERARCHY.md` (visual diagrams)
3. Examine existing `/Users/aideveloper/core/zerodb-local/dashboard/app/page.tsx`

### Step 2: Install Dependencies

```bash
cd /Users/aideveloper/core/zerodb-local/dashboard

# Install syntax highlighting library for CodeBlock
npm install react-syntax-highlighter
npm install --save-dev @types/react-syntax-highlighter

# Verify existing dependencies are up to date
npm install
```

### Step 3: Implementation Order

Follow this exact order to minimize breaking changes:

```
Phase 1: Component Extraction (Week 1)
├── 1. Extract ServiceCard → components/monitoring/ServiceCard.tsx
├── 2. Create SystemStatusSection → components/monitoring/SystemStatusSection.tsx
├── 3. Create ServiceHealthSection → components/monitoring/ServiceHealthSection.tsx
├── 4. Create QuickStatsSection → components/stats/QuickStatsSection.tsx
├── 5. Create StatCard → components/stats/StatCard.tsx
├── 6. Create LoadingState → components/common/LoadingState.tsx
├── 7. Create ErrorState → components/common/ErrorState.tsx
└── 8. Update page.tsx to use new components (verify no visual changes)

Phase 2: Hero & Features (Week 2)
├── 1. Create HeroSection → components/homepage/HeroSection.tsx
├── 2. Create HeroHeading → components/homepage/HeroHeading.tsx
├── 3. Create HeroActions → components/homepage/HeroActions.tsx
├── 4. Create FeaturesSection → components/homepage/FeaturesSection.tsx
├── 5. Create FeatureCard → components/homepage/FeatureCard.tsx
└── 6. Add to page.tsx (at top, above existing sections)

Phase 3: Code Examples (Week 3)
├── 1. Create CodeBlock → components/homepage/CodeBlock.tsx
├── 2. Create CodeExamplesSection → components/homepage/CodeExamplesSection.tsx
└── 3. Add to page.tsx (after FeaturesSection)

Phase 4: Testing & Polish (Week 4)
├── 1. Write unit tests for all components
├── 2. Accessibility audit (axe-core)
├── 3. Performance testing (Lighthouse)
└── 4. Final code review and deployment
```

---

## File Structure to Create

```
/Users/aideveloper/core/zerodb-local/dashboard/

components/
├── homepage/
│   ├── HeroSection.tsx
│   ├── HeroHeading.tsx
│   ├── HeroActions.tsx
│   ├── FeaturesSection.tsx
│   ├── FeatureCard.tsx
│   ├── CodeExamplesSection.tsx
│   └── CodeBlock.tsx
│
├── monitoring/
│   ├── SystemStatusSection.tsx
│   ├── ServiceHealthSection.tsx
│   └── ServiceCard.tsx
│
├── stats/
│   ├── QuickStatsSection.tsx
│   └── StatCard.tsx
│
└── common/
    ├── LoadingState.tsx
    └── ErrorState.tsx

types/
└── homepage.ts (new file with all homepage-related types)

tests/
└── components/
    ├── homepage/
    │   ├── HeroSection.test.tsx
    │   ├── FeaturesSection.test.tsx
    │   ├── CodeExamplesSection.test.tsx
    │   └── CodeBlock.test.tsx
    ├── monitoring/
    │   ├── SystemStatusSection.test.tsx
    │   ├── ServiceHealthSection.test.tsx
    │   └── ServiceCard.test.tsx
    └── stats/
        ├── QuickStatsSection.test.tsx
        └── StatCard.test.tsx
```

---

## Component Implementation Checklist

### For Each Component:

- [ ] Create TypeScript file with proper imports
- [ ] Define Props interface with JSDoc comments
- [ ] Implement component with accessibility attributes
- [ ] Add proper TypeScript types (no `any`)
- [ ] Use `cn()` utility for className merging
- [ ] Add ARIA labels and semantic HTML
- [ ] Export component with display name
- [ ] Write unit test file
- [ ] Write accessibility test (axe-core)
- [ ] Update types/homepage.ts if needed

---

## Critical Implementation Notes

### 1. TypeScript Strictness

```typescript
// ✓ CORRECT: Proper typing
interface ServiceCardProps {
  name: string
  status: 'healthy' | 'unhealthy'
  latency?: number
  icon: React.ReactNode
  description: string
  error?: string
  className?: string
}

// ✗ INCORRECT: Avoid 'any'
interface ServiceCardProps {
  name: any
  status: any
  // ...
}
```

### 2. Accessibility Requirements

```tsx
// ✓ CORRECT: Proper accessibility
<section
  className="py-12"
  aria-labelledby="hero-heading"
>
  <h1 id="hero-heading">
    Self-Hosted AI Database
  </h1>
</section>

// ✗ INCORRECT: Missing accessibility
<div className="py-12">
  <div>Self-Hosted AI Database</div>
</div>
```

### 3. Import Optimization

```typescript
// ✓ CORRECT: Import only what you need
import { Database, Activity, HardDrive } from 'lucide-react'

// ✗ INCORRECT: Imports entire library
import * as Icons from 'lucide-react'
```

### 4. Component Memoization

```typescript
// ✓ CORRECT: Memo for pure components with props
import { memo } from 'react'

export const ServiceCard = memo(function ServiceCard(props: ServiceCardProps) {
  // Implementation
})

// ✗ INCORRECT: Unnecessary memo for static components
export const HeroSection = memo(function HeroSection() {
  // No props, no need for memo
})
```

### 5.ClassName Merging

```typescript
// ✓ CORRECT: Use cn() utility
import { cn } from '@/lib/utils'

<Card className={cn("hover:shadow-lg", className)} />

// ✗ INCORRECT: String concatenation
<Card className={`hover:shadow-lg ${className}`} />
```

---

## Testing Requirements

### Unit Test Template

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { YourComponent } from '@/components/path/YourComponent'

describe('YourComponent', () => {
  it('renders without crashing', () => {
    render(<YourComponent />)
    expect(screen.getByRole('...')).toBeInTheDocument()
  })

  it('renders with custom props', () => {
    render(<YourComponent prop="value" />)
    expect(screen.getByText('value')).toBeInTheDocument()
  })

  it('has no accessibility violations', async () => {
    const { container } = render(<YourComponent />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
```

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:ui

# Run tests with coverage
npm run test:coverage

# Type checking
npm run type-check
```

---

## Common Patterns

### 1. Section Wrapper Pattern

```tsx
export function YourSection({ className }: { className?: string }) {
  return (
    <section
      className={cn("py-12 px-4", className)}
      aria-labelledby="section-heading"
    >
      <h2
        id="section-heading"
        className="text-3xl font-bold text-center mb-8"
      >
        Section Title
      </h2>
      {/* Section content */}
    </section>
  )
}
```

### 2. Card Component Pattern

```tsx
import { Card, CardHeader, CardContent, CardTitle, CardDescription } from '@/components/ui/card'

export function YourCard({ title, description }: YourCardProps) {
  return (
    <Card className="hover:shadow-lg transition-shadow duration-200">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Content */}
      </CardContent>
    </Card>
  )
}
```

### 3. Grid Layout Pattern

```tsx
export function YourGrid({ items }: { items: Item[] }) {
  return (
    <div
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      role="list"
      aria-label="Item list"
    >
      {items.map(item => (
        <YourCard key={item.id} {...item} />
      ))}
    </div>
  )
}
```

### 4. Interactive Button Pattern

```tsx
import { Button } from '@/components/ui/button'
import { Icon } from 'lucide-react'

export function YourButton({ onClick, label }: ButtonProps) {
  return (
    <Button
      size="lg"
      onClick={onClick}
      aria-label={label}
      className="text-lg px-8 py-6"
    >
      <Icon className="mr-2 h-5 w-5" aria-hidden="true" />
      {label}
    </Button>
  )
}
```

### 5. Conditional Rendering Pattern

```tsx
export function YourComponent() {
  const { data, isLoading, error } = useQuery(...)

  if (isLoading) {
    return <LoadingState message="Loading..." />
  }

  if (error) {
    return <ErrorState message={error.message} />
  }

  return (
    <div>{/* Main content */}</div>
  )
}
```

---

## Integration with Existing Code

### Current page.tsx Structure

```tsx
// EXISTING (lines 1-57)
'use client'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
// ... existing imports

export default function DashboardPage() {
  const { data: health, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 5000,
  })

  // Loading and error states...
}
```

### Updated page.tsx Structure (After Implementation)

```tsx
'use client'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'

// NEW: Import new components
import { HeroSection } from '@/components/homepage/HeroSection'
import { FeaturesSection } from '@/components/homepage/FeaturesSection'
import { CodeExamplesSection } from '@/components/homepage/CodeExamplesSection'

// REFACTORED: Import refactored components
import { SystemStatusSection } from '@/components/monitoring/SystemStatusSection'
import { ServiceHealthSection } from '@/components/monitoring/ServiceHealthSection'
import { QuickStatsSection } from '@/components/stats/QuickStatsSection'

// NEW: Import utility components
import { LoadingState } from '@/components/common/LoadingState'
import { ErrorState } from '@/components/common/ErrorState'

export default function DashboardPage() {
  const { data: health, isLoading, error, refetch } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 5000,
  })

  if (isLoading) {
    return (
      <div className="p-8">
        <LoadingState message="Connecting to ZeroDB..." />
      </div>
    )
  }

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

  return (
    <div className="min-h-screen bg-white">
      {/* NEW: Hero Section */}
      <HeroSection />

      {/* NEW: Features Section */}
      <FeaturesSection />

      {/* NEW: Code Examples Section */}
      <CodeExamplesSection />

      {/* EXISTING: Refactored monitoring sections */}
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

## Styling Guidelines

### Tailwind CSS Classes

```tsx
// Section spacing
className="py-12 px-4"           // Standard section padding
className="py-16 px-4"           // Hero section (larger)

// Container sizing
className="max-w-4xl mx-auto"    // Narrow content (hero text)
className="max-w-6xl mx-auto"    // Wide content (grids)

// Typography
className="text-5xl md:text-6xl font-bold"  // Hero heading
className="text-3xl font-bold"              // Section heading
className="text-xl md:text-2xl"             // Hero subtitle
className="text-base"                       // Body text
className="text-sm text-gray-600"           // Small text

// Colors
className="text-gray-900"        // Primary text
className="text-gray-600"        // Secondary text
className="text-gray-500"        // Tertiary text
className="bg-gray-50"           // Light background
className="bg-blue-50"           // Accent background

// Interactive states
className="hover:shadow-lg transition-shadow duration-200"
className="hover:bg-gray-100"
className="focus:ring-2 focus:ring-blue-500"

// Grid layouts
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4"

// Flex layouts
className="flex items-center justify-between"
className="flex flex-col sm:flex-row gap-4"
```

### Color Palette Reference

```css
/* From tailwind.config.ts */
--primary: /* Blue/Indigo theme */
--success: #16a34a (green-600)
--warning: #ca8a04 (yellow-600)
--destructive: #dc2626 (red-600)

/* Neutral palette */
--gray-50: #f9fafb
--gray-100: #f3f4f6
--gray-500: #6b7280
--gray-600: #4b5563
--gray-900: #111827
```

---

## Debugging Tips

### 1. React Query DevTools

```tsx
// Add to app/layout.tsx for development
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

<ReactQueryDevtools initialIsOpen={false} />
```

### 2. Component Props Debugging

```tsx
// Temporary: Log props to console
console.log('ServiceCard props:', { name, status, latency })

// Better: Use React DevTools browser extension
```

### 3. TypeScript Errors

```bash
# Check for type errors without running tests
npm run type-check

# VS Code: Enable "TypeScript: Show Inline Errors"
```

### 4. Accessibility Testing

```bash
# Install axe DevTools browser extension
# Right-click page → Inspect → axe DevTools tab → Scan
```

---

## Common Issues & Solutions

### Issue 1: Import Path Errors

```typescript
// ✗ INCORRECT
import { Card } from '../../../components/ui/card'

// ✓ CORRECT (use alias)
import { Card } from '@/components/ui/card'
```

### Issue 2: Missing displayName

```typescript
// ✗ INCORRECT: React DevTools shows "Anonymous"
export const ServiceCard = memo((props) => { ... })

// ✓ CORRECT: Proper display name
export const ServiceCard = memo(function ServiceCard(props) { ... })
```

### Issue 3: Type Inference Issues

```typescript
// ✗ INCORRECT: Type inference fails
const items = []
items.push({ name: 'test' })

// ✓ CORRECT: Explicit typing
const items: Item[] = []
items.push({ name: 'test' })
```

### Issue 4: className Not Applied

```typescript
// ✗ INCORRECT: Overwrites className
<Card className="border-red-200" />

// ✓ CORRECT: Merge with cn()
<Card className={cn("border-red-200", props.className)} />
```

---

## Performance Checklist

Before merging each phase:

- [ ] Bundle size increase < 50KB (check with `npm run build`)
- [ ] Lighthouse Performance Score > 90
- [ ] No console errors or warnings
- [ ] All images optimized (use Next.js Image component)
- [ ] No unnecessary re-renders (check with React DevTools Profiler)
- [ ] All heavy libraries lazy-loaded (e.g., react-syntax-highlighter)
- [ ] Tree-shaking working (imports from specific paths)

---

## Final Checklist Before Deployment

- [ ] All unit tests passing (`npm test`)
- [ ] Test coverage ≥ 80% (`npm run test:coverage`)
- [ ] No TypeScript errors (`npm run type-check`)
- [ ] No ESLint errors (`npm run lint`)
- [ ] Accessibility audit passing (axe-core)
- [ ] Mobile responsive (test on multiple viewports)
- [ ] Cross-browser testing (Chrome, Firefox, Safari)
- [ ] Performance metrics meet targets (Lighthouse)
- [ ] Code reviewed by team
- [ ] Documentation updated

---

## Getting Help

**Architecture Questions:**
- Review: `/Users/aideveloper/core/zerodb-local/docs/architecture/DASHBOARD_HOMEPAGE_ARCHITECTURE.md`
- Component hierarchy: `/Users/aideveloper/core/zerodb-local/docs/architecture/DASHBOARD_COMPONENT_HIERARCHY.md`

**API Integration:**
- API client: `/Users/aideveloper/core/zerodb-local/dashboard/services/api-client.ts`
- Types: `/Users/aideveloper/core/zerodb-local/dashboard/types/index.ts`

**UI Components:**
- shadcn/ui docs: https://ui.shadcn.com/
- Radix UI docs: https://www.radix-ui.com/
- Tailwind CSS docs: https://tailwindcss.com/

**Testing:**
- Vitest docs: https://vitest.dev/
- React Testing Library: https://testing-library.com/react
- axe-core: https://github.com/dequelabs/axe-core

---

## Next Steps

1. **Start with Phase 1:** Extract existing components without changing functionality
2. **Test thoroughly:** Ensure no visual regressions
3. **Move to Phase 2:** Add new hero and features sections
4. **Iterate:** Get feedback, refine, and continue to Phase 3
5. **Polish:** Phase 4 is for testing, optimization, and final touches

Good luck with the implementation! Follow the architecture document closely and reach out if you have questions.

---

**Document Version:** 1.0.0
**Last Updated:** 2026-03-07
**Author:** System Architect
