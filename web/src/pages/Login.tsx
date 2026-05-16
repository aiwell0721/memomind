import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { api } from '../lib/api';

export default function Login() {
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setError('请输入用户名');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const res = await api.login(username.trim());
      login(username.trim(), res.access_token);
      navigate('/');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '登录失败';
      setError(message.includes('401') ? '用户不存在' : message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="flex items-center justify-center fade-in"
      style={{
        minHeight: '100vh',
        background: 'var(--apple-bg)',
      }}
    >
      <div style={{ width: '100%', maxWidth: 400, padding: '0 1.5rem' }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🧠</div>
          <h1 style={{
            fontSize: '2rem',
            fontWeight: 700,
            letterSpacing: '-0.03em',
            marginBottom: 8,
          }}>
            MemoMind
          </h1>
          <p style={{
            fontSize: 14,
            color: 'var(--apple-text-secondary)',
            fontWeight: 400,
          }}>
            团队知识库与智能笔记系统
          </p>
        </div>

        {/* Login card */}
        <div className="card" style={{ padding: '2rem' }}>
          <h2 style={{
            fontSize: '1.125rem',
            fontWeight: 600,
            marginBottom: '1.5rem',
            letterSpacing: '-0.01em',
          }}>
            登录
          </h2>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label
                style={{
                  display: 'block',
                  fontSize: 13,
                  fontWeight: 500,
                  color: 'var(--apple-text-secondary)',
                  marginBottom: 6,
                }}
              >
                用户名
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input"
                placeholder="输入用户名"
                autoFocus
              />
            </div>

            {error && (
              <div style={{
                marginBottom: 16,
                padding: '0.625rem 0.875rem',
                background: 'var(--danger-bg)',
                borderRadius: 10,
                color: 'var(--danger)',
                fontSize: 13,
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.75rem',
                background: 'var(--accent)',
                color: 'white',
                borderRadius: 10,
                fontSize: 14,
                fontWeight: 600,
                border: 'none',
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.5 : 1,
                transition: 'all 0.2s',
                fontFamily: 'inherit',
                letterSpacing: '-0.01em',
              }}
            >
              {loading ? '登录中...' : '登录'}
            </button>
          </form>
        </div>

        {/* Hint */}
        <div style={{
          marginTop: 20,
          padding: '0.875rem 1rem',
          background: 'rgba(0,0,0,0.02)',
          borderRadius: 10,
          fontSize: 12,
          color: 'var(--apple-text-secondary)',
          lineHeight: 1.6,
        }}>
          <p>提示：首次使用请先注册（通过 API 或 CLI）</p>
          <code style={{
            display: 'block',
            marginTop: 6,
            background: 'rgba(0,0,0,0.04)',
            padding: '0.25rem 0.5rem',
            borderRadius: 4,
            fontSize: 11,
            fontFamily: '"SF Mono", Menlo, monospace',
          }}>
            python cli.py create-user --username demo
          </code>
        </div>
      </div>
    </div>
  );
}
