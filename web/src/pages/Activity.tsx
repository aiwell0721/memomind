import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { ActivityLog } from '../lib/api';

const actionIcons: Record<string, string> = {
  create: '📝',
  update: '✏️',
  delete: '🗑️',
  search: '🔍',
  login: '🔑',
  workspace_create: '🏢',
  workspace_update: '🏢',
  workspace_delete: '🏢',
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

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">📋 活动日志</h1>

      {/* Filters */}
      <div className="card mb-4">
        <div className="flex gap-3 items-center">
          <label className="text-sm text-gray-500">动作:</label>
          <select
            value={filter.action}
            onChange={(e) => setFilter({ ...filter, action: e.target.value })}
            className="input w-40"
          >
            <option value="">全部</option>
            <option value="create">创建</option>
            <option value="update">更新</option>
            <option value="delete">删除</option>
          </select>
          <label className="text-sm text-gray-500">数量:</label>
          <select
            value={filter.limit}
            onChange={(e) => setFilter({ ...filter, limit: Number(e.target.value) })}
            className="input w-24"
          >
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>
        </div>
      </div>

      {/* Timeline */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">加载中...</div>
      ) : logs.length === 0 ? (
        <div className="text-center py-12 text-gray-400">暂无活动记录</div>
      ) : (
        <div className="card">
          <div className="space-y-0">
            {logs.map((log, i) => (
              <div
                key={log.id}
                className={`flex gap-3 py-3 ${
                  i < logs.length - 1 ? 'border-b border-gray-100' : ''
                }`}
              >
                <div className="text-xl">
                  {actionIcons[log.action] || '📌'}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium capitalize">{log.action}</span>
                    {log.note_id && (
                      <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                        笔记 #{log.note_id}
                      </span>
                    )}
                    {log.workspace_id && (
                      <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded">
                        工作区 #{log.workspace_id}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-gray-400">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
