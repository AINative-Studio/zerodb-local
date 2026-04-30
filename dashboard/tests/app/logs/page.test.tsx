import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import LogsPage from '@/app/logs/page'

describe('LogsPage', () => {
  it('renders the page heading', () => {
    render(<LogsPage />)
    expect(screen.getByText('Event Logs')).toBeInTheDocument()
  })

  it('renders the description text', () => {
    render(<LogsPage />)
    expect(screen.getByText('View real-time event stream and system logs')).toBeInTheDocument()
  })

  it('renders the coming soon placeholder', () => {
    render(<LogsPage />)
    expect(screen.getByText('Log viewer coming soon')).toBeInTheDocument()
  })
})
