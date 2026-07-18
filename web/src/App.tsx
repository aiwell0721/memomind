import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useState, useEffect, createContext, useContext } from 'react';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Notes from './pages/Notes';
import NoteEditor from './pages/NoteEditor';
import Tags from './pages/Tags';
import Activity from './pages/Activity';
import Settings from './pages/Settings';
import AiChat from './pages/AiChat';
import { api } from './lib/api';

/* ═══════════════════════════════════════════
   Auth Context
   ═══════════════════════════════════════════ */

interface AuthContextType {
  token: string | null;
  username: string | null;
  login: (username: string, token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  token: null,
  username: null,
  login: () => {},
  logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

/* ═══════════════════════════════════════════
   Protected Route
   ═══════════════════════════════════════════ */

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

/* ═══════════════════════════════════════════
   Page Transition Wrapper
   ═══════════════════════════════════════════ */

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <div key={location.pathname} className="page-enter">
      <Routes location={location}>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        >
          <Route index element={<Notes />} />
          <Route path="notes/:id" element={<NoteEditor />} />
          <Route path="tags" element={<Tags />} />
          <Route path="activity" element={<Activity />} />
          <Route path="settings" element={<Settings />} />
          <Route path="ai" element={<AiChat />} />
        </Route>
      </Routes>
    </div>
  );
}

/* ═══════════════════════════════════════════
   Toast System (global)
   ═══════════════════════════════════════════ */

interface ToastItem {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info';
}

let toastId = 0;
let addToastFn: ((msg: string, type: ToastItem['type']) => void) | null = null;

/** 全局 toast 工具：toast("保存成功") 或 toast("保存成功", "success") */
export function toast(message: string, type: ToastItem['type'] = 'success') {
  addToastFn?.(message, type);
}

function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    addToastFn = (message, type) => {
      const id = ++toastId;
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => {
        setToasts((prev) => prev.map((t) => (t.id === id ? { ...t } : t)));
        // 触发退出动画
        const el = document.getElementById(`toast-${id}`);
        if (el) el.classList.add('toast-out');
        setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 260);
      }, 3000);
    };
    return () => { addToastFn = null; };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} id={`toast-${t.id}`} className={`toast toast-${t.type}`}>
          {t.type === 'success' && (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          )}
          {t.type === 'error' && (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          )}
          {t.type === 'info' && (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
          )}
          {t.message}
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════
   App Root
   ═══════════════════════════════════════════ */

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('memomind_token'));
  const [username, setUsername] = useState<string | null>(localStorage.getItem('memomind_user'));

  useEffect(() => {
    if (token) {
      api.me().catch(() => {
        localStorage.removeItem('memomind_token');
        localStorage.removeItem('memomind_user');
        setToken(null);
        setUsername(null);
      });
    }
  }, [token]);

  const login = (u: string, t: string) => {
    localStorage.setItem('memomind_token', t);
    localStorage.setItem('memomind_user', u);
    setToken(t);
    setUsername(u);
  };

  const logout = () => {
    localStorage.removeItem('memomind_token');
    localStorage.removeItem('memomind_user');
    setToken(null);
    setUsername(null);
  };

  return (
    <AuthContext.Provider value={{ token, username, login, logout }}>
      <BrowserRouter>
        <AnimatedRoutes />
        <ToastContainer />
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

export default App;
