import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../App';
import { api } from '../lib/api';
import type { Workspace, Tag } from '../lib/api';

const navItems = [
  { path: '/', icon: 'note', label: '笔记' },
  { path: '/tags', icon: 'tag', label: '标签' },
  { path: '/activity', icon: 'activity', label: '活动日志' },
  { path: '/settings', icon: 'settings', label: '设置' },
];

const icons: Record<string, React.ReactNode> = {
  note: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  ),
  tag: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
      <line x1="7" y1="7" x2="7.01" y2="7" />
    </svg>
  ),
  activity: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  settings: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  ),
};

function SidebarChevron({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
    >
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

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
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--apple-bg)' }}>
      {/* Sidebar */}
      <aside
        className="flex flex-col transition-all duration-300 ease-in-out"
        style={{
          width: sidebarOpen ? 240 : 56,
          background: 'var(--apple-sidebar)',
          borderRight: '0.5px solid var(--apple-border-light)',
        }}
      >
        {/* Logo */}
        <div
          className="flex items-center justify-between px-3 py-3"
          style={{ borderBottom: '0.5px solid var(--apple-border-light)' }}
        >
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <span style={{ fontSize: 20 }}>🧠</span>
              <span style={{ fontWeight: 700, fontSize: 15, letterSpacing: '-0.02em' }}>
                MemoMind
              </span>
              {health && (
                <span
                  style={{
                    fontSize: 10,
                    background: 'rgba(0,0,0,0.06)',
                    padding: '1px 5px',
                    borderRadius: 6,
                    color: 'var(--apple-text-secondary)',
                    fontWeight: 500,
                  }}
                >
                  v{health.version}
                </span>
              )}
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            style={{
              width: 28,
              height: 28,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 6,
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              color: 'var(--apple-text-secondary)',
              transition: 'background 0.15s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(0,0,0,0.05)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <SidebarChevron open={sidebarOpen} />
          </button>
        </div>

        {/* Workspace selector */}
        {sidebarOpen && workspaces.length > 0 && (
          <div className="px-3 py-2" style={{ borderBottom: '0.5px solid var(--apple-border-light)' }}>
            <div className="section-label">工作区</div>
            <select
              value={selectedWorkspace ?? ''}
              onChange={(e) =>
                handleWorkspaceChange(e.target.value ? Number(e.target.value) : null)
              }
              style={{
                width: '100%',
                marginTop: 4,
                background: 'var(--apple-surface)',
                border: '0.5px solid var(--apple-border)',
                borderRadius: 8,
                padding: '4px 8px',
                fontSize: 12,
                color: 'var(--apple-text)',
                outline: 'none',
                fontFamily: 'inherit',
              }}
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
        <nav className="flex-1 px-2 py-2 space-y-0.5">
          {sidebarOpen && <div className="section-label">导航</div>}
          {navItems.map((item) => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className="sidebar-item"
              style={{
                background:
                  location.pathname === item.path
                    ? 'var(--accent-light)'
                    : 'transparent',
                color:
                  location.pathname === item.path
                    ? 'var(--accent)'
                    : 'var(--apple-text)',
                fontWeight: location.pathname === item.path ? 600 : 500,
                animation: sidebarOpen ? 'none' : 'none',
              }}
            >
              <span style={{ opacity: 0.75 }}>{icons[item.icon]}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </button>
          ))}
        </nav>

        {/* Tags */}
        {sidebarOpen && tags.length > 0 && (
          <div className="px-3 py-2" style={{ borderTop: '0.5px solid var(--apple-border-light)' }}>
            <div className="section-label">标签</div>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {tags.slice(0, 10).map((tag) => (
                <span
                  key={tag.id}
                  onClick={() => navigate(`/?tag=${tag.name}`)}
                  style={{
                    padding: '2px 8px',
                    background: 'rgba(0,0,0,0.04)',
                    borderRadius: 6,
                    fontSize: 11,
                    color: 'var(--apple-text-secondary)',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(0,0,0,0.08)';
                    e.currentTarget.style.color = 'var(--apple-text)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(0,0,0,0.04)';
                    e.currentTarget.style.color = 'var(--apple-text-secondary)';
                  }}
                >
                  {tag.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* User */}
        <div
          className="flex items-center justify-between px-3 py-2.5"
          style={{ borderTop: '0.5px solid var(--apple-border-light)' }}
        >
          {sidebarOpen && (
            <span style={{ fontSize: 12, color: 'var(--apple-text-secondary)', fontWeight: 500 }}>
              {username}
            </span>
          )}
          <button
            onClick={logout}
            title="退出登录"
            style={{
              width: 28,
              height: 28,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 6,
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              color: 'var(--apple-text-tertiary)',
              transition: 'all 0.15s',
              fontSize: 16,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--danger-bg)';
              e.currentTarget.style.color = 'var(--danger)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'var(--apple-text-tertiary)';
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
