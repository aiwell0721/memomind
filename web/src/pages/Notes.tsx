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

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">📝 笔记</h1>
          {selectedTag && (
            <span className="text-sm text-gray-500">
              标签: <span className="tag">{selectedTag}</span>
              <button
                className="ml-2 text-red-500 hover:text-red-600"
                onClick={() => navigate('/')}
              >
                清除
              </button>
            </span>
          )}
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + 新建笔记
        </button>
      </div>

      {/* Search */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          className="input flex-1"
          placeholder="搜索笔记..."
        />
        <button className="btn btn-secondary" onClick={() => handleSearch()}>
          🔍 搜索
        </button>
        {searchResults && (
          <button className="btn btn-secondary" onClick={() => { setQuery(''); setSearchResults(null); }}>
            显示全部
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Create dialog */}
      {showCreate && (
        <div className="mb-4 card">
          <h3 className="font-medium mb-3">新建笔记</h3>
          <input
            type="text"
            value={newNote.title}
            onChange={(e) => setNewNote({ ...newNote, title: e.target.value })}
            className="input mb-2"
            placeholder="标题"
            autoFocus
          />
          <textarea
            value={newNote.content}
            onChange={(e) => setNewNote({ ...newNote, content: e.target.value })}
            className="input mb-3"
            placeholder="内容（支持 Markdown）"
            rows={4}
          />
          <div className="flex gap-2">
            <button className="btn btn-primary btn-sm" onClick={handleCreate}>
              创建
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowCreate(false)}>
              取消
            </button>
          </div>
        </div>
      )}

      {/* Notes list */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">加载中...</div>
      ) : displayNotes.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          {query ? '没有找到匹配的笔记' : '暂无笔记，点击上方按钮创建'}
        </div>
      ) : (
        <div className="space-y-2">
          {displayNotes.map((note) => (
            <div
              key={note.id}
              className="card hover:shadow-md transition cursor-pointer flex items-center justify-between"
              onClick={() => navigate(`/notes/${note.id}`)}
            >
              <div className="flex-1 min-w-0">
                <h3 className="font-medium truncate">{note.title}</h3>
                <p className="text-sm text-gray-500 truncate">{note.content.slice(0, 100)}</p>
                <div className="flex items-center gap-2 mt-1">
                  {note.tags.slice(0, 3).map((tag, i) => (
                    <span key={i} className="tag">
                      {tag}
                    </span>
                  ))}
                  <span className="text-xs text-gray-400">
                    {new Date(note.updated_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
              <button
                className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded transition"
                onClick={(e) => handleDelete(note.id, e)}
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      )}

      {searchResults && (
        <div className="mt-2 text-sm text-gray-500">
          找到 {searchResults.length} 条结果
        </div>
      )}
    </div>
  );
}
