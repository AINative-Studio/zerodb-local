import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from '@/components/ui/badge'

describe('Badge Component', () => {
  it('renders badge with text', () => {
    render(<Badge>Test Badge</Badge>)
    expect(screen.getByText('Test Badge')).toBeInTheDocument()
  })

  it('applies default variant classes', () => {
    const { container } = render(<Badge>Default</Badge>)
    expect(container.firstChild).toHaveClass('bg-primary')
  })

  it('applies success variant classes', () => {
    const { container } = render(<Badge variant="success">Success</Badge>)
    expect(container.firstChild).toHaveClass('bg-green-500')
  })

  it('applies warning variant classes', () => {
    const { container } = render(<Badge variant="warning">Warning</Badge>)
    expect(container.firstChild).toHaveClass('bg-yellow-500')
  })

  it('applies destructive variant classes', () => {
    const { container } = render(<Badge variant="destructive">Error</Badge>)
    expect(container.firstChild).toHaveClass('bg-destructive')
  })

  it('applies custom className', () => {
    const { container } = render(<Badge className="custom">Custom</Badge>)
    expect(container.firstChild).toHaveClass('custom')
  })
})
