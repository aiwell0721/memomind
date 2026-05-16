import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { marked } from 'marked';
import { api } from '../lib/api';
import type { Note, Version, Collaborator } from '../lib/api';
import { createWsClient } from '../lib/api';

// Markdown syntax reference data
const markdownSyntax = [
  { element: '# 标题', desc: '一级标题', example: '# 标题' },
  { element: '## 二级标题', desc: '二级标题', example: '## 子标题' },
  { element: '**粗体**', desc: '加粗文本', example: '**重要内容**' },
  { element: '*斜体*', desc: '斜体文本', example: '*强调文字*' },
  { element: '~~删除线~~', desc: '删除线', example: '~~已删除~~' },
  { element: '`行内代码`', desc: '行内代码', example: '`const x = 1`' },
  { element: '```代码块', desc: '多行代码块', example: '```python\nprint("hi")\n```' },
  { element: '- 列表项', desc: '无序列表', example: '- 第一项\n- 第二项' },
  { element: '1. 列表项', desc: '有序列表', example: '1. 步骤一\n2. 步骤二' },
  { element: '> 引用', desc: '引用块', example: '> 这是一段引用' },
  { element: '[文本](URL)', desc: '超链接', example: '[Google](https://google.com)' },
  { element: '![alt](URL)', desc: '图片', example: '![描述](image.png)' },
  { element: '---', desc: '分隔线', example: '---' },
  { element: '| 表头 |', desc: '表格', example: '| 列A | 列B |\n|---|---|\n| 1 | 2 |' },
  { element: '- [ ] 任务', desc: '待办事项', example: '- [ ] 未完成\n- [x] 已完成' },
];

type ViewMode = 'preview' | 'raw';

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

  // View mode: preview (rendered Markdown) vs raw (raw source)
  const [viewMode, setViewMode] = useState<ViewMode>('preview');

  // Syntax panel state
  const [showSyntax, setShowSyntax] = useState(false);

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

      wsRef.current?.sendEdit(editTitle, editContent);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setLoading(false);
      setTimeout(() => { isLocalEdit.current = false; }, 500);
    }
  };

  useEffect(() => {
    if (!editMode || !wsRef.current) return;
    const timer = setTimeout(() => {
      wsRef.current?.sendEdit(editTitle, editContent);
    }, 500);
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
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--apple-text-tertiary)' }}>
        加载中...
      </div>
    );
  }

  if (!note) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ color: 'var(--apple-text-secondary)' }}>笔记不存在</p>
        <button className="btn btn-secondary" style={{ marginTop: 16 }} onClick={() => navigate('/')}>
          返回
        </button>
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ padding: '1.5rem 2rem', maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <div
        className="flex items-center justify-between"
        style={{ marginBottom: '1rem', paddingBottom: '0.75rem', borderBottom: '0.5px solid var(--apple-border-light)' }}
      >
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          返回
        </button>
        <div className="flex items-center gap-2">
          {/* Online users */}
          {onlineUsers.length > 0 && (
            <div className="flex items-center gap-1" title={`${onlineUsers.length} 人正在编辑`}>
              {onlineUsers.map((u) => (
                <span
                  key={u.user_id}
                  style={{
                    width: 26,
                    height: 26,
                    borderRadius: '50%',
                    background: 'var(--accent-light)',
                    color: 'var(--accent)',
                    fontSize: 11,
                    fontWeight: 600,
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {u.username.charAt(0).toUpperCase()}
                </span>
              ))}
            </div>
          )}

          {/* Versions */}
          <button className="btn btn-secondary btn-sm" onClick={() => setShowVersions(!showVersions)}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            版本 ({versions.length})
          </button>

          {/* Edit / Save */}
          {!editMode ? (
            <button className="btn btn-primary btn-sm" onClick={() => setEditMode(true)}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
              编辑
            </button>
          ) : (
            <>
              <button className="btn btn-secondary btn-sm" onClick={() => { setEditMode(false); loadNote(); }}>
                取消
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={loading}>
                {loading ? '保存中...' : '保存'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Remote edit notification */}
      {remoteEdit && (
        <div style={{
          marginBottom: 12,
          padding: '0.5rem 1rem',
          background: 'var(--accent-light)',
          borderRadius: 8,
          color: 'var(--accent)',
          fontSize: 13,
        }}>
          协作者已更新内容
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{
          marginBottom: 12,
          padding: '0.75rem 1rem',
          background: 'var(--danger-bg)',
          borderRadius: 10,
          color: 'var(--danger)',
          fontSize: 13,
        }}>
          {error}
        </div>
      )}

      {/* Versions panel */}
      {showVersions && (
        <div className="card slide-in" style={{ marginBottom: '1rem' }}>
          <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>版本历史</h3>
            <button className="btn btn-primary btn-sm" onClick={handleSaveVersion}>
              保存当前版本
            </button>
          </div>
          {versions.length === 0 ? (
            <p style={{ fontSize: 13, color: 'var(--apple-text-tertiary)' }}>暂无版本</p>
          ) : (
            <div style={{ maxHeight: 200, overflowY: 'auto' }}>
              {versions.map((v) => (
                <div
                  key={v.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.5rem 0.75rem',
                    background: 'var(--apple-bg)',
                    borderRadius: 8,
                    marginBottom: 6,
                  }}
                >
                  <div>
                    <span style={{ fontSize: 13, fontWeight: 500 }}>{v.change_summary || '自动保存'}</span>
                    <span style={{ fontSize: 11, color: 'var(--apple-text-tertiary)', marginLeft: 8 }}>
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

      {/* Note title + meta */}
      {editMode ? (
        <div style={{ marginBottom: '1rem' }}>
          <input
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            style={{
              fontSize: '1.5rem',
              fontWeight: 700,
              width: '100%',
              border: 'none',
              borderBottom: '1px solid var(--apple-border)',
              padding: '0.5rem 0',
              marginBottom: 8,
              fontFamily: 'inherit',
              letterSpacing: '-0.021em',
              outline: 'none',
              background: 'transparent',
            }}
            placeholder="标题"
          />
          <input
            type="text"
            value={editTags}
            onChange={(e) => setEditTags(e.target.value)}
            className="input"
            placeholder="标签（逗号分隔）"
            style={{ fontSize: 13, padding: '0.375rem 0.75rem' }}
          />
        </div>
      ) : (
        <>
          <h1 style={{
            fontSize: '1.75rem',
            fontWeight: 700,
            letterSpacing: '-0.021em',
            marginBottom: 8,
          }}>
            {note.title}
          </h1>
          <div className="flex items-center gap-3" style={{ marginBottom: '1rem' }}>
            {note.tags.map((tag, i) => (
              <span key={i} className="tag">{tag}</span>
            ))}
            <span style={{ fontSize: 12, color: 'var(--apple-text-tertiary)' }}>
              更新于 {new Date(note.updated_at).toLocaleString()}
            </span>
          </div>
        </>
      )}

      {/* View mode toggle (only in non-edit mode) */}
      {!editMode && (
        <div className="flex items-center justify-between" style={{ marginBottom: '0.75rem' }}>
          {/* View toggle */}
          <div className="view-toggle">
            <button
              className={`view-toggle-btn ${viewMode === 'preview' ? 'active' : ''}`}
              onClick={() => setViewMode('preview')}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ marginRight: 4 }}>
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
              预览
            </button>
            <button
              className={`view-toggle-btn ${viewMode === 'raw' ? 'active' : ''}`}
              onClick={() => setViewMode('raw')}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ marginRight: 4 }}>
                <polyline points="16 18 22 12 16 6" />
                <polyline points="8 6 2 12 8 18" />
              </svg>
              RAW
            </button>
          </div>

          {/* Syntax hint toggle */}
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setShowSyntax(!showSyntax)}
            style={{ fontSize: 12 }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            {showSyntax ? '收起语法' : 'Markdown 语法'}
          </button>
        </div>
      )}

      {/* Syntax hint panel */}
      {!editMode && (
        <div className="syntax-panel slide-in" style={{ marginBottom: '1rem', maxHeight: showSyntax ? 480 : 42, overflow: 'hidden', transition: 'max-height 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)' }}>
          <div className="syntax-panel-header" onClick={() => setShowSyntax(!showSyntax)}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Markdown 语法速查</span>
            <svg
              width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
              style={{ transform: showSyntax ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
          <div style={{ opacity: showSyntax ? 1 : 0, transition: 'opacity 0.2s' }}>
            <div className="syntax-table">
              {markdownSyntax.map((row, i) => (
                <div key={i} className="syntax-row">
                  <span className="syntax-example">{row.example.split('\n')[0]}</span>
                  <span className="syntax-desc">{row.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Content area */}
      {editMode ? (
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          className="input"
          placeholder="内容（支持 Markdown）"
          rows={18}
          style={{ fontFamily: '"SF Mono", SFMono-Regular, Menlo, Consolas, monospace', fontSize: 13, lineHeight: 1.7 }}
        />
      ) : viewMode === 'raw' ? (
        <div className="raw-content">{note.content || '（空笔记）'}</div>
      ) : (
        <div
          className="card markdown-content"
          dangerouslySetInnerHTML={{ __html: marked(note.content || '_暂无内容_') }}
          style={{ padding: '1.5rem' }}
        />
      )}

      {/* Incoming links */}
      {incomingLinks.length > 0 && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ marginRight: 6, verticalAlign: 'middle' }}>
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            反向链接 ({incomingLinks.length})
          </h3>
          <div>
            {incomingLinks.slice(0, 10).map((link, i) => {
              const l = link as Record<string, unknown>;
              return (
                <span
                  key={i}
                  style={{
                    display: 'block',
                    fontSize: 13,
                    color: 'var(--accent)',
                    cursor: 'pointer',
                    padding: '0.375rem 0',
                  }}
                >
                  → {String(l.source_title || '笔记')}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
