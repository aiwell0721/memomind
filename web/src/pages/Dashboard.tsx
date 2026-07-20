import { useState, useEffect, useRef } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../App';
import { api } from '../lib/api';
import type { Workspace, Tag } from '../lib/api';

/* ═══════════════════════════════════════════
   Navigation Items
   ═══════════════════════════════════════════ */

const navItems = [
  { path: '/', icon: 'note', label: '笔记' },
  { path: '/tags', icon: 'tag', label: '标签' },
  { path: '/ai', icon: 'ai', label: 'AI 问答' },
  { path: '/dreaming', icon: 'dreaming', label: '记忆整理' },
  { path: '/activity', icon: 'activity', label: '活动日志' },
  { path: '/settings', icon: 'settings', label: '设置' },
];

/* ── SVG Icons ── */
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
  ai: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-4 4 4 4 0 0 1-4-4V6a4 4 0 0 1 4-4z" />
      <path d="M12 14v2" />
      <path d="M12 18a6 6 0 0 0 6-6h2a8 8 0 0 1-16 0h2a6 6 0 0 0 6 6z" />
      <line x1="8.5" y1="3.5" x2="15.5" y2="10.5" />
      <line x1="15.5" y1="3.5" x2="8.5" y2="10.5" />
    </svg>
  ),
  settings: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  ),
  chevron: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  ),
  plus: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  logout: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  ),
  search: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  dreaming: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  ),
};

/* ═══════════════════════════════════════════
   Workspace Dropdown (custom, not native)
   ═══════════════════════════════════════════ */

function WorkspaceDropdown({
  workspaces, selected, onChange,
}: {
  workspaces: Workspace[];
  selected: number | null;
  onChange: (id: number | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selectedWs = workspaces.find((w) => w.id === selected);
  const filtered = workspaces.filter((w) =>
    w.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div ref={ref} style={{ position: 'relative', width: '100%' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          gap: 8, padding: '6px 10px', borderRadius: 'var(--radius-sm)',
          border: '0.5px solid var(--apple-border)', background: 'var(--apple-surface)',
          fontSize: 12, fontWeight: 500, color: 'var(--apple-text)',
          cursor: 'pointer', fontFamily: 'inherit',
          transition: 'all 0.15s var(--ease-smooth)',
        }}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {selectedWs ? (
            <span className="flex items-center gap-2">
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--apple-accent)', flexShrink: 0 }} />
              {selectedWs.name}
            </span>
          ) : (
            <span style={{ color: 'var(--apple-text-secondary)' }}>全部工作区</span>
          )}
        </span>
        <span style={{
          transform: open ? 'rotate(180deg)' : 'none',
          transition: 'transform 0.2s var(--ease-smooth)',
          color: 'var(--apple-text-tertiary)',
          display: 'flex',
        }}>
          {icons.chevron}
        </span>
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 50,
          background: 'var(--apple-surface)', borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-lg)', border: '0.5px solid var(--apple-border-light)',
          overflow: 'hidden', animation: 'scaleIn 0.15s var(--ease-spring)',
        }}>
          {/* Search */}
          <div style={{ padding: '6px 8px', borderBottom: '0.5px solid var(--apple-border-light)' }}>
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', opacity: 0.35, display: 'flex' }}>
                {icons.search}
              </span>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索工作区..."
                style={{
                  width: '100%', padding: '4px 8px 4px 28px', fontSize: 12,
                  border: 'none', borderRadius: 6, background: 'var(--apple-bg)',
                  color: 'var(--apple-text)', outline: 'none', fontFamily: 'inherit',
                }}
              />
            </div>
          </div>

          {/* List */}
          <div style={{ maxHeight: 180, overflowY: 'auto', padding: '4px 0' }}>
            <button
              onClick={() => { onChange(null); setOpen(false); }}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 10px', border: 'none', background: !selected ? 'var(--apple-accent-light)' : 'transparent',
                color: !selected ? 'var(--apple-accent)' : 'var(--apple-text-secondary)',
                fontSize: 12, fontWeight: !selected ? 600 : 400, cursor: 'pointer',
                fontFamily: 'inherit', textAlign: 'left',
              }}
            >
              全部工作区
            </button>
            {filtered.map((ws) => (
              <button
                key={ws.id}
                onClick={() => { onChange(ws.id); setOpen(false); }}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                  padding: '6px 10px', border: 'none',
                  background: selected === ws.id ? 'var(--apple-accent-light)' : 'transparent',
                  color: selected === ws.id ? 'var(--apple-accent)' : 'var(--apple-text)',
                  fontSize: 12, fontWeight: selected === ws.id ? 600 : 400,
                  cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--apple-accent)', flexShrink: 0 }} />
                {ws.name}
                {ws.note_count !== undefined && (
                  <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--apple-text-tertiary)' }}>
                    {ws.note_count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════
   Color dot palette for tags
   ═══════════════════════════════════════════ */

const dotColors = [
  '#0071e3', '#30b158', '#f09824', '#ee4b40',
  '#ac4ee0', '#ff69b4', '#00b8b0', '#ff9500',
];

function TagDot({ index }: { index: number }) {
  return (
    <span style={{
      width: 7, height: 7, borderRadius: '50%',
      background: dotColors[index % dotColors.length],
      flexShrink: 0,
    }} />
  );
}

/* ═══════════════════════════════════════════
   Main Dashboard Component
   ═══════════════════════════════════════════ */

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

  // Flatten tag tree for display
  const flatTags = (tagList: Tag[]): Tag[] =>
    tagList.flatMap((t) => [t, ...flatTags(t.children || [])]);

  const allTags = flatTags(tags);

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--apple-bg)' }}>
      {/* ═══ Sidebar (glass morphism) ═══ */}
      <aside
        className="sidebar flex flex-col transition-all duration-300 ease-in-out"
        style={{ width: sidebarOpen ? 248 : 56 }}
      >
        {/* ── Logo Bar ── */}
        <div
          className="flex items-center justify-between"
          style={{
            padding: sidebarOpen ? '0.625rem 0.75rem' : '0.625rem 0.5rem',
            borderBottom: '0.5px solid var(--apple-border-light)',
            minHeight: 48,
          }}
        >
          {sidebarOpen ? (
            <div className="flex items-center gap-2" style={{ minWidth: 0 }}>
              <span style={{ fontSize: 20, flexShrink: 0 }}>
                <svg width="22" height="22" viewBox="0 0 56 56" fill="none">
                  <defs>
                    <linearGradient id="sbGrad" x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
                      <stop stopColor="#0071e3" /><stop offset="1" stopColor="#40a4ff" />
                    </linearGradient>
                  </defs>
                  <rect x="4" y="8" width="38" height="44" rx="6" stroke="url(#sbGrad)" strokeWidth="3" fill="none" />
                  <line x1="14" y1="22" x2="32" y2="22" stroke="url(#sbGrad)" strokeWidth="2.5" strokeLinecap="round" />
                  <line x1="14" y1="30" x2="32" y2="30" stroke="url(#sbGrad)" strokeWidth="2.5" strokeLinecap="round" />
                </svg>
              </span>
              <span style={{ fontWeight: 700, fontSize: 15, letterSpacing: '-0.02em', whiteSpace: 'nowrap' }}>
                MemoMind{import.meta.env.DEV && <span style={{fontWeight:400, fontSize:11, opacity:.5}}>(Dev)</span>}
              </span>
              {health && (
                <span style={{
                  fontSize: 10, background: 'rgba(0,0,0,0.06)', padding: '1px 6px',
                  borderRadius: 6, color: 'var(--apple-text-secondary)', fontWeight: 500,
                  flexShrink: 0,
                }}>
                  v{health.version}
                </span>
              )}
            </div>
          ) : (
            <span style={{ fontSize: 20, margin: '0 auto' }}>
              <svg width="22" height="22" viewBox="0 0 56 56" fill="none">
                <defs>
                  <linearGradient id="sbGrad2" x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#0071e3" /><stop offset="1" stopColor="#40a4ff" />
                  </linearGradient>
                </defs>
                <rect x="4" y="8" width="38" height="44" rx="6" stroke="url(#sbGrad2)" strokeWidth="3" fill="none" />
                <line x1="14" y1="22" x2="32" y2="22" stroke="url(#sbGrad2)" strokeWidth="2.5" strokeLinecap="round" />
                <line x1="14" y1="30" x2="32" y2="30" stroke="url(#sbGrad2)" strokeWidth="2.5" strokeLinecap="round" />
              </svg>
            </span>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="btn-icon"
            style={{ width: 28, height: 28, flexShrink: 0 }}
            title={sidebarOpen ? '收起侧边栏' : '展开侧边栏'}
          >
            <span style={{
              transform: sidebarOpen ? 'rotate(180deg)' : 'none',
              transition: 'transform 0.2s var(--ease-smooth)',
              display: 'flex',
            }}>
              {icons.chevron}
            </span>
          </button>
        </div>

        {/* ── Workspace Selector ── */}
        {sidebarOpen && workspaces.length > 0 && (
          <div style={{ padding: '0.625rem 0.75rem', borderBottom: '0.5px solid var(--apple-border-light)' }}>
            <div className="sidebar-section-label">工作区</div>
            <div style={{ marginTop: 4 }}>
              <WorkspaceDropdown
                workspaces={workspaces}
                selected={selectedWorkspace}
                onChange={handleWorkspaceChange}
              />
            </div>
          </div>
        )}

        {/* ── Nav ── */}
        <nav className="flex-1" style={{ padding: '0.5rem', overflowY: 'auto' }}>
          {sidebarOpen && <div className="sidebar-section-label">导航</div>}
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`sidebar-item ${isActive ? 'active' : ''}`}
                title={!sidebarOpen ? item.label : undefined}
                style={{ justifyContent: sidebarOpen ? 'flex-start' : 'center' }}
              >
                <span style={{ opacity: isActive ? 1 : 0.6, display: 'flex', flexShrink: 0 }}>
                  {icons[item.icon]}
                </span>
                {sidebarOpen && <span>{item.label}</span>}
              </button>
            );
          })}
        </nav>

        {/* ── Tags (compact sidebar list) ── */}
        {sidebarOpen && allTags.length > 0 && (
          <div style={{ padding: '0.5rem 0.75rem', borderTop: '0.5px solid var(--apple-border-light)' }}>
            <div className="sidebar-section-label">标签</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6, maxHeight: 120, overflowY: 'auto' }}>
              {allTags.slice(0, 15).map((tag, i) => (
                <span
                  key={tag.id}
                  onClick={() => navigate(`/?tag=${tag.name}`)}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 4,
                    padding: '3px 8px', borderRadius: 6, fontSize: 11,
                    background: 'rgba(0,0,0,0.04)', color: 'var(--apple-text-secondary)',
                    cursor: 'pointer', transition: 'all 0.15s',
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
                  <TagDot index={i} />
                  {tag.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* ── User Footer ── */}
        <div
          className="flex items-center justify-between"
          style={{
            padding: sidebarOpen ? '0.5rem 0.75rem' : '0.5rem',
            borderTop: '0.5px solid var(--apple-border-light)',
            minHeight: 44,
          }}
        >
          {sidebarOpen && (
            <div className="flex items-center gap-2" style={{ minWidth: 0 }}>
              {/* Avatar */}
              <div style={{
                width: 26, height: 26, borderRadius: '50%',
                background: 'linear-gradient(135deg, var(--apple-accent), #40a4ff)',
                color: 'white', fontSize: 11, fontWeight: 600,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                {username?.charAt(0).toUpperCase()}
              </div>
              <span style={{ fontSize: 12, color: 'var(--apple-text-secondary)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {username}
              </span>
            </div>
          )}
          <button
            onClick={logout}
            title="退出登录"
            className="btn-icon"
            style={{ width: 28, height: 28, flexShrink: 0, marginLeft: sidebarOpen ? 0 : 'auto', marginRight: sidebarOpen ? 0 : 'auto' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--danger-bg)';
              e.currentTarget.style.color = 'var(--danger)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'var(--apple-text-tertiary)';
            }}
          >
            {icons.logout}
          </button>
        </div>
      </aside>

      {/* ═══ Main Content ═══ */}
      <main className="flex-1 overflow-auto" style={{ position: 'relative', paddingTop: '2rem' }}>
        <Outlet />
      </main>
    </div>
  );
}
