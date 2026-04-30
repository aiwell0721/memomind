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
        className="flex items-center justify-between py-2 px-3 hover:bg-gray-50 rounded group"
        style={{ paddingLeft: `${level * 1.5 + 0.75}rem` }}
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">{level === 0 ? '📁' : '📂'}</span>
          <span className="font-medium">{tag.name}</span>
          {tag.children && tag.children.length > 0 && (
            <span className="text-xs text-gray-400">({tag.children.length} 子标签)</span>
          )}
        </div>
        <button
          className="opacity-0 group-hover:opacity-100 p-1 text-red-400 hover:text-red-600 transition"
          onClick={() => handleDelete(tag.id)}
        >
          🗑️
        </button>
      </div>,
      ...(tag.children ? renderTagTree(tag.children, level + 1) : []),
    ]);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">🏷️ 标签管理</h1>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Create tag */}
      <div className="card mb-4">
        <h3 className="font-medium mb-3">新建标签</h3>
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
        <h3 className="font-medium mb-3">标签树 ({tags.length})</h3>
        {tags.length === 0 ? (
          <p className="text-gray-400 text-center py-4">暂无标签</p>
        ) : (
          <div className="space-y-0">{renderTagTree(tags)}</div>
        )}
      </div>
    </div>
  );
}
