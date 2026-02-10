import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Dashboard from '../../src/components/Dashboard';
import { DockerStatus } from '../../src/App';

describe('Dashboard Component', () => {
  const mockStatus: DockerStatus = {
    docker_running: true,
    services: [
      {
        name: 'zerodb-api',
        status: 'running',
        healthy: true,
        port: 'localhost:8000',
      },
      {
        name: 'zerodb-dashboard',
        status: 'running',
        healthy: true,
        port: 'localhost:3000',
      },
      {
        name: 'zerodb-postgres',
        status: 'stopped',
        healthy: false,
        port: undefined,
      },
    ],
  };

  it('should render loading state when loading without status', () => {
    const mockProps = {
      status: null,
      loading: true,
      onStart: vi.fn(),
      onStop: vi.fn(),
      onRestart: vi.fn(),
      onOpenDashboard: vi.fn(),
    };

    render(<Dashboard {...mockProps} />);
    expect(screen.getByText(/Loading/i)).toBeInTheDocument();
  });

  it('should render Docker not running message when Docker is stopped', () => {
    const stoppedStatus: DockerStatus = {
      docker_running: false,
      services: [],
    };

    const mockProps = {
      status: stoppedStatus,
      loading: false,
      onStart: vi.fn(),
      onStop: vi.fn(),
      onRestart: vi.fn(),
      onOpenDashboard: vi.fn(),
    };

    render(<Dashboard {...mockProps} />);
    expect(screen.getByText(/Docker Not Running/i)).toBeInTheDocument();
  });

  it('should render all services when Docker is running', () => {
    const mockProps = {
      status: mockStatus,
      loading: false,
      onStart: vi.fn(),
      onStop: vi.fn(),
      onRestart: vi.fn(),
      onOpenDashboard: vi.fn(),
    };

    render(<Dashboard {...mockProps} />);
    expect(screen.getByText('zerodb-api')).toBeInTheDocument();
    expect(screen.getByText('zerodb-dashboard')).toBeInTheDocument();
    expect(screen.getByText('zerodb-postgres')).toBeInTheDocument();
  });

  it('should show correct service count', () => {
    const mockProps = {
      status: mockStatus,
      loading: false,
      onStart: vi.fn(),
      onStop: vi.fn(),
      onRestart: vi.fn(),
      onOpenDashboard: vi.fn(),
    };

    render(<Dashboard {...mockProps} />);
    expect(screen.getByText(/Services \(2\/3 running\)/i)).toBeInTheDocument();
  });

  it('should call onOpenDashboard when Open Dashboard button is clicked', () => {
    const mockOnOpenDashboard = vi.fn();
    const mockProps = {
      status: mockStatus,
      loading: false,
      onStart: vi.fn(),
      onStop: vi.fn(),
      onRestart: vi.fn(),
      onOpenDashboard: mockOnOpenDashboard,
    };

    render(<Dashboard {...mockProps} />);
    const button = screen.getByText('Open Dashboard');
    fireEvent.click(button);
    expect(mockOnOpenDashboard).toHaveBeenCalledTimes(1);
  });

  it('should call onRestart when Restart button is clicked', () => {
    const mockOnRestart = vi.fn();
    const mockProps = {
      status: mockStatus,
      loading: false,
      onStart: vi.fn(),
      onStop: vi.fn(),
      onRestart: mockOnRestart,
      onOpenDashboard: vi.fn(),
    };

    render(<Dashboard {...mockProps} />);
    const button = screen.getByText('Restart Services');
    fireEvent.click(button);
    expect(mockOnRestart).toHaveBeenCalledTimes(1);
  });

  it('should call onStop when Stop All button is clicked', () => {
    const mockOnStop = vi.fn();
    const mockProps = {
      status: mockStatus,
      loading: false,
      onStart: vi.fn(),
      onStop: mockOnStop,
      onRestart: vi.fn(),
      onOpenDashboard: vi.fn(),
    };

    render(<Dashboard {...mockProps} />);
    const button = screen.getByText('Stop All');
    fireEvent.click(button);
    expect(mockOnStop).toHaveBeenCalledTimes(1);
  });

  it('should disable buttons when loading', () => {
    const mockProps = {
      status: mockStatus,
      loading: true,
      onStart: vi.fn(),
      onStop: vi.fn(),
      onRestart: vi.fn(),
      onOpenDashboard: vi.fn(),
    };

    render(<Dashboard {...mockProps} />);
    const restartButton = screen.getByText('Restart Services');
    const stopButton = screen.getByText('Stop All');
    expect(restartButton).toBeDisabled();
    expect(stopButton).toBeDisabled();
  });

  it('should show port information for services', () => {
    const mockProps = {
      status: mockStatus,
      loading: false,
      onStart: vi.fn(),
      onStop: vi.fn(),
      onRestart: vi.fn(),
      onOpenDashboard: vi.fn(),
    };

    render(<Dashboard {...mockProps} />);
    expect(screen.getByText(/localhost:8000/i)).toBeInTheDocument();
    expect(screen.getByText(/localhost:3000/i)).toBeInTheDocument();
  });
});
