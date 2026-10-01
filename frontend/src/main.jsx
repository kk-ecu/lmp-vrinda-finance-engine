import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import Dashboard from './pages/Dashboard';
import MonthWorkspace from './pages/MonthWorkspace';
import TestExtraction from './pages/TestExtraction';
import Admin from './pages/Admin';
import Login from './pages/Login';
import ChangePassword from './pages/ChangePassword';
import { api, auth, setUnauthorizedHandler } from './services/api';

// Minimal hash router:
//   #/                 -> dashboard
//   #/month/<id>       -> workspace
//   #/test-extraction  -> extraction test bench (if enabled by config)
//   #/admin            -> admin
function useHashRoute() {
  const [hash, setHash] = useState(window.location.hash || '#/');
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || '#/');
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return hash;
}

function App() {
  const hash = useHashRoute();
  const [config, setConfig] = useState(null);
  const [authed, setAuthed] = useState(Boolean(auth.token));

  useEffect(() => {
    // When any API call returns 401, drop to the login screen.
    setUnauthorizedHandler(() => setAuthed(false));
    api.appConfig().then(setConfig).catch(() => setConfig({ auth_enabled: true, test_extraction_enabled: false }));
  }, []);

  const goHome = () => { window.location.hash = '#/'; };

  // Wait until we know whether auth is required.
  if (config === null) {
    return <div className="shell"><div className="panel empty">Loading…</div></div>;
  }

  const needsLogin = config.auth_enabled && !authed;
  if (needsLogin) {
    return <Login onLoggedIn={() => setAuthed(true)} />;
  }

  const logout = () => { auth.logout(); setAuthed(false); goHome(); };
  const testEnabled = !!config.test_extraction_enabled;

  if (hash.startsWith('#/test-extraction')) {
    if (!testEnabled) { goHome(); return null; }
    return <TestExtraction onBack={goHome} />;
  }

  if (hash.startsWith('#/admin')) {
    return <Admin onBack={goHome} onOpenMonth={(id) => { window.location.hash = `#/month/${id}`; }} />;
  }

  if (hash.startsWith('#/change-password')) {
    return <ChangePassword onBack={goHome} />;
  }

  const match = hash.match(/^#\/month\/(.+)$/);
  if (match) {
    return <MonthWorkspace monthId={match[1]} onBack={goHome} />;
  }
  return (
    <Dashboard
      onOpenMonth={(id) => { window.location.hash = `#/month/${id}`; }}
      testEnabled={testEnabled}
      authEnabled={config.auth_enabled}
      onLogout={logout}
    />
  );
}

createRoot(document.getElementById('root')).render(<App />);
