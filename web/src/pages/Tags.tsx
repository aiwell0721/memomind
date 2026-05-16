import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { Tag } from '../lib/api';

export default function Tags() {
  const [tags, setTags] = useState<Tag[]>([]);
  const [newTag, setNewTag] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadTags();
  }, []);

  const loadTags = async () => {
    try {
      const data = await api.tags(true);
      setTags(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载失败');
    }
  };

  const handleCreate = async () => {
    if (!newTag.trim()) return;
    setLoading(true);
    try {
      await api.createTag(newTag.trim());
      setNewTag('');
      loadTags();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除此标签？')) return;
    try {
      await api.deleteTag(id);
      loadTags();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const renderTagTree = (tagList: Tag[], level = 0): React.ReactNode[] => {
    return tagList.flatMap((tag) => [
      <div
        key={tag.id}
        className="group"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.5rem 0.75rem',
          paddingLeft: `${level * 1.5 + 0.75}rem`,
          borderRadius: 8,
          transition: 'background 0.15s',
          cursor: 'default',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(0,0,0,0.02)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
      >
        <div className="flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.5 }}>
            {level === 0 ? (
              <>
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </>
            ) : (
              <>
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </>
            )}
          </svg>
          <span style={{ fontSize: 13, fontWeight: 500 }}>{tag.name}</span>
          {tag.children && tag.children.length > 0 && (
            <span style={{ fontSize: 11, color: 'var(--apple-text-tertiary)' }}>
              ({tag.children.length} 子标签)
            </span>
          )}
        </div>
        <button
          onClick={() => handleDelete(tag.id)}
          style={{
            opacity: 0,
            transition: 'opacity 0.15s',
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
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </div>,
      ...(tag.children ? renderTagTree(tag.children, level + 1) : []),
    ]);
  };

  return (
    <div className="fade-in" style={{ padding: '2rem', maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.021em', marginBottom: '1.5rem' }}>
        标签管理
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

      {/* Create tag */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>新建标签</h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            className="input"
            placeholder="标签名称"
          />
          <button
            className="btn btn-primary"
            onClick={handleCreate}
            disabled={loading}
          >
            创建
          </button>
        </div>
      </div>

      {/* Tags tree */}
      <div className="card">
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
          标签树 ({tags.length})
        </h3>
        {tags.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '1.5rem 0', color: 'var(--apple-text-tertiary)', fontSize: 13 }}>
            暂无标签
          </p>
        ) : (
          <div>{renderTagTree(tags)}</div>
        )}
      </div>
    </div>
  );
}
