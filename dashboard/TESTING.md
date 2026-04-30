# Testing Documentation

## Overview

The ZeroLocal Dashboard uses Vitest for unit and integration testing with React Testing Library for component tests.

## Test Coverage Requirements

- **Minimum Coverage**: 80%
- **Test Framework**: Vitest
- **Component Testing**: React Testing Library
- **Mocking**: Vitest mocks

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui

# Generate coverage report
npm run test:coverage

# Type checking
npm run type-check
```

## Test Structure

```
tests/
├── setup.ts                          # Test setup and global mocks
├── components/
│   └── ui/
│       ├── button.test.tsx          # Button component tests
│       ├── card.test.tsx            # Card component tests
│       └── badge.test.tsx           # Badge component tests
├── lib/
│   └── utils.test.ts                # Utility functions tests
└── services/
    └── api-client.test.ts           # API client tests
```

## Test Coverage by Module

### UI Components (100% target)

- **Button**: ✅ All variants, sizes, disabled state, asChild prop
- **Card**: ✅ All sections (Header, Title, Description, Content, Footer)
- **Badge**: ✅ All variants (default, success, warning, destructive)

### Utility Functions (100% target)

- **cn**: ✅ Class merging, conditional classes
- **formatBytes**: ✅ Zero, bytes, KB, MB, GB, decimal rounding
- **formatNumber**: ✅ Small and large numbers with commas
- **formatDate**: ✅ Date strings and Date objects
- **formatRelativeTime**: ✅ Just now, minutes, hours, days, old dates

### API Client (90% target)

- **getHealth**: ✅ Successful fetch
- **listProjects**: ✅ Successful fetch, pagination
- **createProject**: ✅ Successful creation
- **Error Handling**: ✅ API errors, network errors

## Writing New Tests

### Component Test Example

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { YourComponent } from '@/components/your-component'

describe('YourComponent', () => {
  it('renders correctly', () => {
    render(<YourComponent />)
    expect(screen.getByText('Expected Text')).toBeInTheDocument()
  })

  it('handles user interaction', async () => {
    const { user } = render(<YourComponent />)
    await user.click(screen.getByRole('button'))
    expect(screen.getByText('Result')).toBeInTheDocument()
  })
})
```

### API Test Example

```typescript
import { describe, it, expect, vi } from 'vitest'
import { apiClient } from '@/services/api-client'

vi.mock('axios')

describe('API Method', () => {
  it('fetches data successfully', async () => {
    // Mock implementation
    const result = await apiClient.someMethod()
    expect(result).toBeDefined()
  })
})
```

## Mocking Strategy

### Next.js Router Mock

```typescript
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  usePathname: () => '/',
}))
```

### API Client Mock

```typescript
vi.mock('@/services/api-client', () => ({
  apiClient: {
    getHealth: vi.fn().mockResolvedValue({ status: 'healthy' }),
    listProjects: vi.fn().mockResolvedValue([]),
  },
}))
```

## Coverage Thresholds

The project is configured with the following coverage thresholds:

```json
{
  "coverage": {
    "branches": 80,
    "functions": 80,
    "lines": 80,
    "statements": 80
  }
}
```

## CI/CD Integration

Tests are run automatically on:
- Pre-commit hooks
- Pull request checks
- Production deployment

## Best Practices

1. **Test Behavior, Not Implementation**: Focus on what the component does, not how it does it
2. **Use Semantic Queries**: Prefer `getByRole`, `getByLabelText` over `getByTestId`
3. **Mock External Dependencies**: Always mock API calls and external services
4. **Test Edge Cases**: Include tests for empty states, errors, and loading states
5. **Keep Tests Fast**: Use mocks to avoid slow network calls
6. **One Assertion Per Test**: Each test should verify one specific behavior

## Common Issues

### Mock Not Working

Ensure mocks are defined before imports:
```typescript
vi.mock('module-to-mock')
import { ComponentUsingMock } from './component'
```

### Async Test Failures

Use `waitFor` for async state updates:
```typescript
await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeInTheDocument()
})
```

### Router Mock Issues

Check that `next/navigation` mock is in `tests/setup.ts`

## Refs

Issue #1129 - ZeroLocal Dashboard Implementation
