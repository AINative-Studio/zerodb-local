import React, { useState, useEffect } from 'react';

interface PreferencesData {
  autoStartOnLogin: boolean;
  showNotifications: boolean;
  apiPort: number;
  dashboardPort: number;
  autoCheckUpdates: boolean;
}

const Preferences: React.FC = () => {
  const [preferences, setPreferences] = useState<PreferencesData>({
    autoStartOnLogin: false,
    showNotifications: true,
    apiPort: 8000,
    dashboardPort: 3000,
    autoCheckUpdates: true,
  });

  const [saved, setSaved] = useState(false);

  useEffect(() => {
    loadPreferences();
  }, []);

  function loadPreferences() {
    const stored = localStorage.getItem('zerolocal-preferences');
    if (stored) {
      setPreferences(JSON.parse(stored));
    }
  }

  function savePreferences() {
    localStorage.setItem('zerolocal-preferences', JSON.stringify(preferences));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function updatePreference<K extends keyof PreferencesData>(
    key: K,
    value: PreferencesData[K]
  ) {
    setPreferences((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div className="card">
      <h2>Preferences</h2>

      <div className="preferences-section">
        <h3>General</h3>
        <div className="form-group">
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="autoStartOnLogin"
              checked={preferences.autoStartOnLogin}
              onChange={(e) => updatePreference('autoStartOnLogin', e.target.checked)}
            />
            <label htmlFor="autoStartOnLogin">Start services automatically on login</label>
          </div>
        </div>
        <div className="form-group">
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="showNotifications"
              checked={preferences.showNotifications}
              onChange={(e) => updatePreference('showNotifications', e.target.checked)}
            />
            <label htmlFor="showNotifications">Show notifications</label>
          </div>
        </div>
        <div className="form-group">
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="autoCheckUpdates"
              checked={preferences.autoCheckUpdates}
              onChange={(e) => updatePreference('autoCheckUpdates', e.target.checked)}
            />
            <label htmlFor="autoCheckUpdates">Automatically check for updates</label>
          </div>
        </div>
      </div>

      <div className="preferences-section">
        <h3>Ports</h3>
        <div className="form-group">
          <label htmlFor="apiPort">API Port</label>
          <input
            type="number"
            id="apiPort"
            value={preferences.apiPort}
            onChange={(e) => updatePreference('apiPort', parseInt(e.target.value))}
          />
        </div>
        <div className="form-group">
          <label htmlFor="dashboardPort">Dashboard Port</label>
          <input
            type="number"
            id="dashboardPort"
            value={preferences.dashboardPort}
            onChange={(e) => updatePreference('dashboardPort', parseInt(e.target.value))}
          />
        </div>
      </div>

      <div className="button-group">
        <button className="button primary" onClick={savePreferences}>
          {saved ? 'Saved!' : 'Save Preferences'}
        </button>
        <button className="button secondary" onClick={loadPreferences}>
          Reset
        </button>
      </div>

      <div style={{ marginTop: '32px', padding: '16px', background: '#f5f5f7', borderRadius: '8px' }}>
        <h3 style={{ fontSize: '14px', marginBottom: '8px' }}>About ZeroLocal</h3>
        <p style={{ fontSize: '13px', color: '#86868b', marginBottom: '4px' }}>
          Version 0.1.0
        </p>
        <p style={{ fontSize: '13px', color: '#86868b' }}>
          Built with Tauri, React, and Rust
        </p>
      </div>
    </div>
  );
};

export default Preferences;
