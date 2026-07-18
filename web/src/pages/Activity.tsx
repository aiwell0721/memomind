import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { ActivityLog } from '../lib/api';

/* ═══════════════════════════════════════════
   Config & Helpers
   ═══════════════════════════════════════════ */

const actionConfig: Record<string, { label: string; color: string; icon: string }> = {
  create:             { label: '创建了笔记',     color: 'var(--success)', icon: 'create' },
  update:             { label: '更新了笔记',     color: 'var(--accent)',  icon: 'update' },
  delete:             { label: '删除了笔记',     color: 'var(--danger)',  icon: 'delete' },
  search:             { label: '搜索了笔记',     color: 'var(--apple-text-tertiary)', icon: 'search' },
  login:              { label: '登录了系统',     color: 'var(--warning)', icon: 'login' },
  workspace_create:   { label: '创建了工作区',   color: 'var(--success)', icon: 'workspace' },
  workspace_update:   { label: '更新了工作区',   color: 'var(--accent)',  icon: 'workspace' },
  workspace_delete:   { label: '删除了工作区',   color: 'var(--danger)',  icon: 'workspace' },
};

const actionIcons: Record<string, React.ReactNode> = {
  create: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  update: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  ),
  delete: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  ),
  search: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  login: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
      <polyline points="10 17 15 12 10 7" /><line x1="15" y1="12" x2="3" y2="12" />
    </svg>
  ),
  workspace: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  ),
};

type FilterAction = 'all' | 'create' | 'update' | 'delete' | 'workspace';

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHr = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return `${diffMin} 分钟前`;
  if (diffHr < 24) return `${diffHr} 小时前`;
  if (diffDay < 7) return `${diffDay} 天前`;
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

/** Group logs by date: today, yesterday, older */
function groupByDate(logs: ActivityLog[]): { label: string; items: ActivityLog[] }[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);

  const groups: Record<string, ActivityLog[]> = {};

  for (const log of logs) {
    const d = new Date(log.created_at);
    const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());

    let key: string;
    if (day.getTime() >= today.getTime()) key = '今天';
    else if (day.getTime() >= yesterday.getTime()) key = '昨天';
    else key = d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });

    if (!groups[key]) groups[key] = [];
    groups[key].push(log);
  }

  return Object.entries(groups).map(([label, items]) => ({ label, items }));
}

/* ═══════════════════════════════════════════
   Activity Page
   ═══════════════════════════════════════════ */

export default function Activity() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<FilterAction>('all');
  const [limit, setLimit] = useState(50);

  useEffect(() => {
    loadActivity();
  }, [filter, limit]);

  const loadActivity = async () => {
    setLoading(true);
    try {
      const actionParam = filter === 'all' ? undefined
        : filter === 'workspace' ? undefined
        : filter;
      const data = await api.activity({ action: actionParam, limit });
      // Client-side workspace filter
      const filtered = filter === 'workspace'
        ? data.filter((l) => l.action.startsWith('workspace'))
        : data;
      setLogs(filtered);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  const filterTabs: { id: FilterAction; label: string }[] = [
    { id: 'all', label: '全部' },
    { id: 'create', label: '创建' },
    { id: 'update', label: '更新' },
    { id: 'delete', label: '删除' },
    { id: 'workspace', label: '工作区' },
  ];

  const groups = groupByDate(logs);

  return (
    <div className="page-enter" style={{ padding: '0 2rem 2rem' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.021em', marginBottom: '1.5rem' }}>
        活动日志
      </h1>

      {/* ── Segmented Control Filter ── */}
      <div className="segmented-control" style={{ marginBottom: '1.25rem' }}>
        {filterTabs.map((tab) => (
          <button
            key={tab.id}
            className={`segmented-control-btn ${filter === tab.id ? 'active' : ''}`}
            onClick={() => setFilter(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Limit selector ── */}
      <div className="flex items-center gap-2" style={{ marginBottom: '1.25rem' }}>
        <span style={{ fontSize: 13, color: 'var(--apple-text-secondary)' }}>显示</span>
        {[20, 50, 100].map((n) => (
          <button
            key={n}
            onClick={() => setLimit(n)}
            style={{
              padding: '2px 10px', borderRadius: 6, fontSize: 12, fontWeight: 500,
              border: 'none', cursor: 'pointer', fontFamily: 'inherit',
              background: limit === n ? 'var(--accent-light)' : 'transparent',
              color: limit === n ? 'var(--accent)' : 'var(--apple-text-secondary)',
            }}
          >
            {n}
          </button>
        ))}
        <span style={{ fontSize: 13, color: 'var(--apple-text-secondary)' }}>条</span>
      </div>

      {/* ── Content ── */}
      {loading ? (
        <div>
          {[1, 2, 3].map((i) => (
            <div key={i} className="card" style={{ marginBottom: 8, padding: '1rem 1.25rem' }}>
              <div className="skeleton skeleton-text" style={{ width: '50%', height: 14 }} />
              <div className="skeleton skeleton-text" style={{ width: '30%' }} />
            </div>
          ))}
        </div>
      ) : logs.length === 0 ? (
        <div className="empty-state">
          <svg className="empty-state-icon" viewBox="0 0 120 100" fill="none">
            <polyline points="22 32 18 22 32 22 18 38" stroke="currentColor" strokeWidth="2.5" fill="none" opacity="0.5" strokeLinecap="round" strokeLinejoin="round" />
            <rect x="35" y="18" width="70" height="64" rx="6" stroke="currentColor" strokeWidth="2.5" fill="none" opacity="0.5" />
            <line x1="44" y1="34" x2="70" y2="34" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
            <line x1="44" y1="46" x2="80" y2="46" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
            <line x1="44" y1="58" x2="60" y2="58" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.2" />
          </svg>
          <h3 className="empty-state-title">暂无活动记录</h3>
          <p className="empty-state-desc">系统操作记录将显示在这里</p>
        </div>
      ) : (
        <div className="card" style={{ padding: '0.5rem 0' }}>
          {groups.map((group) => (
            <div key={group.label}>
              {/* Date header */}
              <div style={{
                padding: '0.5rem 1.25rem', fontSize: 12, fontWeight: 600,
                color: 'var(--apple-text-secondary)', letterSpacing: '0.02em',
                borderBottom: '0.5px solid var(--apple-border-light)',
              }}>
                {group.label}
              </div>

              {/* Timeline items */}
              <div className="timeline" style={{ padding: '0.5rem 1.25rem 0.25rem 2.5rem' }}>
                {group.items.map((log) => {
                  const config = actionConfig[log.action] || {
                    label: log.action, color: 'var(--apple-text-tertiary)', icon: 'search',
                  };
                  const iconKey = log.action.startsWith('workspace') ? 'workspace' : log.action;

                  return (
                    <div key={log.id} className="timeline-item">
                      <span className="timeline-dot" style={{ background: config.color }} />
                      <div style={{
                        padding: '0.5rem 0.75rem', background: 'var(--apple-bg)',
                        borderRadius: 8, display: 'flex', alignItems: 'flex-start',
                        gap: 10, cursor: log.note_id ? 'pointer' : 'default',
                      }}
                        onClick={() => { if (log.note_id) navigate(`/notes/${log.note_id}`); }}
                      >
                        {/* Icon */}
                        <span style={{
                          width: 28, height: 28, borderRadius: 8,
                          background: `${config.color}14`,
                          color: config.color, display: 'flex',
                          alignItems: 'center', justifyContent: 'center',
                          flexShrink: 0,
                        }}>
                          {actionIcons[iconKey] || actionIcons.search}
                        </span>

                        {/* Content */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 13, fontWeight: 500 }}>
                            {config.label}
                            {log.note_id && (
                              <span className="badge badge-blue" style={{ marginLeft: 8, cursor: 'pointer' }}>
                                #{log.note_id}
                              </span>
                            )}
                            {log.workspace_id && (
                              <span className="badge badge-green" style={{ marginLeft: 4 }}>
                                WS #{log.workspace_id}
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--apple-text-tertiary)', marginTop: 2 }}>
                            {formatTime(log.created_at)}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
