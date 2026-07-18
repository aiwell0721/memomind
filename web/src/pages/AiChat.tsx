import { useState, useRef, useEffect } from 'react';
import { api } from '../lib/api';

/* ═══════════════════════════════════════════
   AI 问答 — RAG Chat
   ═══════════════════════════════════════════ */

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
}

export default function AiChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: '你好！我是 AI 助手，可以基于你的笔记内容回答问题。试试问我点什么吧。' },
  ]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleAsk = async () => {
    const q = question.trim();
    if (!q || loading) return;

    setMessages((prev) => [...prev, { role: 'user', content: q }]);
    setQuestion('');
    setLoading(true);

    try {
      const res = await api.ask(q);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `❌ ${err instanceof Error ? err.message : '请求失败，请检查 AI 配置'}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '0 1.5rem' }}>
      {/* ── Header ── */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.021em', marginBottom: 4 }}>
          AI 问答
        </h1>
        <p style={{ fontSize: 13, color: 'var(--apple-text-secondary)' }}>
          基于你的笔记内容进行智能问答 · 支持追问和上下文理解
        </p>
      </div>

      {/* ── Chat Messages ── */}
      <div className="card" style={{ padding: '1.5rem', minHeight: 400, maxHeight: 'calc(100vh - 280px)', overflowY: 'auto', marginBottom: '1rem' }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ marginBottom: '1.25rem' }}>
            <div className="flex items-center gap-2" style={{ marginBottom: 6 }}>
              <div style={{
                width: 24, height: 24, borderRadius: '50%', display: 'flex',
                alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                fontSize: 11, fontWeight: 600,
                background: msg.role === 'user'
                  ? 'rgba(0,0,0,0.06)'
                  : 'linear-gradient(135deg, var(--accent), #40a4ff)',
                color: msg.role === 'user' ? 'var(--apple-text)' : '#fff',
              }}>
                {msg.role === 'user' ? '你' : 'AI'}
              </div>
              <span style={{ fontSize: 11, fontWeight: 600, color: msg.role === 'user' ? 'var(--apple-text)' : 'var(--accent)' }}>
                {msg.role === 'user' ? '你' : 'AI 助手'}
              </span>
            </div>
            <div style={{
              padding: '0.75rem 1rem',
              marginLeft: 32,
              borderRadius: 'var(--radius-md)',
              background: msg.role === 'user' ? 'rgba(0,0,0,0.03)' : 'rgba(0,113,227,0.06)',
              fontSize: '0.9375rem',
              lineHeight: 1.7,
              overflowWrap: 'break-word',
              wordBreak: 'break-word',
              whiteSpace: 'pre-wrap',
            }}>
              {msg.content}
            </div>

            {/* 来源笔记 */}
            {msg.sources && msg.sources.length > 0 && (
              <div style={{ marginLeft: 32, marginTop: 6 }}>
                <span style={{ fontSize: 11, color: 'var(--apple-text-tertiary)' }}>
                  来源: {msg.sources.join(', ')}
                </span>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2" style={{ marginLeft: 32, marginBottom: '1rem' }}>
            <div style={{
              width: 20, height: 20, borderRadius: '50%',
              border: '2px solid var(--apple-border)',
              borderTopColor: 'var(--accent)',
              animation: 'spin 0.6s linear infinite',
            }} />
            <span style={{ fontSize: 12, color: 'var(--apple-text-tertiary)' }}>思考中...</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input Area ── */}
      <div className="flex items-end gap-2" style={{ background: 'var(--card-bg)', borderRadius: 'var(--radius-md)', padding: '0.75rem', border: '0.5px solid var(--apple-border-light)' }}>
        <textarea
          ref={inputRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          className="input"
          placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
          rows={2}
          style={{ flex: 1, fontSize: 13, lineHeight: 1.6, resize: 'none', padding: '0.5rem 0.75rem' }}
          disabled={loading}
        />
        <button
          className="btn btn-primary"
          onClick={handleAsk}
          disabled={loading || !question.trim()}
          style={{ height: 38, flexShrink: 0, display: 'flex', alignItems: 'center', gap: 4 }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
          发送
        </button>
      </div>
    </div>
  );
}
