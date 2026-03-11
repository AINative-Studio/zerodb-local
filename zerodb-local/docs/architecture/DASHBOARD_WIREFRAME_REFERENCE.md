# ZeroDB Local Dashboard - Wireframe Reference

**Document Version:** 1.0.0
**Date:** 2026-03-07
**Purpose:** Visual layout reference for implementation

---

## Desktop Layout (1280px+)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          NAVIGATION BAR (Existing)                            │
│  ZeroDB Local Logo                          Projects | Settings | Help        │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                           HERO SECTION (NEW)                                  │
│                         Background: Gradient Blue                             │
│                                                                                │
│                      Self-Hosted AI Database                                  │
│                     (text-5xl font-bold text-gray-900)                        │
│                                                                                │
│              Zero API Costs • Full Privacy • Offline Development              │
│                     (text-xl text-gray-600)                                   │
│                                                                                │
│   ┌─────────────────────────┐   ┌─────────────────────────┐                │
│   │  🚀 Quick Start Guide   │   │  📖 View Documentation  │                │
│   │    (Primary Button)     │   │   (Secondary Button)    │                │
│   └─────────────────────────┘   └─────────────────────────┘                │
│                                                                                │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                        FEATURES SECTION (NEW)                                 │
│                                                                                │
│                      Why Choose ZeroDB Local?                                 │
│                     (text-3xl font-bold text-center)                          │
│                                                                                │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │       💰              │  │       🔒              │  │       📡          │  │
│  │  Zero API Costs      │  │  Full Privacy Control │  │ Offline Development│
│  │                      │  │                       │  │                   │  │
│  │  Run vector          │  │  Your data never      │  │ Develop without   │  │
│  │  embeddings locally  │  │  leaves your machine. │  │ internet. Perfect │  │
│  │  with BAAI BGE       │  │  Complete control     │  │ for secure        │  │
│  │  models. No external │  │  over your AI         │  │ environments and  │  │
│  │  API calls, no usage │  │  infrastructure.      │  │ travel.           │  │
│  │  fees.               │  │                       │  │                   │  │
│  │                      │  │                       │  │                   │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────┘  │
│        (Card - hover:shadow-lg)                                               │
│                                                                                │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                    CODE EXAMPLES SECTION (NEW)                                │
│                      Background: Light Gray                                   │
│                                                                                │
│                      Get Started in Seconds                                   │
│                     (text-3xl font-bold text-center)                          │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  [ Python ]  [ JavaScript ]  [ cURL ]                                │   │
│  │  (Tabs - active tab highlighted)                                     │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │  Python SDK example for storing vector embeddings    [ 📋 Copy ]    │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │  import requests                                                     │   │
│  │                                                                       │   │
│  │  # Store a vector embedding                                          │   │
│  │  response = requests.post(                                           │   │
│  │      "http://localhost:8000/v1/projects/my-project/...",           │   │
│  │      json={                                                          │   │
│  │          "vector": [0.1, 0.2, 0.3, ...],                           │   │
│  │          "metadata": {"source": "document.pdf"}                     │   │
│  │      }                                                               │   │
│  │  )                                                                   │   │
│  │                                                                       │   │
│  │  print(response.json())                                             │   │
│  │  (Syntax highlighted code - dark theme)                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                    SYSTEM STATUS SECTION (EXISTING - REFACTORED)              │
│                                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  System Status                                      [ HEALTHY ]         │  │
│  │  Overall health of all services                     (Green Badge)       │  │
│  │                                                                          │  │
│  │  5 of 5 services operational                                            │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                  SERVICE HEALTH SECTION (EXISTING - REFACTORED)               │
│                                                                                │
│  Service Health                                                                │
│                                                                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │  🗄️ PostgreSQL   │  │  🔍 Qdrant        │  │  💾 MinIO         │          │
│  │                  │  │                   │  │                   │          │
│  │  Primary database│  │  Vector search    │  │  Object storage   │          │
│  │                  │  │  engine           │  │                   │          │
│  │  ✅ [healthy]    │  │  ✅ [healthy]     │  │  ✅ [healthy]     │          │
│  │  15ms            │  │  23ms             │  │  12ms             │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                                │
│  ┌──────────────────┐  ┌──────────────────┐                                 │
│  │  📡 RedPanda     │  │  🤖 Embeddings    │                                 │
│  │                  │  │                   │                                 │
│  │  Event streaming │  │  Local embeddings │                                 │
│  │                  │  │  (BAAI BGE)       │                                 │
│  │  ✅ [healthy]    │  │  ✅ [healthy]     │                                 │
│  │  18ms            │  │  45ms             │                                 │
│  └──────────────────┘  └──────────────────┘                                 │
│                                                                                │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                    QUICK STATS SECTION (EXISTING - REFACTORED)                │
│                                                                                │
│  Quick Stats                                                                   │
│                                                                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌────────┐  │
│  │ API Endpoint    │  │ Dashboard       │  │ Version         │  │ Mode   │  │
│  │                 │  │                 │  │                 │  │        │  │
│  │ localhost:8000  │  │ localhost:3000  │  │ 1.0.0           │  │ Local  │  │
│  │ Local dev       │  │ This interface  │  │ ZeroLocal       │  │ No API │  │
│  │                 │  │                 │  │                 │  │ costs  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └────────┘  │
│                                                                                │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                              FOOTER (Existing)                                │
│                  © 2026 ZeroDB Local | Documentation | GitHub                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Tablet Layout (768px - 1024px)

```
┌─────────────────────────────────────────────────────────────┐
│                    NAVIGATION BAR                            │
│  ZeroDB Local                      [☰ Menu]                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     HERO SECTION                             │
│              Self-Hosted AI Database                         │
│                                                               │
│        Zero API Costs • Full Privacy • Offline Dev           │
│                                                               │
│         ┌───────────────────────────┐                       │
│         │  🚀 Quick Start Guide     │                       │
│         └───────────────────────────┘                       │
│         ┌───────────────────────────┐                       │
│         │  📖 View Documentation    │                       │
│         └───────────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  FEATURES SECTION                            │
│                                                               │
│          Why Choose ZeroDB Local?                            │
│                                                               │
│  ┌────────────────────┐  ┌────────────────────┐            │
│  │  💰 Zero API Costs │  │  🔒 Full Privacy   │            │
│  │  Description...    │  │  Description...    │            │
│  └────────────────────┘  └────────────────────┘            │
│                                                               │
│  ┌────────────────────┐                                     │
│  │  📡 Offline Dev    │                                     │
│  │  Description...    │                                     │
│  └────────────────────┘                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│               CODE EXAMPLES SECTION                          │
│                                                               │
│  [ Python ] [ JavaScript ] [ cURL ]                         │
│  ┌───────────────────────────────────────┐                 │
│  │  Code example with syntax highlighting │                 │
│  │  (Full width on tablet)                │                 │
│  └───────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              SYSTEM STATUS SECTION                           │
│  ┌───────────────────────────────────┐                      │
│  │  System Status    [ HEALTHY ]     │                      │
│  │  5 of 5 services operational      │                      │
│  └───────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│             SERVICE HEALTH SECTION                           │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  PostgreSQL ✅  │  │  Qdrant ✅      │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  MinIO ✅       │  │  RedPanda ✅    │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                               │
│  ┌─────────────────┐                                        │
│  │  Embeddings ✅  │                                        │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                QUICK STATS SECTION                           │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ API Endpoint │  │ Dashboard    │                        │
│  └──────────────┘  └──────────────┘                        │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ Version      │  │ Mode         │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Mobile Layout (320px - 767px)

```
┌──────────────────────────────────┐
│      NAVIGATION BAR               │
│  ZeroDB       [☰]                │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│        HERO SECTION               │
│                                   │
│    Self-Hosted AI Database       │
│        (text-4xl)                │
│                                   │
│  Zero API Costs • Full Privacy   │
│     • Offline Development        │
│                                   │
│  ┌────────────────────────┐      │
│  │  🚀 Quick Start        │      │
│  └────────────────────────┘      │
│                                   │
│  ┌────────────────────────┐      │
│  │  📖 Documentation      │      │
│  └────────────────────────┘      │
│                                   │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│      FEATURES SECTION             │
│                                   │
│  Why Choose ZeroDB Local?        │
│                                   │
│  ┌──────────────────────┐        │
│  │  💰                   │        │
│  │  Zero API Costs      │        │
│  │                      │        │
│  │  Run vector embeddings│       │
│  │  locally...           │       │
│  └──────────────────────┘        │
│                                   │
│  ┌──────────────────────┐        │
│  │  🔒                   │        │
│  │  Full Privacy Control │       │
│  │                      │        │
│  │  Your data never...   │       │
│  └──────────────────────┘        │
│                                   │
│  ┌──────────────────────┐        │
│  │  📡                   │        │
│  │  Offline Development  │       │
│  │                      │        │
│  │  Develop without...   │       │
│  └──────────────────────┘        │
│                                   │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│    CODE EXAMPLES SECTION          │
│                                   │
│  Get Started in Seconds          │
│                                   │
│  [ Python ] [JavaScript] [cURL]  │
│                                   │
│  ┌────────────────────────┐      │
│  │  Python example        │      │
│  │  (Code scrollable      │      │
│  │   horizontally)        │      │
│  │                        │      │
│  │  [ 📋 Copy ]           │      │
│  └────────────────────────┘      │
│                                   │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│    SYSTEM STATUS SECTION          │
│                                   │
│  ┌────────────────────────┐      │
│  │  System Status         │      │
│  │  [ HEALTHY ]           │      │
│  │                        │      │
│  │  5 of 5 services       │      │
│  │  operational           │      │
│  └────────────────────────┘      │
│                                   │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│    SERVICE HEALTH SECTION         │
│                                   │
│  Service Health                  │
│                                   │
│  ┌────────────────────────┐      │
│  │  🗄️ PostgreSQL        │      │
│  │  Primary database      │      │
│  │  ✅ [healthy] 15ms     │      │
│  └────────────────────────┘      │
│                                   │
│  ┌────────────────────────┐      │
│  │  🔍 Qdrant             │      │
│  │  Vector search engine  │      │
│  │  ✅ [healthy] 23ms     │      │
│  └────────────────────────┘      │
│                                   │
│  ┌────────────────────────┐      │
│  │  💾 MinIO              │      │
│  │  Object storage        │      │
│  │  ✅ [healthy] 12ms     │      │
│  └────────────────────────┘      │
│                                   │
│  ┌────────────────────────┐      │
│  │  📡 RedPanda           │      │
│  │  Event streaming       │      │
│  │  ✅ [healthy] 18ms     │      │
│  └────────────────────────┘      │
│                                   │
│  ┌────────────────────────┐      │
│  │  🤖 Embeddings         │      │
│  │  Local BAAI BGE        │      │
│  │  ✅ [healthy] 45ms     │      │
│  └────────────────────────┘      │
│                                   │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│     QUICK STATS SECTION           │
│                                   │
│  Quick Stats                     │
│                                   │
│  ┌────────────────────────┐      │
│  │  API Endpoint          │      │
│  │  localhost:8000        │      │
│  │  Local development     │      │
│  └────────────────────────┘      │
│                                   │
│  ┌────────────────────────┐      │
│  │  Dashboard             │      │
│  │  localhost:3000        │      │
│  │  This interface        │      │
│  └────────────────────────┘      │
│                                   │
│  ┌────────────────────────┐      │
│  │  Version               │      │
│  │  1.0.0                 │      │
│  │  ZeroLocal             │      │
│  └────────────────────────┘      │
│                                   │
│  ┌────────────────────────┐      │
│  │  Mode                  │      │
│  │  Local                 │      │
│  │  No API costs          │      │
│  └────────────────────────┘      │
│                                   │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│           FOOTER                  │
│  © 2026 ZeroDB Local              │
│  Documentation | GitHub           │
└──────────────────────────────────┘
```

---

## Spacing & Layout Measurements

### Section Spacing

```
Hero Section:
- Padding: py-16 (64px vertical)
- Max width: max-w-4xl (896px)
- Background: bg-gradient-to-br from-blue-50 to-indigo-50

Features Section:
- Padding: py-12 (48px vertical)
- Max width: max-w-6xl (1152px)
- Grid gap: gap-4 (16px)

Code Examples Section:
- Padding: py-12 (48px vertical)
- Max width: max-w-4xl (896px)
- Background: bg-gray-50

Monitoring Sections:
- Container padding: p-8 (32px all sides)
- Section margin bottom: mb-8 (32px)
- Grid gap: gap-4 (16px)
```

### Card Dimensions

```
Feature Cards:
- Min height: auto
- Padding: p-6 (24px)
- Border radius: rounded-lg (8px)
- Icon size: 32px (h-8 w-8)
- Icon background: 48px circle

Service Cards:
- Min height: auto
- Padding: p-6 (24px)
- Border width: 1px
- Border color: Conditional (green-200/red-200)

Stat Cards:
- Min height: auto
- Padding: Header pb-3 (12px), Content p-6 (24px)
```

### Typography Scale

```
Hero Heading:
- Desktop: text-6xl (60px)
- Mobile: text-4xl (36px)
- Font weight: font-bold (700)

Hero Subtitle:
- Desktop: text-2xl (24px)
- Mobile: text-xl (20px)
- Font weight: normal (400)

Section Headings:
- Size: text-3xl (30px)
- Font weight: font-bold (700)
- Margin bottom: mb-8 (32px)

Card Titles:
- Feature cards: text-xl (20px)
- Service cards: text-lg (18px)
- Font weight: font-semibold (600)

Body Text:
- Size: text-base (16px)
- Line height: 1.5

Small Text:
- Size: text-sm (14px)
- Color: text-gray-500
```

### Color Palette

```
Primary Text:
- Headings: text-gray-900 (#111827)
- Body: text-gray-600 (#4b5563)
- Muted: text-gray-500 (#6b7280)

Backgrounds:
- Hero: bg-gradient-to-br from-blue-50 to-indigo-50
- Code section: bg-gray-50 (#f9fafb)
- Cards: bg-white (#ffffff)
- Code block: bg-gray-800 (#1f2937)

Status Colors:
- Success: green-600 (#16a34a)
- Warning: yellow-600 (#ca8a04)
- Error: red-600 (#dc2626)
- Info: blue-600 (#2563eb)

Borders:
- Default: border-gray-200 (#e5e7eb)
- Success: border-green-200 (#bbf7d0)
- Error: border-red-200 (#fecaca)
```

---

## Interactive States

### Buttons

```
Primary Button (Quick Start):
- Default: bg-primary text-white
- Hover: opacity-90
- Focus: ring-2 ring-primary ring-offset-2
- Active: scale-95
- Transition: all 150ms ease

Secondary Button (Documentation):
- Default: border border-gray-300 text-gray-700
- Hover: bg-gray-100
- Focus: ring-2 ring-gray-300 ring-offset-2
- Active: scale-95
```

### Cards

```
Feature Cards:
- Default: shadow-sm
- Hover: shadow-lg
- Transition: shadow 200ms ease

Service Cards:
- Default: border-1
- Hover: border color darkens slightly
- Healthy: border-green-200 hover:border-green-300
- Unhealthy: border-red-200 hover:border-red-300
- Transition: colors 200ms ease

Stat Cards:
- Default: shadow-sm
- Hover: shadow-md
- Transition: shadow 200ms ease
```

### Code Block

```
Copy Button:
- Default: text-gray-300 bg-transparent
- Hover: text-white bg-gray-700
- Active: bg-gray-600
- Copied state: text-green-400
- Transition: background 150ms ease
```

### Tabs

```
Tab Trigger:
- Default: text-gray-600 bg-gray-100
- Active: text-primary bg-white border-b-2 border-primary
- Hover: bg-gray-200
- Focus: ring-2 ring-primary ring-offset-2
```

---

## Accessibility Annotations

### Focus Indicators

```
All interactive elements:
- focus:ring-2 focus:ring-primary
- focus:ring-offset-2
- focus:outline-none (only with visible ring)

Visible focus required on:
- Buttons
- Links
- Tab triggers
- Form inputs
```

### ARIA Labels

```
Hero Section:
<section aria-labelledby="hero-heading">
  <h1 id="hero-heading">...</h1>
</section>

Features Section:
<section aria-labelledby="features-heading">
  <h2 id="features-heading">...</h2>
  <div role="list" aria-label="Feature list">
    <div role="listitem">...</div>
  </div>
</section>

Service Cards:
<div role="list" aria-label="Service health status">
  <div role="listitem" aria-labelledby="service-postgres">
    <h3 id="service-postgres">PostgreSQL</h3>
    <span aria-label="Service is healthy">✅</span>
  </div>
</div>

Loading State:
<div role="status" aria-live="polite" aria-label="Loading content">
  <div aria-hidden="true">Spinner</div>
</div>

Error State:
<div role="alert" aria-live="assertive">
  Error message
</div>
```

### Semantic HTML

```
Correct structure:
<main>
  <section aria-labelledby="hero-heading">
    <h1 id="hero-heading">...</h1>
  </section>

  <section aria-labelledby="features-heading">
    <h2 id="features-heading">...</h2>
  </section>

  <section aria-labelledby="status-heading">
    <h2 id="status-heading">...</h2>
  </section>
</main>
```

---

## Animation & Transitions

### Page Load Animation (Optional)

```
Hero Section:
- Fade in from top
- Duration: 400ms
- Delay: 0ms

Features Section:
- Fade in from bottom
- Duration: 400ms
- Delay: 100ms

Code Examples:
- Fade in from bottom
- Duration: 400ms
- Delay: 200ms

Existing Sections:
- No animation (instant render)
```

### Interactive Animations

```
Button Click:
- Scale: 0.95
- Duration: 100ms
- Easing: ease-out

Card Hover:
- Shadow: sm → lg
- Duration: 200ms
- Easing: ease-out

Tab Switch:
- Fade out: 150ms
- Fade in: 150ms
- Slide: 200ms

Copy Button:
- "Copy" → "Copied" text change
- Icon swap: Copy → Check
- Duration: 150ms
- Reset after: 2000ms
```

---

## Responsive Breakpoints

```typescript
// From tailwind.config.ts
const breakpoints = {
  sm: '640px',   // Mobile landscape, small tablets
  md: '768px',   // Tablets
  lg: '1024px',  // Desktop
  xl: '1280px',  // Large desktop
  '2xl': '1400px' // Extra large desktop
}

// Usage examples:
className="text-4xl md:text-5xl lg:text-6xl"         // Responsive text
className="grid-cols-1 md:grid-cols-2 lg:grid-cols-3" // Responsive grid
className="flex-col sm:flex-row"                      // Responsive flex
className="px-4 md:px-8 lg:px-16"                     // Responsive padding
```

---

## Loading & Error States

### Loading State Wireframe

```
┌──────────────────────────────────┐
│                                   │
│          ⟳ (Spinner)              │
│                                   │
│    Connecting to ZeroDB...       │
│    (text-gray-600)               │
│                                   │
└──────────────────────────────────┘
```

### Error State Wireframe

```
┌──────────────────────────────────┐
│  ⚠️ Connection Error              │
│  (text-red-800)                  │
│                                   │
│  Unable to connect to ZeroDB API │
│  at localhost:8000               │
│  (text-red-600)                  │
│                                   │
│  Error message details...        │
│  (text-red-700)                  │
│                                   │
│  ┌────────────────────────┐      │
│  │  🔄 Retry Connection   │      │
│  └────────────────────────┘      │
│  (Button with RefreshCw icon)    │
│                                   │
└──────────────────────────────────┘
```

---

## Print Stylesheet Considerations (Future)

If dashboard needs to be printable:

```css
@media print {
  /* Hide interactive elements */
  button, .hover-effects { display: none; }

  /* Expand collapsed sections */
  details { display: block; }

  /* Adjust colors for print */
  .bg-gradient { background: white; }

  /* Page breaks */
  section { page-break-inside: avoid; }
}
```

---

## Dark Mode Considerations (Future)

If dark mode is added later:

```tsx
// Color scheme would use CSS variables
className="bg-white dark:bg-gray-900"
className="text-gray-900 dark:text-gray-100"
className="border-gray-200 dark:border-gray-700"

// Status colors remain the same
className="bg-green-600" // Works in both modes
```

---

**End of Wireframe Reference**

**Next Steps:**
1. Review this wireframe alongside the architecture document
2. Begin implementation following the phased approach
3. Test responsiveness at each breakpoint
4. Validate accessibility at each phase
5. Maintain visual consistency with existing sections

**Visual Design Tools:**
- Figma/Sketch: For detailed mockups (if needed)
- Chrome DevTools: For responsive testing
- WAVE extension: For accessibility testing
- Lighthouse: For performance testing
