import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../App';
import { api } from '../lib/api';
import type { Workspace, Tag } from '../lib/api';

const navItems = [
  { path: '/', icon: '📝', label: '笔记' },
  { path: '/tags', icon: '🏷️', label: '标签' },
  { path: '/activity', icon: '📋', label: '活动日志' },
  { path: '/settings', icon: '⚙️', label: '设置' },
];

export default function Dashboard() {
  const { username, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<number | null>(null);
  const [tags, setTags] = useState<Tag[]>([]);
  const [health, setHealth] = useState<{ status: string; version: string } | null>(null);

  useEffect(() => {
    api.workspaces().then(setWorkspaces).catch(() => {});
    api.tags(true).then(setTags).catch(() => {});
    api.health().then(setHealth).catch(() => {});
  }, []);

  const handleWorkspaceChange = (id: number | null) => {
    setSelectedWorkspace(id);
    window.dispatchEvent(new CustomEvent('workspace-change', { detail: id }));
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-16'
        } bg-slate-800 text-slate-200 flex flex-col transition-all duration-300`}
      >
        {/* Logo */}
        <div className="p-4 border-b border-slate-700 flex items-center justify-between">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <span className="text-xl">🧠</span>
              <span className="font-bold text-white">MemoMind</span>
              {health && (
                <span className="text-xs bg-slate-600 px-1.5 py-0.5 rounded">
                  v{health.version}
                </span>
              )}
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 hover:bg-slate-700 rounded transition"
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>

        {/* Workspace selector */}
        {sidebarOpen && workspaces.length > 0 && (
          <div className="p-3 border-b border-slate-700">
            <label className="text-xs text-slate-400 uppercase tracking-wider">工作区</label>
            <select
              value={selectedWorkspace ?? ''}
              onChange={(e) => handleWorkspaceChange(e.target.value ? Number(e.target.value) : null)}
              className="w-full mt-1 bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm text-white outline-none focus:border-blue-500"
            >
              <option value="">全部工作区</option>
              {workspaces.map((ws) => (
                <option key={ws.id} value={ws.id}>
                  {ws.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition ${
                location.pathname === item.path
                  ? 'bg-blue-600 text-white'
                  : 'hover:bg-slate-700'
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </button>
          ))}
        </nav>

        {/* Tags (show in sidebar when open) */}
        {sidebarOpen && tags.length > 0 && (
          <div className="p-3 border-t border-slate-700">
            <label className="text-xs text-slate-400 uppercase tracking-wider">标签</label>
            <div className="mt-2 flex flex-wrap gap-1">
              {tags.slice(0, 10).map((tag) => (
                <span
                  key={tag.id}
                  className="px-2 py-0.5 bg-slate-600 rounded text-xs cursor-pointer hover:bg-slate-500 transition"
                  onClick={() => {
                    navigate(`/?tag=${tag.name}`);
                  }}
                >
                  {tag.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* User */}
        <div className="p-3 border-t border-slate-700">
          <div className="flex items-center justify-between">
            {sidebarOpen && <span className="text-sm">{username}</span>}
            <button
              onClick={logout}
              className="p-1.5 hover:bg-red-600 rounded transition"
              title="退出登录"
            >
              🚪
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
