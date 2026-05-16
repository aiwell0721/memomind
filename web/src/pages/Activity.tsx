import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { ActivityLog } from '../lib/api';

const actionConfig: Record<string, { icon: string; color: string }> = {
  create: { icon: 'create', color: 'var(--success)' },
  update: { icon: 'update', color: 'var(--accent)' },
  delete: { icon: 'delete', color: 'var(--danger)' },
  search: { icon: 'search', color: 'var(--apple-text-tertiary)' },
  login: { icon: 'login', color: 'var(--warning)' },
  workspace_create: { icon: 'workspace', color: 'var(--success)' },
  workspace_update: { icon: 'workspace', color: 'var(--accent)' },
  workspace_delete: { icon: 'workspace', color: 'var(--danger)' },
};

const actionIcons: Record<string, React.ReactNode> = {
  create: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  update: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  ),
  delete: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  ),
  search: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  login: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
      <polyline points="10 17 15 12 10 7" />
      <line x1="15" y1="12" x2="3" y2="12" />
    </svg>
  ),
  workspace: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  ),
};

export default function Activity() {
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState({ action: '', limit: 50 });

  useEffect(() => {
    loadActivity();
  }, [filter]);

  const loadActivity = async () => {
    setLoading(true);
    try {
      const data = await api.activity({
        action: filter.action || undefined,
        limit: filter.limit,
      });
      setLogs(data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (dateStr: string) => {
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
  };

  return (
    <div className="fade-in" style={{ padding: '2rem', maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.021em', marginBottom: '1.5rem' }}>
        活动日志
      </h1>

      {/* Filters */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <div className="flex gap-3 items-center" style={{ flexWrap: 'wrap' }}>
          <label style={{ fontSize: 13, color: 'var(--apple-text-secondary)' }}>动作:</label>
          <select
            value={filter.action}
            onChange={(e) => setFilter({ ...filter, action: e.target.value })}
            style={{
              padding: '0.375rem 0.625rem',
              border: '1px solid var(--apple-border)',
              borderRadius: 8,
              fontSize: 13,
              background: 'var(--apple-surface)',
              fontFamily: 'inherit',
              color: 'var(--apple-text)',
              outline: 'none',
            }}
          >
            <option value="">全部</option>
            <option value="create">创建</option>
            <option value="update">更新</option>
            <option value="delete">删除</option>
          </select>
          <label style={{ fontSize: 13, color: 'var(--apple-text-secondary)' }}>数量:</label>
          <select
            value={filter.limit}
            onChange={(e) => setFilter({ ...filter, limit: Number(e.target.value) })}
            style={{
              padding: '0.375rem 0.625rem',
              border: '1px solid var(--apple-border)',
              borderRadius: 8,
              fontSize: 13,
              background: 'var(--apple-surface)',
              fontFamily: 'inherit',
              color: 'var(--apple-text)',
              outline: 'none',
            }}
          >
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>

      {/* Timeline */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--apple-text-tertiary)', fontSize: 14 }}>
          加载中...
        </div>
      ) : logs.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--apple-text-tertiary)' }}>
          <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.4 }}>📋</div>
          <div style={{ fontSize: 14 }}>暂无活动记录</div>
        </div>
      ) : (
        <div className="card" style={{ padding: '0.5rem 0' }}>
          <div>
            {logs.map((log, i) => {
              const config = actionConfig[log.action] || { color: 'var(--apple-text-tertiary)' };
              const iconKey = log.action.startsWith('workspace') ? 'workspace' : log.action;
              return (
                <div
                  key={log.id}
                  style={{
                    display: 'flex',
                    gap: 14,
                    padding: '0.75rem 1.25rem',
                    borderBottom: i < logs.length - 1 ? '0.5px solid rgba(0,0,0,0.04)' : 'none',
                  }}
                >
                  <div style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: `${config.color}12`,
                    color: config.color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}>
                    {actionIcons[iconKey] || actionIcons.search}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="flex items-center gap-2" style={{ flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 13, fontWeight: 600, textTransform: 'capitalize' }}>
                        {log.action}
                      </span>
                      {log.note_id && (
                        <span className="badge badge-blue">
                          笔记 #{log.note_id}
                        </span>
                      )}
                      {log.workspace_id && (
                        <span className="badge badge-green">
                          工作区 #{log.workspace_id}
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: 12, color: 'var(--apple-text-tertiary)', marginTop: 2 }}>
                      {formatTime(log.created_at)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
