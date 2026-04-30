import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { Workspace, User, Backup } from '../lib/api';

export default function Settings() {
  const [activeTab, setActiveTab] = useState<'workspaces' | 'users' | 'backups'>('workspaces');
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [backups, setBackups] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Workspace state
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [newWorkspaceDesc, setNewWorkspaceDesc] = useState('');

  // User state
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
    { id: 'workspaces' as const, label: '🏢 工作区' },
    { id: 'users' as const, label: '👥 用户' },
    { id: 'backups' as const, label: '💾 备份' },
  ];

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">⚙️ 设置</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setError(''); }}
            className={`px-4 py-2 border-b-2 transition ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600 font-medium'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Workspaces */}
      {activeTab === 'workspaces' && (
        <div className="space-y-4">
          <div className="card">
            <h3 className="font-medium mb-3">新建工作区</h3>
            <div className="flex gap-2">
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
              <button
                className="btn btn-primary"
                onClick={handleCreateWorkspace}
                disabled={loading}
              >
                创建
              </button>
            </div>
          </div>

          <div className="card">
            <h3 className="font-medium mb-3">工作区列表 ({workspaces.length})</h3>
            {workspaces.length === 0 ? (
              <p className="text-gray-400 text-center py-4">暂无工作区</p>
            ) : (
              <div className="space-y-2">
                {workspaces.map((ws) => (
                  <div
                    key={ws.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded"
                  >
                    <div>
                      <span className="font-medium">{ws.name}</span>
                      {ws.description && (
                        <span className="text-sm text-gray-400 ml-2">{ws.description}</span>
                      )}
                    </div>
                    <button
                      className="p-1 text-red-400 hover:text-red-600 transition"
                      onClick={() => handleDeleteWorkspace(ws.id)}
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Users */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="card">
            <h3 className="font-medium mb-3">新建用户</h3>
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
            <h3 className="font-medium mb-3">用户列表 ({users.length})</h3>
            {users.length === 0 ? (
              <p className="text-gray-400 text-center py-4">暂无用户</p>
            ) : (
              <div className="space-y-2">
                {users.map((user) => (
                  <div
                    key={user.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded"
                  >
                    <div>
                      <span className="font-medium">{user.username}</span>
                      {user.display_name && (
                        <span className="text-sm text-gray-400 ml-2">{user.display_name}</span>
                      )}
                    </div>
                    <button
                      className="p-1 text-red-400 hover:text-red-600 transition"
                      onClick={() => handleDeleteUser(user.id)}
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Backups */}
      {activeTab === 'backups' && (
        <div className="space-y-4">
          <div className="card">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">备份列表 ({backups.length})</h3>
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
            <div className="card text-center text-gray-400 py-8">暂无备份</div>
          ) : (
            <div className="card">
              <div className="space-y-2">
                {backups.map((backup) => (
                  <div
                    key={backup.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded"
                  >
                    <div>
                      <span className="font-medium">
                        {backup.description || '自动备份'}
                      </span>
                      <span className="text-sm text-gray-400 ml-2">
                        {new Date(backup.created_at).toLocaleString()}
                      </span>
                      {backup.size && (
                        <span className="text-xs text-gray-400 ml-2">
                          ({(backup.size / 1024).toFixed(1)} KB)
                        </span>
                      )}
                    </div>
                    <button
                      className="p-1 text-red-400 hover:text-red-600 transition"
                      onClick={() => handleDeleteBackup(backup.id)}
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
