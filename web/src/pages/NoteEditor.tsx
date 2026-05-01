import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { marked } from 'marked';
import { api } from '../lib/api';
import type { Note, Version, Collaborator } from '../lib/api';
import { createWsClient } from '../lib/api';

export default function NoteEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [note, setNote] = useState<Note | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [editTags, setEditTags] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [versions, setVersions] = useState<Version[]>([]);
  const [showVersions, setShowVersions] = useState(false);
  const [incomingLinks, setIncomingLinks] = useState<unknown[]>([]);
  const [onlineUsers, setOnlineUsers] = useState<Collaborator[]>([]);
  const [remoteEdit, setRemoteEdit] = useState(false);

  const wsRef = useRef<ReturnType<typeof createWsClient> | null>(null);
  const isLocalEdit = useRef(false);

  const loadNote = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await api.getNote(Number(id));
      setNote(data);
      setEditTitle(data.title);
      setEditContent(data.content);
      setEditTags(data.tags.join(', '));

      api.versions(Number(id), 10).then(setVersions).catch(() => {});
      api.incomingLinks(Number(id)).then(setIncomingLinks).catch(() => {});
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadNote();
  }, [loadNote]);

  // WebSocket 协作连接
  useEffect(() => {
    if (!id || !note) return;

    const ws = createWsClient(Number(id), (msg) => {
      if (msg.type === 'edit' && msg.content !== undefined) {
        // 收到远程编辑，同步到本地
        if (!isLocalEdit.current) {
          setEditContent(msg.content || '');
          setEditTitle(msg.title || '');
        }
        setRemoteEdit(true);
        setTimeout(() => setRemoteEdit(false), 2000);
      }
      if (msg.type === 'user_joined' || msg.type === 'user_left') {
        setOnlineUsers(msg.users || []);
      }
    });

    wsRef.current = ws;

    return () => {
      ws.disconnect();
      wsRef.current = null;
    };
  }, [id, note?.updated_at]);

  const handleSave = async () => {
    if (!note || !editTitle.trim()) return;
    setLoading(true);
    isLocalEdit.current = true;
    try {
      const tags = editTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      await api.updateNote(note.id, {
        title: editTitle,
        content: editContent,
        tags,
      });
      setEditMode(false);
      loadNote();

      // 广播保存结果给协作者
      wsRef.current?.sendEdit(editTitle, editContent);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setLoading(false);
      setTimeout(() => { isLocalEdit.current = false; }, 500);
    }
  };

  // 编辑内容变化时广播（仅在编辑模式下）
  useEffect(() => {
    if (!editMode || !wsRef.current) return;
    const timer = setTimeout(() => {
      wsRef.current?.sendEdit(editTitle, editContent);
    }, 500); // 防抖 500ms
    return () => clearTimeout(timer);
  }, [editTitle, editContent, editMode]);

  const handleSaveVersion = async () => {
    if (!note) return;
    try {
      await api.saveVersion(note.id, '手动保存');
      api.versions(note.id, 10).then(setVersions);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存版本失败');
    }
  };

  const handleRestoreVersion = async (versionId: number) => {
    if (!confirm('恢复到这个版本？当前内容将被覆盖。')) return;
    try {
      await api.restoreVersion(versionId);
      loadNote();
      setShowVersions(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '恢复失败');
    }
  };

  if (loading && !note) {
    return <div className="p-6 text-center text-gray-400">加载中...</div>;
  }

  if (!note) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-500">笔记不存在</p>
        <button className="btn btn-secondary mt-4" onClick={() => navigate('/')}>
          返回
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/')}>
          ← 返回
        </button>
        <div className="flex items-center gap-3">
          {/* 在线用户 */}
          {onlineUsers.length > 0 && (
            <div className="flex items-center gap-1" title={`${onlineUsers.length} 人正在编辑`}>
              {onlineUsers.map((u) => (
                <span
                  key={u.user_id}
                  className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-blue-100 text-blue-600 text-xs font-medium"
                >
                  {u.username.charAt(0).toUpperCase()}
                </span>
              ))}
            </div>
          )}
          <button className="btn btn-secondary btn-sm" onClick={() => setShowVersions(!showVersions)}>
            📜 版本历史 ({versions.length})
          </button>
          {!editMode ? (
            <button className="btn btn-primary btn-sm" onClick={() => setEditMode(true)}>
              ✏️ 编辑
            </button>
          ) : (
            <>
              <button className="btn btn-secondary btn-sm" onClick={() => { setEditMode(false); loadNote(); }}>
                取消
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleSave}>
                💾 保存
              </button>
            </>
          )}
        </div>
      </div>

      {/* 远程编辑通知 */}
      {remoteEdit && (
        <div className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded-lg text-blue-600 text-sm">
          协作者已更新内容
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Versions panel */}
      {showVersions && (
        <div className="mb-4 card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium">📜 版本历史</h3>
            <button className="btn btn-primary btn-sm" onClick={handleSaveVersion}>
              保存当前版本
            </button>
          </div>
          {versions.length === 0 ? (
            <p className="text-sm text-gray-400">暂无版本</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {versions.map((v) => (
                <div key={v.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <div>
                    <span className="text-sm font-medium">{v.change_summary || '自动保存'}</span>
                    <span className="text-xs text-gray-400 ml-2">
                      {new Date(v.created_at).toLocaleString()}
                    </span>
                  </div>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleRestoreVersion(v.id)}
                  >
                    恢复
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Note content */}
      {editMode ? (
        <div className="space-y-3">
          <input
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            className="input text-xl font-bold"
            placeholder="标题"
          />
          <input
            type="text"
            value={editTags}
            onChange={(e) => setEditTags(e.target.value)}
            className="input"
            placeholder="标签（逗号分隔）"
          />
          <textarea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            className="input font-mono"
            placeholder="内容（支持 Markdown）"
            rows={16}
          />
        </div>
      ) : (
        <>
          <h1 className="text-3xl font-bold mb-2">{note.title}</h1>
          <div className="flex items-center gap-3 mb-4">
            {note.tags.map((tag, i) => (
              <span key={i} className="tag">{tag}</span>
            ))}
            <span className="text-xs text-gray-400">
              更新于 {new Date(note.updated_at).toLocaleString()}
            </span>
          </div>
          <div
            className="card markdown-content"
            dangerouslySetInnerHTML={{ __html: marked(note.content) }}
          />
        </>
      )}

      {/* Incoming links */}
      {incomingLinks.length > 0 && (
        <div className="mt-6 card">
          <h3 className="font-medium mb-2">🔗 反向链接 ({incomingLinks.length})</h3>
          <div className="space-y-1">
            {incomingLinks.slice(0, 10).map((link, i) => {
              const l = link as Record<string, unknown>;
              return (
                <span key={i} className="text-sm text-blue-600 cursor-pointer hover:underline">
                  {String(l.source_title || '笔记')} → {note.title}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
