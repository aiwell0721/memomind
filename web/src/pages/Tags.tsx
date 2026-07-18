import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { toast } from '../App';
import type { Tag } from '../lib/api';

/* ── Color palette for dots ── */
const dotColors = [
  '#0071e3', '#30b158', '#f09824', '#ee4b40',
  '#ac4ee0', '#ff69b4', '#00b8b0', '#ff9500',
];

function getColor(index: number) { return dotColors[index % dotColors.length]; }

/* ── Flatten tree to get note count per tag (simulated since API doesn't return counts on tags) ── */
function flattenTree(tags: Tag[]): Tag[] {
  return tags.flatMap((t) => [t, ...flattenTree(t.children || [])]);
}

/* ═══════════════════════════════════════════
   Tags Page
   ═══════════════════════════════════════════ */

export default function Tags() {
  const navigate = useNavigate();
  const [tags, setTags] = useState<Tag[]>([]);
  const [newTagName, setNewTagName] = useState('');
  const [newTagParent, setNewTagParent] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [creatingInline, setCreatingInline] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());

  useEffect(() => { loadTags(); }, []);

  const loadTags = async () => {
    try {
      const data = await api.tags(true);
      setTags(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载失败');
    }
  };

  const handleCreate = async () => {
    if (!newTagName.trim()) return;
    setLoading(true);
    try {
      await api.createTag(newTagName.trim(), newTagParent);
      setNewTagName('');
      setNewTagParent(undefined);
      setCreatingInline(false);
      toast('标签已创建');
      loadTags();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteTag(id);
      toast('标签已删除');
      setConfirmDeleteId(null);
      loadTags();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const toggleCollapse = (id: number) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  /* ── Render tree with lines ── */
  const renderTree = (tagList: Tag[], level = 0): React.ReactNode[] => {
    return tagList.flatMap((tag, i) => {
      const hasChildren = tag.children && tag.children.length > 0;
      const isCollapsed = collapsed.has(tag.id);
      const color = getColor(level * tagList.length + i);
      const isLastInLevel = i === tagList.length - 1;

      return [
        <div key={tag.id} style={{ position: 'relative' }}>
          {/* Vertical tree line */}
          {level > 0 && (
            <>
              <div style={{
                position: 'absolute', left: `${(level - 1) * 1.5 + 0.75}rem`,
                top: 0, bottom: isLastInLevel ? '50%' : 0,
                width: 1, background: 'var(--apple-border)',
              }} />
              <div style={{
                position: 'absolute', left: `${(level - 1) * 1.5 + 0.75}rem`,
                top: '50%', width: '0.75rem', height: 1,
                background: 'var(--apple-border)',
              }} />
            </>
          )}

          <div
            className="group"
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '0.5rem 0.75rem',
              paddingLeft: `${level * 1.5 + 0.75}rem`,
              borderRadius: 8, transition: 'background 0.15s', cursor: 'default',
              position: 'relative',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(0,0,0,0.02)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
          >
            <div className="flex items-center gap-2" style={{ minWidth: 0 }}>
              {/* Collapse toggle */}
              {hasChildren ? (
                <button
                  onClick={() => toggleCollapse(tag.id)}
                  style={{
                    width: 18, height: 18, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--apple-text-tertiary)',
                    borderRadius: 4, flexShrink: 0,
                  }}
                >
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
                    style={{ transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
              ) : (
                <span style={{ width: 18, flexShrink: 0 }} />
              )}

              {/* Color dot */}
              <span style={{
                width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0,
              }} />

              {/* Tag name */}
              <span
                style={{ fontSize: 13, fontWeight: 500, cursor: 'pointer', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                onClick={() => navigate(`/?tag=${tag.name}`)}
                title="点击查看该标签的笔记"
              >
                {tag.name}
              </span>

              {/* Children count badge */}
              {hasChildren && (
                <span className="badge badge-gray" style={{ fontSize: 10, padding: '0px 6px' }}>
                  {tag.children!.length}
                </span>
              )}
            </div>

            {/* Delete action */}
            {confirmDeleteId === tag.id ? (
              <div className="flex items-center gap-1" style={{ animation: 'slideInRight 0.2s var(--ease-spring)' }}>
                <span style={{ fontSize: 11, color: 'var(--danger)' }}>删除？</span>
                <button
                  className="btn btn-danger btn-sm"
                  style={{ padding: '0.125rem 0.5rem', fontSize: 11 }}
                  onClick={() => handleDelete(tag.id)}
                >
                  确认
                </button>
                <button
                  className="btn btn-ghost btn-sm"
                  style={{ padding: '0.125rem 0.5rem', fontSize: 11 }}
                  onClick={() => setConfirmDeleteId(null)}
                >
                  取消
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDeleteId(tag.id)}
                className="btn-icon"
                style={{ width: 24, height: 24, opacity: 0, transition: 'opacity 0.15s' }}
                title="删除标签"
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
            )}
          </div>
        </div>,

        /* Children (recursive) */
        ...(hasChildren && !isCollapsed ? renderTree(tag.children!, level + 1) : []),
      ];
    });
  };

  const allTags = flattenTree(tags);

  return (
    <div className="page-enter" style={{ padding: '0 2rem 2rem' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.021em', marginBottom: '1.5rem' }}>
        标签管理
      </h1>

      {/* ── Error ── */}
      {error && (
        <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: 'var(--danger-bg)', borderRadius: 10, color: 'var(--danger)', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* ── Create Tag ── */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
          {creatingInline ? '新建标签' : '标签树'}
          <span style={{ fontWeight: 400, color: 'var(--apple-text-tertiary)', marginLeft: 8, fontSize: 12 }}>
            ({allTags.length})
          </span>
        </h3>

        {creatingInline ? (
          <div className="animate-slide-up">
            <div className="flex gap-2" style={{ marginBottom: 8 }}>
              <input
                type="text"
                value={newTagName}
                onChange={(e) => setNewTagName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                className="input"
                placeholder="标签名称"
                autoFocus
              />
              <select
                value={newTagParent ?? ''}
                onChange={(e) => setNewTagParent(e.target.value ? Number(e.target.value) : undefined)}
                style={{
                  padding: '0.375rem 0.625rem', border: '1px solid var(--apple-border)',
                  borderRadius: 8, fontSize: 13, background: 'var(--apple-surface)',
                  fontFamily: 'inherit', color: 'var(--apple-text)', outline: 'none',
                  maxWidth: 160,
                }}
              >
                <option value="">无父标签</option>
                {allTags.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <button className="btn btn-primary btn-sm" onClick={handleCreate} disabled={loading}>
                {loading ? '创建中...' : '创建'}
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => { setCreatingInline(false); setNewTagName(''); }}>
                取消
              </button>
            </div>
          </div>
        ) : (
          <button className="btn btn-secondary btn-sm" onClick={() => setCreatingInline(true)}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            新建标签
          </button>
        )}
      </div>

      {/* ── Tags Tree ── */}
      <div className="card" style={{ padding: '0.5rem 0' }}>
        {tags.length === 0 ? (
          <div className="empty-state" style={{ padding: '2rem 0' }}>
            <svg className="empty-state-icon" viewBox="0 0 120 100" fill="none">
              <path d="M20.59 53.41l-7.17 7.17a2 2 0 0 0 0 2.83l7.17 7.17" stroke="currentColor" strokeWidth="2.5" fill="none" opacity="0.5" />
              <circle cx="50" cy="60" r="20" stroke="currentColor" strokeWidth="2.5" fill="none" opacity="0.5" />
              <path d="M40 60h20M50 50v20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
            </svg>
            <h3 className="empty-state-title">暂无标签</h3>
            <p className="empty-state-desc">创建标签来组织你的笔记</p>
            <button className="btn btn-primary btn-sm" onClick={() => setCreatingInline(true)}>
              创建第一个标签
            </button>
          </div>
        ) : (
          <div>{renderTree(tags)}</div>
        )}
      </div>
    </div>
  );
}
