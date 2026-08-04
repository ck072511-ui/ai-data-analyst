import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { AnalyticsProvider } from './contexts/AnalyticsContext';
import ChatInterface from './components/ChatInterface';
import { useAuth } from './contexts/AuthContext';
import './styles/App.css';

// Theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2563eb',
    },
    secondary: {
      main: '#7c3aed',
    },
  },
});

const queryClient = new QueryClient();

function AuthScreen() {
  const { login, register } = useAuth();
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [fullName, setFullName] = React.useState('');
  const [error, setError] = React.useState('');

  const submit = async (isRegister) => {
    setError('');
    const result = isRegister
      ? await register(email, password, fullName)
      : await login(email, password);
    if (!result.success) setError(result.error);
    if (isRegister && result.success) setError('Account created. Please sign in.');
  };

  return (
    <main className="auth-container">
      <h2>AI Data Analyst</h2>
      <input placeholder="Full name (for registration)" value={fullName} onChange={(e) => setFullName(e.target.value)} />
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <p className="auth-message">{error}</p>}
      <div><button onClick={() => submit(false)}>Sign in</button><button onClick={() => submit(true)}>Register</button></div>
    </main>
  );
}

function Application() {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <ChatInterface /> : <AuthScreen />;
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <Router>
          <AuthProvider>
            <NotificationProvider>
              <AnalyticsProvider>
                <div className="App">
                  <header className="App-header">
                    <h1>🤖 AI Data Analyst</h1>
                  </header>
                  <main>
                    <Application />
                  </main>
                </div>
              </AnalyticsProvider>
            </NotificationProvider>
          </AuthProvider>
        </Router>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
