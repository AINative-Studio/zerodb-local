import React from 'react';
import { DockerStatus } from '../App';

interface DashboardProps {
  status: DockerStatus | null;
  loading: boolean;
  onStart: () => void;
  onStop: () => void;
  onRestart: () => void;
  onOpenDashboard: () => void;
}

const serviceIcons: Record<string, string> = {
  'zerodb-api': '🚀',
  'zerodb-dashboard': '📊',
  'zerodb-postgres': '🗄️',
  'zerodb-qdrant': '🔍',
  'zerodb-minio': '📦',
  'zerodb-redpanda': '🔴',
  'zerodb-embeddings': '🧠',
};

const Dashboard: React.FC<DashboardProps> = ({
  status,
  loading,
  onStart,
  onStop,
  onRestart,
  onOpenDashboard,
}) => {
  if (loading && !status) {
    return (
      <div className="card">
        <h2>Loading...</h2>
        <p>Checking Docker status...</p>
      </div>
    );
  }

  if (!status?.docker_running) {
    return (
      <div className="card">
        <h2>Docker Not Running</h2>
        <p>Please start Docker Desktop to use ZeroLocal.</p>
        <div className="button-group">
          <button className="button primary" onClick={onStart} disabled={loading}>
            {loading ? 'Starting...' : 'Start Services'}
          </button>
        </div>
      </div>
    );
  }

  const runningServices = status.services.filter((s) => s.status === 'running').length;
  const totalServices = status.services.length;

  return (
    <>
      <div className="card">
        <h2>Quick Actions</h2>
        <div className="button-group">
          <button className="button primary" onClick={onOpenDashboard}>
            Open Dashboard
          </button>
          <button className="button secondary" onClick={onRestart} disabled={loading}>
            Restart Services
          </button>
          <button className="button danger" onClick={onStop} disabled={loading}>
            Stop All
          </button>
        </div>
      </div>

      <div className="card">
        <h2>Services ({runningServices}/{totalServices} running)</h2>
        <div className="service-list">
          {status.services.map((service) => (
            <div key={service.name} className="service-item">
              <div className="service-info">
                <div className="service-icon">
                  {serviceIcons[service.name] || '📦'}
                </div>
                <div className="service-details">
                  <h3>{service.name}</h3>
                  <p>
                    {service.status === 'running' ? (
                      <span style={{ color: '#2e7d32' }}>Running</span>
                    ) : (
                      <span style={{ color: '#c62828' }}>Stopped</span>
                    )}
                    {service.port && ` • ${service.port}`}
                  </p>
                </div>
              </div>
              <div className={`status-badge ${service.status === 'running' ? 'running' : 'stopped'}`}>
                {service.status === 'running' ? '✓' : '✗'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {totalServices === 0 && (
        <div className="card">
          <h2>No Services Found</h2>
          <p>Start the services to see them here.</p>
          <div className="button-group">
            <button className="button primary" onClick={onStart} disabled={loading}>
              {loading ? 'Starting...' : 'Start Services'}
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default Dashboard;
