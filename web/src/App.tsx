import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect, createContext, useContext } from 'react';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Notes from './pages/Notes';
import NoteEditor from './pages/NoteEditor';
import Tags from './pages/Tags';
import Activity from './pages/Activity';
import Settings from './pages/Settings';
import { api } from './lib/api';

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

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

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
        <Routes>
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
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

export default App;
