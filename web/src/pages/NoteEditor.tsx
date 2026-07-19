import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { marked } from 'marked';
import { api } from '../lib/api';
import type { Note, Version, Collaborator } from '../lib/api';
import AnnotationSection from '../components/AnnotationSection';
import { createWsClient } from '../lib/api';
import { toast } from '../App';

/* ═══════════════════════════════════════════
   Markdown Syntax Reference
   ═══════════════════════════════════════════ */

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

/* ── Action color mapping ── */
const actionColors: Record<string, string> = {
  create: 'var(--success)',
  update: 'var(--accent)',
  manual_save: 'var(--warning)',
};

/* ── Friendly action labels ── */
const actionLabels: Record<string, string> = {
  create: '创建了笔记',
  update: '更新了笔记',
  delete: '删除了笔记',
  search: '搜索了笔记',
  login: '登录了系统',
  manual_save: '手动保存了版本',
  workspace_create: '创建了工作区',
  workspace_update: '更新了工作区',
  workspace_delete: '删除了工作区',
};

/* ═══════════════════════════════════════════
   NoteEditor Component
   ═══════════════════════════════════════════ */

export default function NoteEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [note, setNote] = useState<Note | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [editTags, setEditTags] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [versions, setVersions] = useState<Version[]>([]);
  const [showVersions, setShowVersions] = useState(false);
  const [showSyntax, setShowSyntax] = useState(false);
  const [incomingLinks, setIncomingLinks] = useState<unknown[]>([]);
  const [onlineUsers, setOnlineUsers] = useState<Collaborator[]>([]);
  const [remoteEdit, setRemoteEdit] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('preview');
  const [syntaxSearch, setSyntaxSearch] = useState('');
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [aiSummaryLoading, setAiSummaryLoading] = useState(false);
  const [aiTags, setAiTags] = useState<string[] | null>(null);
  const [aiTagsLoading, setAiTagsLoading] = useState(false);
  const [showSummary, setShowSummary] = useState(true);

  const wsRef = useRef<ReturnType<typeof createWsClient> | null>(null);
  const isLocalEdit = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /* ── Load Note ── */
  const loadNote = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await api.getNote(Number(id));
      setNote(data);
      setEditTitle(data.title);
      setEditContent(data.content);
      setEditTags(data.tags.join(', '));
      if (data.ai_summary) {
        setAiSummary(data.ai_summary);
        setShowSummary(true);
      } else {
        setAiSummary(null);
      }
      api.versions(Number(id), 10).then(setVersions).catch(() => {});
      api.incomingLinks(Number(id)).then(setIncomingLinks).catch(() => {});
      setError('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadNote(); }, [loadNote]);

  /* ── WebSocket ── */
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
    return () => { ws.disconnect(); wsRef.current = null; };
  }, [id, note?.updated_at]);

  /* ── Save ── */
  const handleSave = async () => {
    if (!note || !editTitle.trim()) return;
    setSaving(true);
    isLocalEdit.current = true;
    try {
      const tags = editTags.split(',').map((t) => t.trim()).filter(Boolean);
      await api.updateNote(note.id, { title: editTitle, content: editContent, tags });
      setEditMode(false);
      toast('笔记已保存');
      loadNote();
      wsRef.current?.sendEdit(editTitle, editContent);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
      setTimeout(() => { isLocalEdit.current = false; }, 500);
    }
  };

  /* ── Auto-sync while editing ── */
  useEffect(() => {
    if (!editMode || !wsRef.current) return;
    const timer = setTimeout(() => {
      wsRef.current?.sendEdit(editTitle, editContent);
    }, 500);
    return () => clearTimeout(timer);
  }, [editTitle, editContent, editMode]);

  /* ── Version operations ── */
  const handleSaveVersion = async () => {
    if (!note) return;
    try {
      await api.saveVersion(note.id, '手动保存');
      toast('版本快照已保存');
      api.versions(note.id, 10).then(setVersions);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存版本失败');
    }
  };

  const handleRestoreVersion = async (versionId: number) => {
    if (!confirm('恢复到这个版本？当前未保存的内容将被覆盖。')) return;
    try {
      await api.restoreVersion(versionId);
      toast('版本已恢复');
      loadNote();
      setShowVersions(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '恢复失败');
    }
  };

  /* ── Syntax panel: click to insert ── */
  const handleInsertSyntax = (example: string) => {
    if (!textareaRef.current) return;
    const ta = textareaRef.current;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const text = editContent;
    setEditContent(text.substring(0, start) + example + text.substring(end));
    setTimeout(() => {
      ta.focus();
      ta.setSelectionRange(start + example.length, start + example.length);
    }, 0);
  };

  const filteredSyntax = markdownSyntax.filter(
    (s) => s.desc.includes(syntaxSearch) || s.element.includes(syntaxSearch)
  );

  /* ── Loading / Not Found ── */
  if (loading && !note) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center' }}>
        <div className="skeleton skeleton-card" style={{ maxWidth: 600, margin: '0 auto' }} />
        <div style={{ marginTop: 16 }}>
          <div className="skeleton skeleton-text" style={{ maxWidth: 400, margin: '0 auto 8px' }} />
          <div className="skeleton skeleton-text" style={{ maxWidth: 300, margin: '0 auto' }} />
        </div>
      </div>
    );
  }

  if (!note) {
    return (
      <div className="empty-state" style={{ padding: '4rem 1.5rem' }}>
        <svg className="empty-state-icon" viewBox="0 0 120 100" fill="none">
          <circle cx="60" cy="45" r="25" stroke="currentColor" strokeWidth="2.5" fill="none" opacity="0.5" />
          <line x1="45" y1="65" x2="75" y2="65" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
          <line x1="55" y1="60" x2="65" y2="70" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
          <line x1="65" y1="60" x2="55" y2="70" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
        </svg>
        <h3 className="empty-state-title">笔记不存在</h3>
        <button className="btn btn-secondary" style={{ marginTop: 8 }} onClick={() => navigate('/')}>
          返回列表
        </button>
      </div>
    );
  }

  return (
    <div className="page-enter" style={{ padding: '1.5rem 2rem', maxWidth: 960, margin: '0 auto' }}>
      {/* ═══ Toolbar ═══ */}
      <div className="flex items-center justify-between"
        style={{ marginBottom: '1rem', paddingBottom: '0.75rem', borderBottom: '0.5px solid var(--apple-border-light)' }}>
        {/* Left: Back + Online users */}
        <div className="flex items-center gap-2">
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            返回
          </button>

          {/* Online users with status dots */}
          {onlineUsers.length > 0 && (
            <div className="flex items-center gap-1" style={{ marginLeft: 8 }}>
              {onlineUsers.map((u) => (
                <div key={u.user_id} style={{ position: 'relative' }} title={u.username}>
                  <span style={{
                    width: 28, height: 28, borderRadius: '50%',
                    background: 'linear-gradient(135deg, var(--accent-light), var(--accent-lighter))',
                    color: 'var(--accent)', fontSize: 11, fontWeight: 600,
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {u.username.charAt(0).toUpperCase()}
                  </span>
                  {/* Green online dot */}
                  <span style={{
                    position: 'absolute', bottom: -1, right: -1,
                    width: 9, height: 9, borderRadius: '50%',
                    background: 'var(--success)', border: '2px solid var(--apple-surface)',
                  }} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Version history button with badge */}
          <button className="btn btn-secondary btn-sm" onClick={() => setShowVersions(!showVersions)}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            版本
            {versions.length > 0 && (
              <span className="badge badge-blue" style={{ marginLeft: 2, fontSize: 10, padding: '0 5px', minWidth: 18, justifyContent: 'center' }}>
                {versions.length}
              </span>
            )}
          </button>

          {/* Edit / Save / Cancel */}
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
              <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving || !editTitle.trim()}>
                {saving ? '保存中...' : '保存'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── Remote edit toast ── */}
      {remoteEdit && (
        <div style={{ marginBottom: 12, padding: '0.5rem 1rem', background: 'var(--accent-light)', borderRadius: 8, color: 'var(--accent)', fontSize: 13, animation: 'slideUp 0.2s var(--ease-spring)' }}>
          协作者已更新内容
        </div>
      )}

      {/* ── Error ── */}
      {error && (
        <div style={{ marginBottom: 12, padding: '0.75rem 1rem', background: 'var(--danger-bg)', borderRadius: 10, color: 'var(--danger)', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* ═══ Versions Timeline Panel ═══ */}
      {showVersions && (
        <div className="card animate-slide-up" style={{ marginBottom: '1rem', padding: '1.25rem' }}>
          <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>版本历史</h3>
            <button className="btn btn-primary btn-sm" onClick={handleSaveVersion}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              保存当前版本
            </button>
          </div>

          {versions.length === 0 ? (
            <div className="empty-state" style={{ padding: '1.5rem 0' }}>
              <p style={{ fontSize: 13, color: 'var(--apple-text-tertiary)' }}>暂无版本历史，点击上方保存第一个版本</p>
            </div>
          ) : (
            <div className="timeline" style={{ maxHeight: 300, overflowY: 'auto' }}>
              {versions.map((v) => {
                const color = actionColors[v.change_summary] || 'var(--apple-text-tertiary)';
                return (
                  <div key={v.id} className="timeline-item">
                    <span className="timeline-dot" style={{ background: color }} />
                    <div style={{
                      padding: '0.5rem 0.75rem', background: 'var(--apple-bg)', borderRadius: 8,
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    }}>
                      <div>
                        <span style={{ fontSize: 13, fontWeight: 500 }}>
                          {actionLabels[v.change_summary] || v.change_summary || '自动保存'}
                        </span>
                        <span style={{ fontSize: 11, color: 'var(--apple-text-tertiary)', marginLeft: 8 }}>
                          {new Date(v.created_at).toLocaleString('zh-CN')}
                        </span>
                      </div>
                      <button className="btn btn-secondary btn-sm" onClick={() => handleRestoreVersion(v.id)}>
                        恢复
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ═══ Title & Meta ═══ */}
      {editMode ? (
        <div style={{ marginBottom: '1rem' }}>
          <input
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            style={{
              fontSize: '1.5rem', fontWeight: 700, width: '100%',
              border: 'none', borderBottom: '1px solid var(--apple-border)',
              padding: '0.5rem 0', marginBottom: 8,
              fontFamily: 'inherit', letterSpacing: '-0.021em',
              outline: 'none', background: 'transparent', color: 'var(--apple-text)',
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
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.021em', marginBottom: 8 }}>
            {note.title}
          </h1>
          <div className="flex items-center gap-3" style={{ marginBottom: '1rem', flexWrap: 'wrap' }}>
            {note.tags.map((tag, i) => (
              <span key={i} className="tag">
                <span className="tag-dot" style={{ background: ['#0071e3','#30b158','#f09824','#ee4b40'][i % 4] }} />
                {tag}
              </span>
            ))}
            <span style={{ fontSize: 12, color: 'var(--apple-text-tertiary)' }}>
              更新于 {new Date(note.updated_at).toLocaleString('zh-CN')}
            </span>
          </div>
        </>
      )}

      {/* ═══ View Mode Toggle + AI Actions + Syntax Panel ═══ */}
      {!editMode && (
        <div className="flex items-center justify-between" style={{ marginBottom: '0.75rem', flexWrap: 'wrap', gap: 8 }}>
          <div className="flex items-center gap-2" style={{ flexWrap: 'wrap' }}>
            <div className="view-toggle">
              <button className={`view-toggle-btn ${viewMode === 'preview' ? 'active' : ''}`} onClick={() => setViewMode('preview')}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ marginRight: 4 }}>
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                预览
              </button>
              <button className={`view-toggle-btn ${viewMode === 'raw' ? 'active' : ''}`} onClick={() => setViewMode('raw')}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ marginRight: 4 }}>
                  <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
                </svg>
                RAW
              </button>
            </div>

            {/* AI 操作按钮 */}
            <button
              className="btn btn-ghost btn-sm"
              style={{ fontSize: 12, color: 'var(--accent)' }}
              onClick={async () => {
                if (!note) return;
                setAiSummaryLoading(true); setAiSummary(null);
                try {
                  const res = await api.summarizeNote(note.id);
                  setAiSummary(res.summary);
                  await api.updateNote(note.id, { ai_summary: res.summary });
                  setNote({ ...note, ai_summary: res.summary });
                } catch (err) {
                  toast(err instanceof Error ? err.message : '摘要生成失败', 'error');
                } finally { setAiSummaryLoading(false); }
              }}
              disabled={aiSummaryLoading}
              title="AI 生成摘要"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ marginRight: 4 }}>
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              {aiSummaryLoading ? '生成中...' : 'AI 摘要'}
            </button>

            <button
              className="btn btn-ghost btn-sm"
              style={{ fontSize: 12, color: 'var(--success)' }}
              onClick={async () => {
                if (!note) return;
                setAiTagsLoading(true); setAiTags(null);
                try {
                  const res = await api.autoTagNote(note.id);
                  setAiTags(res.tags);
                  toast(`AI 推荐标签: ${res.tags.join(', ')}`);
                } catch (err) {
                  toast(err instanceof Error ? err.message : '自动标签失败', 'error');
                } finally { setAiTagsLoading(false); }
              }}
              disabled={aiTagsLoading}
              title="AI 自动推荐标签"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ marginRight: 4 }}>
                <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
                <line x1="7" y1="7" x2="7.01" y2="7" />
              </svg>
              {aiTagsLoading ? '分析中...' : '自动标签'}
            </button>
          </div>

          <button className="btn btn-ghost btn-sm" onClick={() => setShowSyntax(!showSyntax)} style={{ fontSize: 12 }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            {showSyntax ? '收起语法' : 'Markdown 语法'}
          </button>
        </div>
      )}

      {/* ═══ Syntax Panel (compact table, search, click-to-insert) ═══ */}
      {!editMode && showSyntax && (
        <div className="card animate-slide-up" style={{ marginBottom: '1rem', padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '0.625rem 1rem', borderBottom: '0.5px solid var(--apple-border-light)', background: 'var(--apple-bg)' }}>
            <input
              type="text"
              value={syntaxSearch}
              onChange={(e) => setSyntaxSearch(e.target.value)}
              className="input"
              placeholder="搜索语法..."
              style={{ fontSize: 12, padding: '0.375rem 0.75rem' }}
            />
          </div>
          <div style={{ maxHeight: 300, overflowY: 'auto' }}>
            {filteredSyntax.map((row, i) => (
              <div key={i} className="syntax-row"
                onClick={() => { setEditMode(true); setTimeout(() => handleInsertSyntax(row.example), 50); }}
                style={{ cursor: 'pointer' }}
                title="点击插入"
              >
                <span className="syntax-example">{row.example.split('\n')[0]}</span>
                <span className="syntax-desc">{row.desc}</span>
              </div>
            ))}
            {filteredSyntax.length === 0 && (
              <div style={{ padding: '1rem', textAlign: 'center', fontSize: 12, color: 'var(--apple-text-tertiary)' }}>
                没有匹配的语法
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══ AI 推荐标签结果 ═══ */}
      {aiTags && aiTags.length > 0 && (
        <div className="card animate-slide-up" style={{ marginBottom: '1rem', padding: '1rem 1.5rem', borderLeft: '3px solid var(--success)' }}>
          <div className="flex items-center gap-2" style={{ marginBottom: 8 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2" strokeLinecap="round">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
              <line x1="7" y1="7" x2="7.01" y2="7" />
            </svg>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--success)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>AI 推荐标签</span>
            <button
              className="btn-icon"
              style={{ marginLeft: 'auto', width: 20, height: 20 }}
              onClick={() => setAiTags(null)}
              title="收起"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div className="flex items-center gap-2" style={{ flexWrap: 'wrap' }}>
            {aiTags.map((tag, i) => (
              <span key={i} className="tag">
                <span className="tag-dot" style={{ background: ['#0071e3','#30b158','#f09824','#ee4b40'][i % 4] }} />
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ═══ AI 摘要卡片（持久化 + 可折叠） ═══ */}
      {(aiSummary || note?.ai_summary) && (note?.content?.length ?? 0) >= 100 && (
        <div className="card" style={{
          marginBottom: '1rem', padding: '1.25rem 1.5rem',
          borderLeft: '3px solid var(--accent)'
        }}>
          <div className="flex items-center gap-2" style={{ marginBottom: showSummary ? 8 : 0 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>📝 AI 摘要</span>
            <button
              className="btn-icon"
              style={{ marginLeft: 'auto', width: 20, height: 20 }}
              onClick={() => setShowSummary(!showSummary)}
              title={showSummary ? '收起' : '展开'}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                {showSummary ? (
                  <polyline points="18 15 12 9 6 15" />
                ) : (
                  <polyline points="6 9 12 15 18 9" />
                )}
              </svg>
            </button>
            <button
              className="btn-icon"
              style={{ width: 20, height: 20 }}
              onClick={async () => {
                if (!note) return;
                setAiSummaryLoading(true);
                try {
                  const res = await api.summarizeNote(note.id);
                  setAiSummary(res.summary);
                  await api.updateNote(note.id, { ai_summary: res.summary });
                  setNote({ ...note, ai_summary: res.summary });
                  setShowSummary(true);
                } catch (err) {
                  toast(err instanceof Error ? err.message : '摘要生成失败', 'error');
                } finally { setAiSummaryLoading(false); }
              }}
              disabled={aiSummaryLoading}
              title="重新生成"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <polyline points="23 4 23 10 17 10" />
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
              </svg>
            </button>
          </div>
          {showSummary && (
            <p style={{ fontSize: '0.9375rem', lineHeight: 1.75, color: 'var(--apple-text)', margin: 0, overflowWrap: 'break-word', wordBreak: 'break-word' }}>
              {aiSummary || note?.ai_summary}
            </p>
          )}
        </div>
      )}

      {/* ═══ Content Area ═══ */}
      {editMode ? (
        <textarea
          ref={textareaRef}
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          className="input"
          placeholder="内容（支持 Markdown）"
          rows={18}
          style={{
            fontFamily: '"SF Mono", SFMono-Regular, "JetBrains Mono", "Fira Code", Menlo, Consolas, monospace',
            fontSize: 13, lineHeight: 1.7,
          }}
        />
      ) : viewMode === 'raw' ? (
        <div className="raw-content">{note.content || '（空笔记）'}</div>
      ) : (
        <div className="card markdown-content" style={{ padding: '1.5rem 2rem' }}
          dangerouslySetInnerHTML={{ __html: marked(note.content || '_暂无内容_') }}
        />
      )}


      {/* ═══ 备注区 ═══ */}
      {note && <AnnotationSection noteId={note.id} />}

      {/* ═══ Incoming Links ═══ */}
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
                <span key={i} style={{ display: 'block', fontSize: 13, color: 'var(--accent)', cursor: 'pointer', padding: '0.375rem 0' }}>
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
