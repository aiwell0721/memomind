import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { toast } from '../App';
import type { Note, SearchResult } from '../lib/api';

/* ── Relative time formatter ── */
function formatDate(dateStr: string): string {
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
}

/* ── Empty State SVG illustration ── */
function EmptyNotes({ hasQuery, onCreate }: { hasQuery: boolean; onCreate: () => void }) {
  return (
    <div className="empty-state animate-fade-in-up">
      <svg className="empty-state-icon" viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Notebook */}
        <rect x="30" y="10" width="60" height="80" rx="6" stroke="currentColor" strokeWidth="2.5" fill="none" opacity="0.6" />
        <line x1="42" y1="30" x2="78" y2="30" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
        <line x1="42" y1="42" x2="78" y2="42" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
        <line x1="42" y1="54" x2="66" y2="54" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
        {/* Pencil */}
        <g transform="translate(72, 60) rotate(45)" opacity="0.7">
          <rect x="-4" y="-4" width="24" height="8" rx="2" fill="#f09824" />
          <polygon points="20,-4 28,0 20,4" fill="#ee4b40" />
        </g>
        {/* Sparkle */}
        <circle cx="85" cy="15" r="2" fill="currentColor" opacity="0.5" />
        <circle cx="88" cy="10" r="1.5" fill="currentColor" opacity="0.3" />
      </svg>
      <h3 className="empty-state-title">
        {hasQuery ? '没有找到匹配的笔记' : '还没有笔记'}
      </h3>
      <p className="empty-state-desc">
        {hasQuery ? '试试换个关键词，或者清除搜索条件' : '点击右上角的「新建笔记」按钮，创建第一条知识'}
      </p>
      {!hasQuery && (
        <button className="btn btn-primary" onClick={onCreate}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          创建第一条笔记
        </button>
      )}
    </div>
  );
}

/* ── Skeleton loading ── */
function NoteSkeleton() {
  return (
    <div>
      {[1, 2, 3].map((i) => (
        <div key={i} className="card" style={{ marginBottom: 8, padding: '1rem 1.25rem' }}>
          <div className="skeleton skeleton-text" style={{ width: '60%', height: 14 }} />
          <div className="skeleton skeleton-text" style={{ width: '90%' }} />
          <div className="skeleton skeleton-text" style={{ width: '40%' }} />
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════
   Notes Page
   ═══════════════════════════════════════════ */

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
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  /* ── Load notes ── */
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

  useEffect(() => { loadNotes(); }, [loadNotes]);

  /* ── URL tag param ── */
  useEffect(() => {
    const tag = searchParams.get('tag');
    setSelectedTag(tag);
    if (tag) handleSearch(tag);
    else { setSearchResults(null); loadNotes(); }
  }, [searchParams]);

  /* ── Workspace change listener ── */
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      setWorkspaceId(detail);
    };
    window.addEventListener('workspace-change', handler);
    return () => window.removeEventListener('workspace-change', handler);
  }, []);

  /* ── Search ── */
  const handleSearch = async (searchQuery?: string) => {
    const q = searchQuery ?? query;
    if (!q.trim()) { setSearchResults(null); loadNotes(); return; }
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

  /* ── Create ── */
  const handleCreate = async () => {
    if (!newNote.title.trim()) return;
    setCreating(true);
    try {
      const note = await api.createNote({
        ...newNote,
        tags: selectedTag ? [selectedTag] : [],
        workspace_id: workspaceId ?? undefined,
      });
      setShowCreate(false);
      setNewNote({ title: '', content: '' });
      toast('笔记创建成功');
      loadNotes();
      navigate(`/notes/${note.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreating(false);
    }
  };

  /* ── Delete ── */
  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await api.deleteNote(id);
      toast('笔记已删除');
      setConfirmDeleteId(null);
      loadNotes();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    } finally {
      setDeletingId(null);
    }
  };

  const displayNotes = searchResults ? searchResults.map((r) => r.note) : notes;

  return (
    <div className="page-enter" style={{ padding: '0 2rem 2rem' }}>
      {/* ── Header ── */}
      <div className="flex items-center justify-between" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.021em' }}>笔记</h1>
          {selectedTag && (
            <div style={{ fontSize: 13, color: 'var(--apple-text-secondary)', marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
              筛选标签：
              <span className="tag">{selectedTag}</span>
              <button
                onClick={() => navigate('/')}
                style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: 13, fontFamily: 'inherit' }}
              >
                清除
              </button>
            </div>
          )}
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          新建笔记
        </button>
      </div>

      {/* ── Search Bar ── */}
      <div className="flex items-center gap-2" style={{ marginBottom: '1.25rem' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
            style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', opacity: 0.35, pointerEvents: 'none' }}>
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
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
        <button className="btn btn-secondary" onClick={() => handleSearch()}>搜索</button>
        {searchResults && (
          <button className="btn btn-ghost" onClick={() => { setQuery(''); setSearchResults(null); }}>
            显示全部
          </button>
        )}
      </div>

      {/* ── Result count ── */}
      {searchResults && (
        <div style={{ marginBottom: 12, fontSize: 12, color: 'var(--apple-text-secondary)' }}>
          找到 <strong>{searchResults.length}</strong> 条结果
        </div>
      )}

      {/* ── Error ── */}
      {error && (
        <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: 'var(--danger-bg)', borderRadius: 10, color: 'var(--danger)', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* ── Create Modal ── */}
      {showCreate && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowCreate(false); }}>
          <div className="modal-content">
            <div className="flex items-center justify-between" style={{ marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '1.0625rem', fontWeight: 600 }}>新建笔记</h3>
              <button className="btn-icon" onClick={() => setShowCreate(false)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <input
              type="text"
              value={newNote.title}
              onChange={(e) => setNewNote({ ...newNote, title: e.target.value })}
              className="input"
              placeholder="笔记标题"
              autoFocus
              style={{ marginBottom: 12 }}
            />
            <textarea
              value={newNote.content}
              onChange={(e) => setNewNote({ ...newNote, content: e.target.value })}
              className="input"
              placeholder="内容（支持 Markdown）"
              rows={6}
              style={{ marginBottom: 16 }}
            />
            <div className="flex gap-2 justify-end">
              <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>取消</button>
              <button className="btn btn-primary" onClick={handleCreate} disabled={creating}>
                {creating ? '创建中...' : '创建笔记'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Content Area ── */}
      {loading ? (
        <NoteSkeleton />
      ) : displayNotes.length === 0 ? (
        <EmptyNotes hasQuery={!!searchResults || !!query} onCreate={() => setShowCreate(true)} />
      ) : (
        <div className="stagger">
          {displayNotes.map((note) => (
            <div
              key={note.id}
              className="card card-hover"
              style={{
                cursor: 'pointer', padding: '1rem 1.25rem',
                display: 'flex', alignItems: 'flex-start', gap: 14,
                marginBottom: 8, position: 'relative', overflow: 'hidden',
              }}
              onClick={() => navigate(`/notes/${note.id}`)}
            >
              {/* Left accent stripe */}
              <div style={{
                position: 'absolute', left: 0, top: 0, bottom: 0,
                width: 3, background: 'var(--apple-accent)',
                opacity: 0, transition: 'opacity 0.2s',
                borderRadius: '3px 0 0 3px',
              }}
                className="card-accent-stripe"
                onMouseEnter={(e) => { e.currentTarget.style.opacity = '1'; }}
              />

              <div style={{ flex: 1, minWidth: 0 }}>
                <h3 style={{
                  fontWeight: 600, fontSize: 15, marginBottom: 4,
                  letterSpacing: '-0.01em', overflow: 'hidden',
                  textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  <span style={{ fontSize: 11, color: 'var(--apple-text-tertiary)', fontWeight: 400, marginRight: 6 }}>
                    #{note.id}
                  </span>
                  {note.title}
                </h3>
                <p style={{
                  fontSize: 13, color: 'var(--apple-text-secondary)',
                  overflow: 'hidden', display: '-webkit-box',
                  WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                  marginBottom: 8, lineHeight: 1.5,
                }}>
                  {note.content.slice(0, 200) || '（空笔记）'}
                </p>
                <div className="flex items-center gap-2" style={{ flexWrap: 'wrap' }}>
                  {note.tags.slice(0, 4).map((tag, i) => (
                    <span key={i} className="tag">
                      <span className="tag-dot" style={{ background: ['#0071e3','#30b158','#f09824','#ee4b40'][i % 4] }} />
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Right: time + delete */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8, flexShrink: 0 }}>
                <span style={{ fontSize: 11, color: 'var(--apple-text-tertiary)', whiteSpace: 'nowrap' }}>
                  {formatDate(note.updated_at)}
                </span>
                {/* Delete — slides in on hover */}
                {confirmDeleteId === note.id ? (
                  <div className="flex items-center gap-1" style={{ animation: 'slideInRight 0.2s var(--ease-spring)' }}>
                    <span style={{ fontSize: 11, color: 'var(--danger)' }}>确定删除？</span>
                    <button
                      className="btn btn-danger btn-sm"
                      style={{ padding: '0.125rem 0.5rem', fontSize: 11 }}
                      onClick={(e) => { e.stopPropagation(); handleDelete(note.id); }}
                      disabled={deletingId === note.id}
                    >
                      确认
                    </button>
                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ padding: '0.125rem 0.5rem', fontSize: 11 }}
                      onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(null); }}
                    >
                      取消
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(note.id); }}
                    className="btn-icon"
                    style={{ width: 28, height: 28, opacity: 0, transition: 'opacity 0.15s' }}
                    title="删除"
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
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
