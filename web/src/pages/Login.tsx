import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { api } from '../lib/api';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');
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
    if (!password.trim()) {
      setError('请输入密码');
      return;
    }
    if (mode === 'register' && password.length < 6) {
      setError('密码至少 6 个字符');
      return;
    }

    setLoading(true);
    setError('');

    try {
      if (mode === 'register') {
        await api.register(username.trim(), password, username.trim());
        // 注册成功后自动登录
        const res = await api.login(username.trim(), password);
        login(username.trim(), res.access_token);
      } else {
        const res = await api.login(username.trim(), password);
        login(username.trim(), res.access_token);
      }
      navigate('/');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : (mode === 'register' ? '注册失败' : '登录失败');
      if (message.includes('401')) {
        setError(mode === 'register' ? '注册失败' : '用户名或密码错误');
      } else if (message.includes('409')) {
        setError('用户名已存在');
      } else {
        setError(message);
      }
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

        {/* Card */}
        <div className="card" style={{ padding: '2rem' }}>
          <h2 style={{
            fontSize: '1.125rem',
            fontWeight: 600,
            marginBottom: '1.5rem',
            letterSpacing: '-0.01em',
          }}>
            {mode === 'login' ? '登录' : '注册'}
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
                密码
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="输入密码"
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
              {loading ? (mode === 'register' ? '注册中...' : '登录中...') : (mode === 'register' ? '注册' : '登录')}
            </button>
          </form>

          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => {
                setMode(mode === 'login' ? 'register' : 'login');
                setError('');
              }}
              style={{ fontSize: 13 }}
            >
              {mode === 'login' ? '没有账号？注册' : '已有账号？登录'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
