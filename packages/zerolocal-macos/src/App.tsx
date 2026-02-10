import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { listen } from '@tauri-apps/api/event';
import Dashboard from './components/Dashboard';
import Preferences from './components/Preferences';
import Logs from './components/Logs';

export interface ServiceStatus {
  name: string;
  status: string;
  healthy: boolean;
  port?: string;
}

export interface DockerStatus {
  docker_running: boolean;
  services: ServiceStatus[];
}

export interface PrerequisiteCheck {
  docker_installed: boolean;
  docker_running: boolean;
  ports_available: boolean;
  disk_space_sufficient: boolean;
}

type TabType = 'dashboard' | 'logs' | 'preferences';

function App() {
  const [currentTab, setCurrentTab] = useState<TabType>('dashboard');
  const [status, setStatus] = useState<DockerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();

    const interval = setInterval(loadStatus, 5000);

    listen('show-preferences', () => {
      setCurrentTab('preferences');
    });

    listen('check-updates', () => {
      checkForUpdates();
    });

    return () => clearInterval(interval);
  }, []);

  async function loadStatus() {
    try {
      const dockerStatus = await invoke<DockerStatus>('get_status');
      setStatus(dockerStatus);
      setError(null);
    } catch (err) {
      setError(err as string);
    } finally {
      setLoading(false);
    }
  }

  async function startServices() {
    setLoading(true);
    try {
      await invoke('start_services');
      await loadStatus();
    } catch (err) {
      setError(err as string);
    } finally {
      setLoading(false);
    }
  }

  async function stopServices() {
    setLoading(true);
    try {
      await invoke('stop_services');
      await loadStatus();
    } catch (err) {
      setError(err as string);
    } finally {
      setLoading(false);
    }
  }

  async function restartServices() {
    setLoading(true);
    try {
      await invoke('restart_services');
      await loadStatus();
    } catch (err) {
      setError(err as string);
    } finally {
      setLoading(false);
    }
  }

  async function openDashboard() {
    try {
      await invoke('open_dashboard');
    } catch (err) {
      setError(err as string);
    }
  }

  async function checkForUpdates() {
    alert('Update check functionality coming soon!');
  }

  return (
    <div className="app">
      <div className="header">
        <h1>ZeroLocal</h1>
        {status && (
          <div className={`status-badge ${status.docker_running ? 'running' : 'stopped'}`}>
            <span>{status.docker_running ? '✓' : '✗'}</span>
            <span>{status.docker_running ? 'Running' : 'Stopped'}</span>
          </div>
        )}
      </div>

      <div className="tab-navigation">
        <button
          className={`tab-button ${currentTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setCurrentTab('dashboard')}
        >
          Dashboard
        </button>
        <button
          className={`tab-button ${currentTab === 'logs' ? 'active' : ''}`}
          onClick={() => setCurrentTab('logs')}
        >
          Logs
        </button>
        <button
          className={`tab-button ${currentTab === 'preferences' ? 'active' : ''}`}
          onClick={() => setCurrentTab('preferences')}
        >
          Preferences
        </button>
      </div>

      <div className="main-content">
        {error && (
          <div className="card" style={{ background: '#fff3e0', borderLeft: '4px solid #ff9800' }}>
            <h2>Error</h2>
            <p>{error}</p>
          </div>
        )}

        {currentTab === 'dashboard' && (
          <Dashboard
            status={status}
            loading={loading}
            onStart={startServices}
            onStop={stopServices}
            onRestart={restartServices}
            onOpenDashboard={openDashboard}
          />
        )}

        {currentTab === 'logs' && <Logs />}

        {currentTab === 'preferences' && <Preferences />}
      </div>
    </div>
  );
}

export default App;
