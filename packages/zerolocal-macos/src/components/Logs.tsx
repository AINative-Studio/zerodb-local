import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/tauri';

const Logs: React.FC = () => {
  const [logs, setLogs] = useState<string>('');
  const [selectedService, setSelectedService] = useState<string>('all');
  const [loading, setLoading] = useState(false);

  const services = [
    { value: 'all', label: 'All Services' },
    { value: 'zerodb-api', label: 'API' },
    { value: 'zerodb-dashboard', label: 'Dashboard' },
    { value: 'zerodb-postgres', label: 'PostgreSQL' },
    { value: 'zerodb-qdrant', label: 'Qdrant' },
    { value: 'zerodb-minio', label: 'MinIO' },
    { value: 'zerodb-redpanda', label: 'RedPanda' },
    { value: 'zerodb-embeddings', label: 'Embeddings' },
  ];

  useEffect(() => {
    loadLogs();
  }, [selectedService]);

  async function loadLogs() {
    setLoading(true);
    try {
      const service = selectedService === 'all' ? undefined : selectedService;
      const logData = await invoke<string>('get_logs', { service });
      setLogs(logData || 'No logs available');
    } catch (err) {
      setLogs(`Error loading logs: ${err}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2>Service Logs</h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: '6px',
              border: '1px solid #d2d2d7',
              fontSize: '14px',
            }}
          >
            {services.map((service) => (
              <option key={service.value} value={service.value}>
                {service.label}
              </option>
            ))}
          </select>
          <button className="button secondary" onClick={loadLogs} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>
      <div className="logs-container">
        <pre>{logs}</pre>
      </div>
    </div>
  );
};

export default Logs;
