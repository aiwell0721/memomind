import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../lib/api';
import type { Annotation } from '../lib/api';
import { toast } from '../App';

/* ═══════════════════════════════════════════
   AnnotationSection Props
   ═══════════════════════════════════════════ */

interface AnnotationSectionProps {
  noteId: number;
}

/* ── 相对时间格式化 ── */
function formatTime(dateStr: string): string {
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

/* ── 递归统计备注总数 ── */
function countAll(anns: Annotation[]): number {
  let count = 0;
  for (const a of anns) {
    count += 1 + countAll(a.replies || []);
  }
  return count;
}

/* ═══════════════════════════════════════════
   AnnotationSection Component
   ═══════════════════════════════════════════ */

export default function AnnotationSection({ noteId }: AnnotationSectionProps) {
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [content, setContent] = useState('');
  const [replyTarget, setReplyTarget] = useState<Annotation | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /* ── 加载备注 ── */
  const loadAnnotations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getAnnotations(noteId);
      setAnnotations(data);
      setError('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载备注失败');
    } finally {
      setLoading(false);
    }
  }, [noteId]);

  useEffect(() => { loadAnnotations(); }, [loadAnnotations]);

  /* ── 提交备注 ── */
  const handleSubmit = async () => {
    if (!content.trim() || submitting) return;
    setSubmitting(true);
    try {
      await api.createAnnotation(noteId, content.trim(), replyTarget?.id);
      setContent('');
      setReplyTarget(null);
      toast('备注已添加');
      loadAnnotations();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : '添加备注失败', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  /* ── 删除备注（含确认） ── */
  const handleDelete = async (annotationId: number) => {
    try {
      await api.deleteAnnotation(annotationId);
      setConfirmDeleteId(null);
      toast('备注已删除');
      loadAnnotations();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : '删除失败', 'error');
    }
  };

  /* ── 点击回复：设置回复目标并聚焦输入框 ── */
  const handleReply = (ann: Annotation) => {
    setReplyTarget(ann);
    setContent('');
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  /* ── 取消回复 ── */
  const handleCancelReply = () => {
    setReplyTarget(null);
    setContent('');
  };

  /* ── 键盘事件：Enter 发送，Shift+Enter 换行 ── */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const totalCount = countAll(annotations);

  /* ── 渲染单条备注及其嵌套回复 ── */
  const renderAnnotation = (ann: Annotation, isReply = false) => {
    const initials = (ann.author || '?').charAt(0).toUpperCase();
    return (
      <div key={ann.id}>
        <div style={{ display: 'flex', gap: 10, padding: isReply ? '0.5rem 0' : '0.625rem 0' }}>
          {/* 头像：首字母圆圈 */}
          <div style={{
            width: 28, height: 28, borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--accent-light), var(--accent-lighter))',
            color: 'var(--accent)',
            fontSize: 12, fontWeight: 600,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, marginTop: 2,
          }}>
            {initials}
          </div>

          {/* 备注内容区 */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--apple-text)' }}>
                {ann.author || '匿名'}
              </span>
              <span style={{ fontSize: 11, color: 'var(--apple-text-tertiary)' }}>
                {formatTime(ann.created_at)}
              </span>
            </div>
            <div style={{
              fontSize: '0.8125rem', lineHeight: 1.6, color: 'var(--apple-text)',
              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {ann.content}
            </div>

            {/* 操作按钮区 */}
            <div style={{ marginTop: 4, display: 'flex', gap: 8, alignItems: 'center' }}>
              <button
                onClick={() => handleReply(ann)}
                style={{
                  fontSize: 11, color: 'var(--apple-text-tertiary)',
                  background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--apple-text-tertiary)'; }}
              >
                回复
              </button>

              {/* 删除：默认隐藏，悬停显示；点击后展开确认 */}
              {confirmDeleteId === ann.id ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, animation: 'slideInRight 0.2s var(--ease-spring)' }}>
                  <span style={{ fontSize: 11, color: 'var(--danger)' }}>确定删除？</span>
                  <button
                    className="btn btn-danger btn-sm"
                    style={{ fontSize: 10, padding: '0.125rem 0.375rem' }}
                    onClick={() => handleDelete(ann.id)}
                  >
                    确认
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ fontSize: 10, padding: '0.125rem 0.375rem' }}
                    onClick={() => setConfirmDeleteId(null)}
                  >
                    取消
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmDeleteId(ann.id)}
                  style={{
                    fontSize: 11, color: 'var(--apple-text-tertiary)',
                    background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                    opacity: 0,
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.color = 'var(--danger)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.opacity = '0'; e.currentTarget.style.color = 'var(--apple-text-tertiary)'; }}
                >
                  删除
                </button>
              )}
            </div>
          </div>
        </div>

        {/* 嵌套回复：左侧竖线缩进（thread 风格） */}
        {ann.replies && ann.replies.length > 0 && (
          <div style={{ marginLeft: 14, borderLeft: '2px solid var(--apple-border-light)', paddingLeft: 16 }}>
            {ann.replies.map((reply) => renderAnnotation(reply, true))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ marginTop: '1.5rem' }}>
      {/* 分隔线 */}
      <div style={{ borderTop: '0.5px solid var(--apple-border-light)', marginBottom: '1rem' }} />

      {/* 标题 */}
      <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: '0.75rem' }}>
        💬 备注 ({totalCount})
      </h3>

      {/* 错误提示 */}
      {error && (
        <div style={{ marginBottom: 12, padding: '0.75rem 1rem', background: 'var(--danger-bg)', borderRadius: 10, color: 'var(--danger)', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* 备注列表：加载中 / 空状态 / 列表 */}
      {loading ? (
        <div style={{ padding: '0.5rem 0' }}>
          <div className="skeleton skeleton-text" style={{ maxWidth: 300 }} />
          <div className="skeleton skeleton-text" style={{ maxWidth: 200 }} />
        </div>
      ) : annotations.length === 0 ? (
        <div style={{ padding: '1rem 0', fontSize: 13, color: 'var(--apple-text-tertiary)', textAlign: 'center' }}>
          暂无备注，来说点什么吧
        </div>
      ) : (
        <div>
          {annotations.map((ann) => renderAnnotation(ann))}
        </div>
      )}

      {/* 输入区 */}
      <div style={{ marginTop: '0.75rem', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          className="input"
          placeholder={replyTarget ? `回复 @${replyTarget.author}...` : '添加备注...'}
          rows={2}
          style={{
            flex: 1,
            fontFamily: 'inherit',
            fontSize: 13,
            lineHeight: 1.5,
            resize: 'none',
            padding: '0.5rem 0.75rem',
          }}
        />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleSubmit}
            disabled={submitting || !content.trim()}
          >
            {submitting ? '发送中' : '发送'}
          </button>
          {replyTarget && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={handleCancelReply}
              style={{ fontSize: 11 }}
            >
              取消回复
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
