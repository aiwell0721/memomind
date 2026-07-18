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
    if (!username.trim()) { setError('请输入用户名'); return; }
    if (!password.trim()) { setError('请输入密码'); return; }
    if (mode === 'register' && password.length < 6) { setError('密码至少 6 个字符'); return; }

    setLoading(true);
    setError('');

    try {
      if (mode === 'register') {
        await api.register(username.trim(), password, username.trim());
        const res = await api.login(username.trim(), password);
        login(username.trim(), res.access_token);
      } else {
        const res = await api.login(username.trim(), password);
        login(username.trim(), res.access_token);
      }
      navigate('/');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : (mode === 'register' ? '注册失败' : '登录失败');
      if (message.includes('401')) setError(mode === 'register' ? '注册失败' : '用户名或密码错误');
      else if (message.includes('409')) setError('用户名已存在');
      else setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="flex items-center justify-center"
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(160deg, var(--apple-bg) 0%, #e8edf3 50%, #dce5f0 100%)',
      }}
    >
      {/* Decorative background blobs */}
      <div style={{
        position: 'fixed', top: '-20%', right: '-10%',
        width: '500px', height: '500px',
        background: 'radial-gradient(circle, rgba(0,113,227,0.06) 0%, transparent 70%)',
        borderRadius: '50%', pointerEvents: 'none',
      }} />
      <div style={{
        position: 'fixed', bottom: '-15%', left: '-8%',
        width: '400px', height: '400px',
        background: 'radial-gradient(circle, rgba(0,113,227,0.05) 0%, transparent 70%)',
        borderRadius: '50%', pointerEvents: 'none',
      }} />

      <div style={{ width: '100%', maxWidth: 400, padding: '0 1.5rem', position: 'relative', zIndex: 1 }}>
        {/* Logo Area */}
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          {/* SVG Logo — stylized brain/notebook */}
          <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'center' }}>
            <svg width="56" height="56" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="logoGrad" x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#0071e3" />
                  <stop offset="1" stopColor="#40a4ff" />
                </linearGradient>
              </defs>
              <rect x="4" y="8" width="38" height="44" rx="6" stroke="url(#logoGrad)" strokeWidth="3" fill="none" />
              <line x1="14" y1="22" x2="32" y2="22" stroke="url(#logoGrad)" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="14" y1="30" x2="32" y2="30" stroke="url(#logoGrad)" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="14" y1="38" x2="24" y2="38" stroke="url(#logoGrad)" strokeWidth="2.5" strokeLinecap="round" />
              {/* Circuit lines on the right */}
              <path d="M44 14h6m-6 8h6m-6 8h3" stroke="url(#logoGrad)" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="44" cy="14" r="2" fill="#0071e3" />
              <circle cx="44" cy="22" r="2" fill="#0071e3" />
              <circle cx="44" cy="30" r="2" fill="#0071e3" />
            </svg>
          </div>
          <h1 style={{
            fontSize: '2rem', fontWeight: 700,
            letterSpacing: '-0.03em', marginBottom: 8,
            background: 'linear-gradient(135deg, var(--apple-text) 0%, #555 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            MemoMind
          </h1>
          <p style={{ fontSize: 14, color: 'var(--apple-text-secondary)', fontWeight: 400 }}>
            团队知识库与智能笔记系统
          </p>
        </div>

        {/* Card */}
        <div className="card" style={{
          padding: '2rem',
          boxShadow: 'var(--shadow-lg)',
          borderRadius: 'var(--radius-xl)',
          background: 'rgba(255,255,255,0.75)',
          backdropFilter: 'blur(20px) saturate(180%)',
          WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        }}>
          {/* Segmented Control — Login / Register */}
          <div className="segmented-control" style={{ marginBottom: '1.5rem' }}>
            <button
              className={`segmented-control-btn ${mode === 'login' ? 'active' : ''}`}
              onClick={() => { setMode('login'); setError(''); }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                <polyline points="10 17 15 12 10 7" />
                <line x1="15" y1="12" x2="3" y2="12" />
              </svg>
              登录
            </button>
            <button
              className={`segmented-control-btn ${mode === 'register' ? 'active' : ''}`}
              onClick={() => { setMode('register'); setError(''); }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <line x1="19" y1="8" x2="19" y2="14" />
                <line x1="22" y1="11" x2="16" y2="11" />
              </svg>
              注册
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: 'var(--apple-text-secondary)', marginBottom: 6 }}>
                用户名
              </label>
              <div style={{ position: 'relative' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
                  style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', opacity: 0.35, pointerEvents: 'none' }}>
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input"
                  placeholder="输入用户名"
                  autoFocus
                  style={{ paddingLeft: 36 }}
                />
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: 'var(--apple-text-secondary)', marginBottom: 6 }}>
                密码
              </label>
              <div style={{ position: 'relative' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
                  style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', opacity: 0.35, pointerEvents: 'none' }}>
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input"
                  placeholder="输入密码"
                  style={{ paddingLeft: 36 }}
                />
              </div>
            </div>

            {error && (
              <div style={{
                marginBottom: 16, padding: '0.625rem 0.875rem',
                background: 'var(--danger-bg)', borderRadius: 10,
                color: 'var(--danger)', fontSize: 13,
                display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary btn-lg"
              style={{ width: '100%' }}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                  </svg>
                  {mode === 'register' ? '注册中...' : '登录中...'}
                </span>
              ) : (mode === 'register' ? '创建账号' : '登录')}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p style={{
          textAlign: 'center', marginTop: '2rem',
          fontSize: 12, color: 'var(--apple-text-tertiary)',
        }}>
          v3.0.0 · MemoMind &copy; {new Date().getFullYear()}
        </p>
      </div>
    </div>
  );
}
