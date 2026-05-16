import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import type { Note, SearchResult } from '../lib/api';

export default function Notes() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [notes, setNotes] = useState<Note[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newNote, setNewNote] = useState({ title: '', content: '' });
  const [workspaceId, setWorkspaceId] = useState<number | null>(null);

  const loadNotes = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.notes({ limit: 100, workspace_id: workspaceId ?? undefined });
      setNotes(data);
      setSearchResults(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  useEffect(() => {
    const tag = searchParams.get('tag');
    setSelectedTag(tag);
    if (tag) {
      handleSearch(tag);
    }
  }, [searchParams]);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      setWorkspaceId(detail);
    };
    window.addEventListener('workspace-change', handler);
    return () => window.removeEventListener('workspace-change', handler);
  }, []);

  const handleSearch = async (searchQuery?: string) => {
    const q = searchQuery ?? query;
    if (!q.trim()) {
      setSearchResults(null);
      loadNotes();
      return;
    }

    setLoading(true);
    try {
      const results = await api.searchNotes(q, selectedTag ? [selectedTag] : undefined);
      setSearchResults(results);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '搜索失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newNote.title.trim()) return;
    try {
      const note = await api.createNote({
        ...newNote,
        tags: selectedTag ? [selectedTag] : [],
        workspace_id: workspaceId ?? undefined,
      });
      setShowCreate(false);
      setNewNote({ title: '', content: '' });
      loadNotes();
      navigate(`/notes/${note.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '创建失败');
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('确定删除此笔记？')) return;
    try {
      await api.deleteNote(id);
      loadNotes();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const displayNotes = searchResults ? searchResults.map((r) => r.note) : notes;

  // Format date relative
  const formatDate = (dateStr: string) => {
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
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="fade-in" style={{ padding: '2rem', maxWidth: 800, margin: '0 auto' }}>
      {/* Header */}
      <div className="flex items-center justify-between" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.021em' }}>
            笔记
          </h1>
          {selectedTag && (
            <div style={{ fontSize: 13, color: 'var(--apple-text-secondary)', marginTop: 4 }}>
              标签：<span className="tag">{selectedTag}</span>
              <button
                onClick={() => navigate('/')}
                style={{
                  marginLeft: 8,
                  background: 'none',
                  border: 'none',
                  color: 'var(--danger)',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontFamily: 'inherit',
                }}
              >
                清除
              </button>
            </div>
          )}
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          新建笔记
        </button>
      </div>

      {/* Search */}
      <div className="flex gap-2" style={{ marginBottom: '1.25rem' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <svg
            width="16" height="16"
            viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
            style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', opacity: 0.35, pointerEvents: 'none' }}
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="input"
            placeholder="搜索笔记..."
            style={{ paddingLeft: 36 }}
          />
        </div>
        <button className="btn btn-secondary" onClick={() => handleSearch()}>
          搜索
        </button>
        {searchResults && (
          <button
            className="btn btn-ghost"
            onClick={() => { setQuery(''); setSearchResults(null); }}
          >
            显示全部
          </button>
        )}
      </div>

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

      {/* Create dialog */}
      {showCreate && (
        <div className="card slide-in" style={{ marginBottom: '1.25rem' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>新建笔记</h3>
          <input
            type="text"
            value={newNote.title}
            onChange={(e) => setNewNote({ ...newNote, title: e.target.value })}
            className="input"
            placeholder="标题"
            autoFocus
            style={{ marginBottom: 10 }}
          />
          <textarea
            value={newNote.content}
            onChange={(e) => setNewNote({ ...newNote, content: e.target.value })}
            className="input"
            placeholder="内容（支持 Markdown）"
            rows={4}
            style={{ marginBottom: 12 }}
          />
          <div className="flex gap-2">
            <button className="btn btn-primary btn-sm" onClick={handleCreate}>创建</button>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowCreate(false)}>取消</button>
          </div>
        </div>
      )}

      {/* Notes list */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--apple-text-tertiary)', fontSize: 14 }}>
          加载中...
        </div>
      ) : displayNotes.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--apple-text-tertiary)' }}>
          <div style={{ fontSize: 48, marginBottom: 12, opacity: 0.4 }}>📝</div>
          <div style={{ fontSize: 14 }}>
            {query ? '没有找到匹配的笔记' : '暂无笔记，点击上方按钮创建'}
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {displayNotes.map((note) => (
            <div
              key={note.id}
              className="card card-hover"
              style={{
                cursor: 'pointer',
                padding: '1rem 1.25rem',
                display: 'flex',
                alignItems: 'flex-start',
                gap: 16,
                marginBottom: 8,
                animation: 'fadeIn 0.2s ease-out',
              }}
              onClick={() => navigate(`/notes/${note.id}`)}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <h3 style={{
                  fontWeight: 600,
                  fontSize: 14,
                  marginBottom: 4,
                  letterSpacing: '-0.01em',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {note.title}
                </h3>
                <p style={{
                  fontSize: 13,
                  color: 'var(--apple-text-secondary)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  marginBottom: 8,
                }}>
                  {note.content.slice(0, 120)}
                </p>
                <div className="flex items-center gap-2">
                  {note.tags.slice(0, 3).map((tag, i) => (
                    <span key={i} className="tag">{tag}</span>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                <span style={{ fontSize: 11, color: 'var(--apple-text-tertiary)', whiteSpace: 'nowrap' }}>
                  {formatDate(note.updated_at)}
                </span>
                <button
                  onClick={(e) => handleDelete(note.id, e)}
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
                    opacity: 0,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.opacity = '1';
                    e.currentTarget.style.background = 'var(--danger-bg)';
                    e.currentTarget.style.color = 'var(--danger)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.opacity = '0';
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--apple-text-tertiary)';
                  }}
                  title="删除"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {searchResults && (
        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--apple-text-tertiary)' }}>
          找到 {searchResults.length} 条结果
        </div>
      )}
    </div>
  );
}
