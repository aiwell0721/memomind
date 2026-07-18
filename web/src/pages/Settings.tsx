import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { toast } from '../App';
import type { Workspace, User, Backup } from '../lib/api';

/* ═══════════════════════════════════════════
   Tab Icons
   ═══════════════════════════════════════════ */

const tabIcons: Record<string, React.ReactNode> = {
  workspaces: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  ),
  users: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
  backups: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  ),
};

/* ── Format file size ── */
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/* ═══════════════════════════════════════════
   Confirm Delete Button (inline, not window.confirm)
   ═══════════════════════════════════════════ */

function ConfirmDelete({ onConfirm, message = '确定删除？' }: { onConfirm: () => void; message?: string }) {
  const [show, setShow] = useState(false);

  if (!show) {
    return (
      <button
        onClick={() => setShow(true)}
        className="btn-icon"
        style={{ width: 28, height: 28 }}
        title="删除"
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'var(--danger-bg)';
          e.currentTarget.style.color = 'var(--danger)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = 'var(--apple-text-tertiary)';
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
      </button>
    );
  }

  return (
    <div className="flex items-center gap-1" style={{ animation: 'slideInRight 0.2s var(--ease-spring)' }}>
      <span style={{ fontSize: 11, color: 'var(--danger)', whiteSpace: 'nowrap' }}>{message}</span>
      <button
        className="btn btn-danger btn-sm"
        style={{ padding: '0.125rem 0.5rem', fontSize: 11 }}
        onClick={onConfirm}
      >
        确认
      </button>
      <button
        className="btn btn-ghost btn-sm"
        style={{ padding: '0.125rem 0.5rem', fontSize: 11 }}
        onClick={() => setShow(false)}
      >
        取消
      </button>
    </div>
  );
}

/* ═══════════════════════════════════════════
   Settings Page
   ═══════════════════════════════════════════ */

export default function Settings() {
  const [activeTab, setActiveTab] = useState<'workspaces' | 'users' | 'backups'>('workspaces');
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [backups, setBackups] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  /* ── Form state ── */
  const [newWsName, setNewWsName] = useState('');
  const [newWsDesc, setNewWsDesc] = useState('');
  const [newUsername, setNewUsername] = useState('');

  /* ── Load data ── */
  useEffect(() => {
    if (activeTab === 'workspaces') api.workspaces().then(setWorkspaces).catch(() => {});
    else if (activeTab === 'users') api.users().then(setUsers).catch(() => {});
    else if (activeTab === 'backups') api.backups(50).then(setBackups).catch(() => {});
  }, [activeTab]);

  /* ── Workspace CRUD ── */
  const handleCreateWorkspace = async () => {
    if (!newWsName.trim()) { setError('请输入工作区名称'); return; }
    setLoading(true); setError('');
    try {
      await api.createWorkspace(newWsName.trim(), newWsDesc.trim());
      setNewWsName(''); setNewWsDesc('');
      toast('工作区已创建');
      api.workspaces().then(setWorkspaces);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally { setLoading(false); }
  };

  const handleDeleteWorkspace = async (id: number) => {
    try {
      await api.deleteWorkspace(id);
      toast('工作区已删除');
      api.workspaces().then(setWorkspaces);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  /* ── User CRUD ── */
  const handleCreateUser = async () => {
    const username = newUsername.trim();
    if (!username) { setError('请输入用户名'); return; }
    const password = window.prompt(`为用户 "${username}" 设置初始密码（至少 6 位）`)?.trim();
    if (!password || password.length < 6) { setError('密码至少 6 个字符'); return; }
    setLoading(true); setError('');
    try {
      await api.createUser(username, password, username);
      setNewUsername('');
      toast('用户已创建');
      api.users().then(setUsers);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally { setLoading(false); }
  };

  const handleDeleteUser = async (id: number) => {
    try {
      await api.deleteUser(id);
      toast('用户已删除');
      api.users().then(setUsers);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  /* ── Backup CRUD ── */
  const handleCreateBackup = async () => {
    setLoading(true); setError('');
    try {
      await api.createBackup('手动备份');
      toast('备份已创建');
      api.backups(50).then(setBackups);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '备份失败');
    } finally { setLoading(false); }
  };

  const handleDeleteBackup = async (id: number) => {
    try {
      await api.deleteBackup(id);
      toast('备份已删除');
      api.backups(50).then(setBackups);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const tabs = [
    { id: 'workspaces' as const, label: '工作区', count: workspaces.length },
    { id: 'users' as const, label: '用户', count: users.length },
    { id: 'backups' as const, label: '备份', count: backups.length },
  ];

  return (
    <div className="page-enter" style={{ padding: '0 2rem 2rem' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.021em', marginBottom: '1.5rem' }}>
        设置
      </h1>

      {/* ── Error ── */}
      {error && (
        <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: 'var(--danger-bg)', borderRadius: 10, color: 'var(--danger)', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* ═══ Segmented Control Tabs ═══ */}
      <div className="segmented-control" style={{ marginBottom: '1.5rem' }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`segmented-control-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => { setActiveTab(tab.id); setError(''); }}
          >
            {tabIcons[tab.id]}
            {tab.label}
            <span style={{
              fontSize: 10, fontWeight: 600, marginLeft: 2,
              background: activeTab === tab.id ? 'var(--accent-light)' : 'rgba(0,0,0,0.06)',
              color: activeTab === tab.id ? 'var(--accent)' : 'var(--apple-text-secondary)',
              borderRadius: 8, padding: '0 6px', minWidth: 20, textAlign: 'center',
            }}>
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* ═══════════════════════════════
         Workspaces Tab
         ═══════════════════════════════ */}
      {activeTab === 'workspaces' && (
        <div>
          {/* Create form */}
          <div className="card" style={{ marginBottom: '1rem' }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>新建工作区</h3>
            <div className="flex gap-2" style={{ marginBottom: 10, flexWrap: 'wrap' }}>
              <input
                type="text" value={newWsName} onChange={(e) => setNewWsName(e.target.value)}
                className="input" placeholder="工作区名称" style={{ flex: 1, minWidth: 140 }}
              />
              <input
                type="text" value={newWsDesc} onChange={(e) => setNewWsDesc(e.target.value)}
                className="input" placeholder="描述（可选）" style={{ flex: 2, minWidth: 200 }}
              />
            </div>
            <button className="btn btn-primary" onClick={handleCreateWorkspace} disabled={loading}>
              {loading ? '创建中...' : '创建工作区'}
            </button>
          </div>

          {/* Workspace list */}
          <div className="card" style={{ padding: '0.75rem 0' }}>
            <div style={{ padding: '0 1.25rem', marginBottom: 8, fontSize: 13, fontWeight: 600, color: 'var(--apple-text-secondary)' }}>
              工作区列表 ({workspaces.length})
            </div>
            {workspaces.length === 0 ? (
              <div className="empty-state" style={{ padding: '2rem 0' }}>
                <p style={{ fontSize: 13, color: 'var(--apple-text-tertiary)' }}>暂无工作区</p>
              </div>
            ) : (
              <div>
                {workspaces.map((ws) => (
                  <div
                    key={ws.id}
                    className="flex items-center justify-between"
                    style={{
                      padding: '0.625rem 1.25rem', transition: 'background 0.15s',
                      borderBottom: '0.5px solid var(--apple-border-light)',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(0,0,0,0.015)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 500 }}>{ws.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--apple-text-secondary)', marginTop: 2, display: 'flex', gap: 12 }}>
                        {ws.description && <span>{ws.description}</span>}
                        <span>ID: {ws.id}</span>
                        <span>创建于 {new Date(ws.created_at).toLocaleDateString('zh-CN')}</span>
                        {ws.note_count !== undefined && <span>{ws.note_count} 篇笔记</span>}
                      </div>
                    </div>
                    <ConfirmDelete onConfirm={() => handleDeleteWorkspace(ws.id)} message="删除？" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══════════════════════════════
         Users Tab
         ═══════════════════════════════ */}
      {activeTab === 'users' && (
        <div>
          <div className="card" style={{ marginBottom: '1rem' }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>新建用户</h3>
            <div className="flex gap-2">
              <input
                type="text" value={newUsername} onChange={(e) => setNewUsername(e.target.value)}
                className="input" placeholder="用户名" style={{ flex: 1 }}
              />
              <button className="btn btn-primary" onClick={handleCreateUser} disabled={loading}>
                {loading ? '创建中...' : '创建用户'}
              </button>
            </div>
          </div>

          <div className="card" style={{ padding: '0.75rem 0' }}>
            <div style={{ padding: '0 1.25rem', marginBottom: 8, fontSize: 13, fontWeight: 600, color: 'var(--apple-text-secondary)' }}>
              用户列表 ({users.length})
            </div>
            {users.length === 0 ? (
              <div className="empty-state" style={{ padding: '2rem 0' }}>
                <p style={{ fontSize: 13, color: 'var(--apple-text-tertiary)' }}>暂无用户</p>
              </div>
            ) : (
              <div>
                {users.map((user) => (
                  <div
                    key={user.id}
                    className="flex items-center justify-between"
                    style={{
                      padding: '0.625rem 1.25rem', transition: 'background 0.15s',
                      borderBottom: '0.5px solid var(--apple-border-light)',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(0,0,0,0.015)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span style={{
                          width: 26, height: 26, borderRadius: '50%',
                          background: 'linear-gradient(135deg, var(--accent-light), var(--accent-lighter))',
                          color: 'var(--accent)', fontSize: 11, fontWeight: 600,
                          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                          {user.username.charAt(0).toUpperCase()}
                        </span>
                        <span style={{ fontSize: 13, fontWeight: 500 }}>{user.username}</span>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--apple-text-secondary)', marginTop: 2, marginLeft: 34 }}>
                        {user.display_name} · 创建于 {new Date(user.created_at).toLocaleDateString('zh-CN')}
                      </div>
                    </div>
                    <ConfirmDelete onConfirm={() => handleDeleteUser(user.id)} message="删除？" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══════════════════════════════
         Backups Tab
         ═══════════════════════════════ */}
      {activeTab === 'backups' && (
        <div>
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="flex items-center justify-between">
              <h3 style={{ fontSize: 14, fontWeight: 600 }}>备份列表 ({backups.length})</h3>
              <button className="btn btn-primary btn-sm" onClick={handleCreateBackup} disabled={loading}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                {loading ? '备份中...' : '创建备份'}
              </button>
            </div>
          </div>

          {backups.length === 0 ? (
            <div className="card empty-state" style={{ padding: '3rem 1.5rem' }}>
              <svg className="empty-state-icon" viewBox="0 0 120 100" fill="none">
                <ellipse cx="60" cy="35" rx="30" ry="10" stroke="currentColor" strokeWidth="2.5" fill="none" opacity="0.5" />
                <path d="M30 35v30c0 5.5 13.4 10 30 10s30-4.5 30-10V35" stroke="currentColor" strokeWidth="2.5" fill="none" opacity="0.5" />
                <path d="M30 50c0 5.5 13.4 10 30 10s30-4.5 30-10" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.3" />
              </svg>
              <h3 className="empty-state-title">暂无备份</h3>
              <p className="empty-state-desc">安全第一，创建数据库备份</p>
              <button className="btn btn-primary btn-sm" onClick={handleCreateBackup}>
                创建第一个备份
              </button>
            </div>
          ) : (
            <div className="card" style={{ padding: '0.75rem 0' }}>
              {backups.map((backup) => (
                <div
                  key={backup.id}
                  className="flex items-center justify-between"
                  style={{
                    padding: '0.625rem 1.25rem', transition: 'background 0.15s',
                    borderBottom: '0.5px solid var(--apple-border-light)',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(0,0,0,0.015)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div className="flex items-center gap-2">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round">
                        <ellipse cx="12" cy="5" rx="9" ry="3" />
                        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                      </svg>
                      <span style={{ fontSize: 13, fontWeight: 500 }}>{backup.description || '自动备份'}</span>
                      <span className="badge badge-gray" style={{ fontSize: 10 }}>{formatSize(backup.size)}</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--apple-text-secondary)', marginTop: 2, display: 'flex', gap: 12 }}>
                      <span>创建于 {new Date(backup.created_at).toLocaleString('zh-CN')}</span>
                      <span>ID: {backup.id}</span>
                    </div>
                  </div>
                  <ConfirmDelete onConfirm={() => handleDeleteBackup(backup.id)} message="删除备份？" />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
