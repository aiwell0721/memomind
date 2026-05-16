import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { Workspace, User, Backup } from '../lib/api';

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

export default function Settings() {
  const [activeTab, setActiveTab] = useState<'workspaces' | 'users' | 'backups'>('workspaces');
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [backups, setBackups] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [newWorkspaceDesc, setNewWorkspaceDesc] = useState('');
  const [newUsername, setNewUsername] = useState('');

  useEffect(() => {
    if (activeTab === 'workspaces') {
      api.workspaces().then(setWorkspaces).catch(() => {});
    } else if (activeTab === 'users') {
      api.users().then(setUsers).catch(() => {});
    } else if (activeTab === 'backups') {
      api.backups(20).then(setBackups).catch(() => {});
    }
  }, [activeTab]);

  const handleCreateWorkspace = async () => {
    if (!newWorkspaceName.trim()) return;
    setLoading(true);
    try {
      await api.createWorkspace(newWorkspaceName.trim(), newWorkspaceDesc);
      setNewWorkspaceName('');
      setNewWorkspaceDesc('');
      api.workspaces().then(setWorkspaces);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteWorkspace = async (id: number) => {
    if (!confirm('确定删除此工作区？其中笔记也会被删除。')) return;
    try {
      await api.deleteWorkspace(id);
      api.workspaces().then(setWorkspaces);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const handleCreateUser = async () => {
    if (!newUsername.trim()) return;
    setLoading(true);
    try {
      await api.createUser(newUsername.trim());
      setNewUsername('');
      api.users().then(setUsers);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (id: number) => {
    if (!confirm('确定删除此用户？')) return;
    try {
      await api.deleteUser(id);
      api.users().then(setUsers);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const handleCreateBackup = async () => {
    setLoading(true);
    try {
      await api.createBackup('手动备份');
      api.backups(20).then(setBackups);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '备份失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteBackup = async (id: number) => {
    if (!confirm('确定删除此备份？')) return;
    try {
      await api.deleteBackup(id);
      api.backups(20).then(setBackups);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const tabs = [
    { id: 'workspaces' as const, label: '工作区' },
    { id: 'users' as const, label: '用户' },
    { id: 'backups' as const, label: '备份' },
  ];

  // Reusable row with delete button
  const ListItem = ({
    primary,
    secondary,
    onRemove,
  }: {
    primary: string;
    secondary?: string;
    onRemove: () => void;
  }) => (
    <div
      className="flex items-center justify-between"
      style={{
        padding: '0.625rem 0.875rem',
        background: 'var(--apple-bg)',
        borderRadius: 8,
        marginBottom: 6,
        transition: 'background 0.15s',
      }}
    >
      <div>
        <span style={{ fontSize: 13, fontWeight: 500 }}>{primary}</span>
        {secondary && (
          <span style={{ fontSize: 12, color: 'var(--apple-text-secondary)', marginLeft: 8 }}>
            {secondary}
          </span>
        )}
      </div>
      <button
        onClick={onRemove}
        style={{
          width: 24,
          height: 24,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 6,
          border: 'none',
          background: 'transparent',
          cursor: 'pointer',
          color: 'var(--apple-text-tertiary)',
          transition: 'all 0.15s',
          opacity: 0.4,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.opacity = '1';
          e.currentTarget.style.background = 'var(--danger-bg)';
          e.currentTarget.style.color = 'var(--danger)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.opacity = '0.4';
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = 'var(--apple-text-tertiary)';
        }}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
      </button>
    </div>
  );

  return (
    <div className="fade-in" style={{ padding: '2rem', maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.021em', marginBottom: '1.5rem' }}>
        设置
      </h1>

      {error && (
        <div style={{
          marginBottom: '1rem',
          padding: '0.75rem 1rem',
          background: 'var(--danger-bg)',
          borderRadius: 10,
          color: 'var(--danger)',
          fontSize: 13,
        }}>
          {error}
        </div>
      )}

      {/* Tabs — Apple segmented control style */}
      <div
        style={{
          display: 'flex',
          background: 'rgba(0,0,0,0.04)',
          borderRadius: 10,
          padding: 2,
          marginBottom: '1.5rem',
        }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setError(''); }}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              padding: '0.5rem 0.75rem',
              fontSize: 13,
              fontWeight: 500,
              fontFamily: 'inherit',
              border: 'none',
              borderRadius: 8,
              cursor: 'pointer',
              transition: 'all 0.2s',
              background: activeTab === tab.id ? 'var(--apple-surface)' : 'transparent',
              color: activeTab === tab.id ? 'var(--apple-text)' : 'var(--apple-text-secondary)',
              boxShadow: activeTab === tab.id ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
            }}
          >
            {tabIcons[tab.id]}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Workspaces */}
      {activeTab === 'workspaces' && (
        <div>
          <div className="card" style={{ marginBottom: '1rem' }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>新建工作区</h3>
            <div className="flex gap-2" style={{ marginBottom: 8 }}>
              <input
                type="text"
                value={newWorkspaceName}
                onChange={(e) => setNewWorkspaceName(e.target.value)}
                className="input"
                placeholder="工作区名称"
              />
              <input
                type="text"
                value={newWorkspaceDesc}
                onChange={(e) => setNewWorkspaceDesc(e.target.value)}
                className="input"
                placeholder="描述（可选）"
              />
            </div>
            <button
              className="btn btn-primary"
              onClick={handleCreateWorkspace}
              disabled={loading}
            >
              创建
            </button>
          </div>

          <div className="card">
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
              工作区列表 ({workspaces.length})
            </h3>
            {workspaces.length === 0 ? (
              <p style={{ textAlign: 'center', padding: '1.5rem 0', color: 'var(--apple-text-tertiary)', fontSize: 13 }}>
                暂无工作区
              </p>
            ) : (
              <div>
                {workspaces.map((ws) => (
                  <ListItem
                    key={ws.id}
                    primary={ws.name}
                    secondary={ws.description}
                    onRemove={() => handleDeleteWorkspace(ws.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Users */}
      {activeTab === 'users' && (
        <div>
          <div className="card" style={{ marginBottom: '1rem' }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>新建用户</h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                className="input"
                placeholder="用户名"
              />
              <button
                className="btn btn-primary"
                onClick={handleCreateUser}
                disabled={loading}
              >
                创建
              </button>
            </div>
          </div>

          <div className="card">
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
              用户列表 ({users.length})
            </h3>
            {users.length === 0 ? (
              <p style={{ textAlign: 'center', padding: '1.5rem 0', color: 'var(--apple-text-tertiary)', fontSize: 13 }}>
                暂无用户
              </p>
            ) : (
              <div>
                {users.map((user) => (
                  <ListItem
                    key={user.id}
                    primary={user.username}
                    secondary={user.display_name}
                    onRemove={() => handleDeleteUser(user.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Backups */}
      {activeTab === 'backups' && (
        <div>
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="flex items-center justify-between">
              <h3 style={{ fontSize: 14, fontWeight: 600 }}>
                备份列表 ({backups.length})
              </h3>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleCreateBackup}
                disabled={loading}
              >
                + 创建备份
              </button>
            </div>
          </div>

          {backups.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--apple-text-tertiary)', fontSize: 13 }}>
              暂无备份
            </div>
          ) : (
            <div className="card">
              <div>
                {backups.map((backup) => (
                  <ListItem
                    key={backup.id}
                    primary={backup.description || '自动备份'}
                    secondary={`${new Date(backup.created_at).toLocaleString()}${backup.size ? ` (${(backup.size / 1024).toFixed(1)} KB)` : ''}`}
                    onRemove={() => handleDeleteBackup(backup.id)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
