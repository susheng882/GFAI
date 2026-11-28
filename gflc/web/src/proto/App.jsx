import React, { useCallback, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import AppShell from './AppShell.jsx';
import AuthPage from './pages/AuthPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import DocumentsPage from './pages/DocumentsPage.jsx';
import DocumentDetailPage from './pages/DocumentDetailPage.jsx';
import NotesPage from './pages/NotesPage.jsx';
import QuestionBanksPage from './pages/QuestionBanksPage.jsx';
import DecksPage from './pages/DecksPage.jsx';
import StudyPage from './pages/StudyPage.jsx';
import ReviewPage from './pages/ReviewPage.jsx';
import PlansPage from './pages/PlansPage.jsx';
import GrowthPage from './pages/GrowthPage.jsx';
import TasksPage from './pages/TasksPage.jsx';
import QAPage from './pages/QAPage.jsx';
import VideoPage from './pages/VideoPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import { profile as defaultProfile } from './mock/index.js';

const SESSION_KEY = 'gflc_session';

function readSession() {
  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function AuthRoute({ onLogin }) {
  const navigate = useNavigate();
  const handle = useCallback(
    (user) => {
      onLogin(user);
      navigate('/dash', { replace: true });
    },
    [onLogin, navigate],
  );
  return <AuthPage onLogin={handle} />;
}

function ShellRoute({ user, onLogout, children }) {
  return (
    <AppShell user={user} onLogout={onLogout}>
      {children}
    </AppShell>
  );
}

export default function App() {
  const [user, setUser] = useState(() => readSession());

  const onLogin = useCallback((next) => {
    setUser(next);
    try {
      window.localStorage.setItem(SESSION_KEY, JSON.stringify(next));
    } catch {
      /* 忽略存储失败，仅内存态 */
    }
  }, []);

  const onLogout = useCallback(() => {
    setUser(null);
    try {
      window.localStorage.removeItem(SESSION_KEY);
    } catch {
      /* 忽略 */
    }
  }, []);

  const current = user || defaultProfile;
  const guard = (node) => (user ? node : <Navigate to="/auth" replace />);

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/auth"
          element={user ? <Navigate to="/dash" replace /> : <AuthRoute onLogin={onLogin} />}
        />
        <Route path="/" element={<Navigate to="/dash" replace />} />
        <Route
          path="/dash"
          element={guard(
            <ShellRoute user={current} onLogout={onLogout}>
              <DashboardPage />
            </ShellRoute>,
          )}
        />
        {[
          ['/docs', <DocumentsPage />],
          ['/docs/:id', <DocumentDetailPage />],
          ['/notes', <NotesPage />],
          ['/banks', <QuestionBanksPage />],
          ['/deck', <DecksPage />],
          ['/study', <StudyPage />],
          ['/review', <ReviewPage />],
          ['/plans', <PlansPage />],
          ['/growth', <GrowthPage />],
          ['/qa', <QAPage />],
          ['/tasks', <TasksPage />],
          ['/video', <VideoPage />],
          ['/settings', <SettingsPage onLogout={onLogout} />],
        ].map(([path, node]) => (
          <Route
            key={path}
            path={path}
            element={guard(
              <ShellRoute user={current} onLogout={onLogout}>
                {node}
              </ShellRoute>,
            )}
          />
        ))}
        <Route path="*" element={<Navigate to="/dash" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
