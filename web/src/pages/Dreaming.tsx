import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { DreamingReport, DreamingSession, DreamingChange } from '../lib/api';

/* ── 工具函数 ── */
function formatTime(dateStr: string | null): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

const statusMap: Record<string, { label: string; cls: string }> = {
  running: { label: '运行中', cls: 'bg-amber-100 text-amber-700' },
  completed: { label: '已完成', cls: 'bg-emerald-100 text-emerald-700' },
  failed: { label: '失败', cls: 'bg-rose-100 text-rose-700' },
  rolled_back: { label: '已回滚', cls: 'bg-slate-100 text-slate-500' },
};

function StatusBadge({ status }: { status: string }) {
  const s = statusMap[status] || { label: status, cls: 'bg-slate-100 text-slate-500' };
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${s.cls}`}>{s.label}</span>;
}

/* ── 策略配置 ── */
type StrategyKey = 'default' | 'aggressive' | 'conservative';

const STRATEGIES: { key: StrategyKey; label: string; desc: string; threshold: string; compression: string }[] = [
  { key: 'default', label: '默认', desc: '平衡精度与压缩率', threshold: '0.70', compression: '46%' },
  { key: 'aggressive', label: '激进', desc: '最大程度压缩', threshold: '0.65', compression: '60%' },
  { key: 'conservative', label: '保守', desc: '最小化信息损失', threshold: '0.75', compression: '28%' },
];

/* ── 小型内联 SVG 图标 ── */
const Icons = {
  Moon: (p: { className?: string }) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className={p.className}>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  ),
  Check: () => (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  Target: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /><path d="M21 12.79A9 9 0 1 1 11.21 3" />
    </svg>
  ),
  Play: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  ),
  Spinner: () => (
    <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="10" strokeDasharray="31.4 31.4" strokeLinecap="round" /></svg>
  ),
  Alert: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
  ),
  XCircle: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>
  ),
  CheckCircle: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>
  ),
  ChevronRight: (p: { open?: boolean }) => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
         className={`transition-transform duration-200 ${p.open ? 'rotate-90' : ''}`}>
      <polyline points="9 18 15 12 9 6" />
    </svg>
  ),
  Doc: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  ),
  Clock: () => (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round">
      <circle cx="12" cy="12" r="10" opacity="0.3" /><path d="M12 6v6l4 2" opacity="0.3" />
    </svg>
  ),
};

/* ── 变更类型配色 ── */
const changeTypeStyle: Record<string, string> = {
  merge: 'bg-blue-50 text-blue-600 border-blue-100',
  archive: 'bg-slate-100 text-slate-500 border-slate-200',
  split: 'bg-purple-50 text-purple-600 border-purple-100',
};

/* ═══════════════════════════════════════════════════════════════════════════ */
export default function Dreaming() {
/* ═══════════════════════════════════════════════════════════════════════════ */
  const [sessions, setSessions] = useState<DreamingSession[]>([]);
  const [changes, setChanges] = useState<Record<number, DreamingChange[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<DreamingReport | null>(null);
  const [strategy, setStrategy] = useState<StrategyKey>('default');
  const [dryRun, setDryRun] = useState(true);
  const [expandedSession, setExpandedSession] = useState<number | null>(null);
  const [rollbackMsg, setRollbackMsg] = useState('');

  const loadHistory = () => {
    api.dreaming.history(20).then(setSessions).catch(() => {});
  };

  useEffect(() => { loadHistory(); }, []);

  async function handleRun() {
    setLoading(true); setError(''); setResult(null);
    try {
      const r = await api.dreaming.run({ strategy, dry_run: dryRun });
      setResult(r);
      if (!dryRun) loadHistory();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '执行失败');
    } finally { setLoading(false); }
  }

  async function handleRollback(sessionId: number) {
    if (!confirm('确定回滚此次 Dreaming？原始笔记将恢复，合并笔记将被删除。')) return;
    setRollbackMsg('');
    try {
      const r = await api.dreaming.rollback(sessionId);
      setRollbackMsg(`已回滚：恢复 ${r.restored_notes} 条笔记，删除 ${r.deleted_merged_notes} 条合并笔记`);
      loadHistory();
    } catch (e: unknown) {
      setRollbackMsg(`回滚失败：${e instanceof Error ? e.message : String(e)}`);
    }
  }

  async function toggleChanges(sessionId: number) {
    if (expandedSession === sessionId) { setExpandedSession(null); return; }
    if (!changes[sessionId]) {
      try {
        const c = await api.dreaming.changes(sessionId);
        setChanges(prev => ({ ...prev, [sessionId]: c }));
      } catch { return; }
    }
    setExpandedSession(sessionId);
  }

  const compressionPct = (s: DreamingSession) => {
    if (s.input_count === 0) return '0.0';
    return ((1 - s.output_count / s.input_count) * 100).toFixed(1);
  };

  /* ── JSX ── */
  return (
    <div className="max-w-[900px] mx-auto px-6 py-10 pb-20 space-y-7 animate-fade-in">
      {/* ═══ 页面标题 ═══ */}
      <header className="space-y-1.5 mb-8">
        <h1 className="text-[28px] font-bold text-apple-text tracking-[-0.015em] leading-tight">记忆整理</h1>
        <p className="text-sm text-apple-text-tertiary leading-relaxed max-w-lg">
          基于 Embedding 聚类的离线记忆压缩，将相似主题笔记合并，减少信息冗余。
        </p>
      </header>

      {/* ═══ 控制面板 ═══ */}
      <section className="bg-white rounded-[20px] border border-apple-border/50 shadow-sm overflow-hidden">
        {/* 面板标题栏 */}
        <div className="px-5 py-3.5 border-b border-apple-border/30 bg-gradient-to-r from-apple-bg/50 to-transparent flex items-center gap-2.5">
          <Icons.Moon className="text-apple-accent shrink-0" />
          <span className="text-[13px] font-semibold text-apple-text">整理参数</span>
        </div>

        <div className="p-6 space-y-5">
          {/* ── 策略卡片 ── */}
          <fieldset>
            <legend className="text-[11px] font-semibold text-apple-text-secondary uppercase tracking-[0.06em] mb-3">
              压缩策略
            </legend>
            <div className="grid grid-cols-3 gap-3">
              {STRATEGIES.map(s => {
                const active = strategy === s.key;
                return (
                  <button
                    key={s.key}
                    onClick={() => setStrategy(s.key)}
                    className={`group relative rounded-[16px] border-2 p-4 text-left transition-all duration-200 focus:outline-none
                      ${active
                        ? 'border-apple-accent bg-[var(--apple-accent-light)] shadow-sm'
                        : 'border-[var(--apple-border-light)] bg-white hover:border-apple-border hover:shadow-sm'}`}
                  >
                    {active && (
                      <span className="absolute top-3 right-3 w-5 h-5 rounded-full bg-apple-accent flex items-center justify-center animate-scale-in">
                        <Icons.Check />
                      </span>
                    )}
                    <p className="text-sm font-semibold text-apple-text mb-0.5">{s.label}</p>
                    <p className="text-[11px] text-apple-text-tertiary leading-relaxed mb-3">{s.desc}</p>
                    <div className="flex items-center gap-2 text-[11px]">
                      <span className="px-1.5 py-0.5 rounded-md bg-apple-bg text-apple-text-secondary font-medium tabular-nums">
                        阈值 {s.threshold}
                      </span>
                      <span className="text-apple-text-tertiary tabular-nums">~{s.compression}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </fieldset>

          {/* ── 分隔 + 控制栏 ── */}
          <div className="border-t border-apple-border/[0.18] pt-5 space-y-4">
          <div className="flex items-center justify-between gap-4">
            {/* iOS 风格 Toggle */}
            <label className="flex items-center gap-3 cursor-pointer select-none group">
              <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} className="sr-only" />
              <div className={`relative w-10 h-6 rounded-full transition-colors duration-200 ${dryRun ? 'bg-apple-accent' : 'bg-gray-300'}`}>
                <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200 ${dryRun ? 'translate-x-[18px]' : 'translate-x-0.5'}`} />
              </div>
              <div>
                <p className="text-sm font-medium text-apple-text">预览模式</p>
                <p className="text-[11px] text-apple-text-tertiary">不写入数据库</p>
              </div>
            </label>

            {/* 执行按钮 */}
            <button
              onClick={handleRun}
              disabled={loading}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-apple-accent text-white rounded-xl text-sm font-semibold
                         hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200
                         shadow-sm hover:shadow-md active:scale-[0.98]"
            >
              {loading ? <><Icons.Spinner /> 执行中...</> : dryRun ? <><Icons.Target /> 预览</> : <><Icons.Play /> 执行 Dreaming</>}
            </button>
          </div>

          {/* ── 消息反馈 ── */}
          {error && (
            <div className="flex items-center gap-2.5 text-sm text-rose-600 bg-rose-50/80 rounded-xl px-4 py-3 border border-rose-200/60 animate-slide-up">
              <span className="shrink-0"><Icons.Alert /></span>
              <span>{error}</span>
            </div>
          )}
          {rollbackMsg && (
            <div className={`flex items-center gap-2.5 text-sm rounded-xl px-4 py-3 border animate-slide-up ${
              rollbackMsg.includes('失败')
                ? 'text-rose-600 bg-rose-50/80 border-rose-200/60'
                : 'text-emerald-600 bg-emerald-50/80 border-emerald-200/60'
            }`}>
              <span className="shrink-0">{rollbackMsg.includes('失败') ? <Icons.XCircle /> : <Icons.CheckCircle />}</span>
              <span>{rollbackMsg}</span>
            </div>
          )}

          {/* ── 结果报告 ── */}
          {result && (
            <div className="bg-gradient-to-br from-apple-bg via-apple-bg to-[var(--apple-accent-light)] rounded-xl border border-[var(--apple-accent)]/15 p-5 space-y-4 animate-slide-up">
              {/* 标题行 */}
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-apple-text flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  {result.dry_run ? '预览报告' : `Dreaming #${result.session_id} 完成`}
                </h4>
                <span className={`text-[11px] font-medium px-2.5 py-0.5 rounded-full border ${
                  result.dry_run
                    ? 'bg-amber-50 text-amber-600 border-amber-200/60'
                    : 'bg-emerald-50 text-emerald-600 border-emerald-200/60'
                }`}>
                  {result.dry_run ? '模拟运行' : '已执行'}
                </span>
              </div>

              {/* 5 列指标 */}
              <div className="grid grid-cols-5 gap-2">
                {([
                  { label: '输入', value: `${result.input_count} 条`, hl: false },
                  { label: '输出', value: `${result.output_count} 条`, hl: true },
                  { label: '压缩率', value: result.input_count > 0 ? `${((1 - result.output_count / result.input_count) * 100).toFixed(1)}%` : '—', hl: true },
                  { label: '合并', value: `${result.merged_count} 条`, hl: false },
                  { label: '归档', value: `${result.archived_count} 条`, hl: false },
                ] as const).map(item => (
                  <div key={item.label} className="bg-white rounded-lg border border-black/5 px-2.5 py-3 text-center">
                    <div className="text-[10px] text-apple-text-tertiary uppercase tracking-[0.05em] mb-1">{item.label}</div>
                    <div className={`text-base font-bold tabular-nums ${item.hl ? 'text-apple-accent' : 'text-apple-text'}`}>{item.value}</div>
                  </div>
                ))}
              </div>

              {/* 簇详情 */}
              {result.clusters.length > 0 && (
                <details className="group mt-4">
                  <summary className="text-xs text-apple-text-tertiary cursor-pointer hover:text-apple-text-secondary transition-colors flex items-center gap-1.5 select-none marker:hidden">
                    <Icons.ChevronRight />
                    簇详情（{result.clusters.length} 个多元素簇）
                  </summary>
                  <div className="mt-2 flex flex-wrap gap-1.5 pl-5">
                    {result.clusters.map((c, i) => (
                      <span key={i} className="inline-flex items-center gap-1 text-[11px] text-apple-text-tertiary bg-white rounded-md border border-black/5 px-2 py-0.5 font-mono">
                        <span className="text-apple-text-secondary font-medium">C{i + 1}</span>
                        #{c.join(', #')}
                      </span>
                    ))}
                  </div>
                </details>
              )}
            </div>
          )}
          </div>
        </div>
      </section>

      {/* ═══ 历史记录 ═══ */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-apple-text">历史记录</h2>
          {sessions.length > 0 && (
            <span className="text-xs text-apple-text-tertiary bg-apple-bg rounded-full px-2.5 py-0.5 tabular-nums">
              {sessions.length} 条
            </span>
          )}
        </div>

        {sessions.length === 0 ? (
          /* ── 空状态 ── */
          <div className="bg-white rounded-[20px] border border-dashed border-apple-border/60 py-16 flex flex-col items-center justify-center text-center">
            <span className="text-apple-border mb-4 opacity-50"><Icons.Clock /></span>
            <p className="text-sm text-apple-text-tertiary font-medium">暂无 Dreaming 记录</p>
            <p className="text-xs text-apple-text-tertiary/60 mt-1">执行一次压缩后，结果将显示在这里</p>
          </div>
        ) : (
          /* ── 数据表格 ── */
          <div className="bg-white rounded-[20px] border border-apple-border/50 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-apple-border/30 bg-apple-bg/50">
                    {['#', '时间', '策略', '状态', '输入', '输出', '压缩率', '操作'].map(h => (
                      <th key={h} className={`px-4 py-3 text-[11px] font-semibold text-apple-text-tertiary ${h === '操作' ? 'text-center' : h === '输入' || h === '输出' || h === '压缩率' ? 'text-right' : 'text-left'}`}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-black/5">
                  {sessions.map((s, i) => {
                    const isExpanded = expandedSession === s.id;
                    const canRollback = s.status === 'completed';
                    return (
                      <tr key={s.id}
                          className="hover:bg-apple-bg/40 transition-colors"
                          style={{ animationDelay: `${i * 30}ms` }}>
                        <td className="px-4 py-3 text-apple-text-tertiary text-xs tabular-nums w-10">{s.id}</td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs text-apple-text-secondary">{formatTime(s.started_at)}</td>
                        <td className="px-4 py-3 text-xs text-apple-text-secondary capitalize">{s.trigger}</td>
                        <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
                        <td className="px-4 py-3 text-right text-xs tabular-nums text-apple-text-secondary">{s.input_count}</td>
                        <td className="px-4 py-3 text-right text-xs tabular-nums text-apple-text-secondary">{s.output_count}</td>
                        <td className="px-4 py-3 text-right text-xs font-semibold tabular-nums text-apple-text">{compressionPct(s)}%</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-center gap-1">
                            <button onClick={() => toggleChanges(s.id)}
                                    className="text-xs text-apple-accent hover:bg-[var(--apple-accent-light)] font-medium transition-colors px-2.5 py-1 rounded-lg">
                              {isExpanded ? '收起' : '详情'}
                            </button>
                            {canRollback && (
                              <button onClick={() => handleRollback(s.id)}
                                      className="text-xs text-rose-500 hover:bg-rose-50 font-medium transition-colors px-2.5 py-1 rounded-lg">
                                回滚
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* ── 展开详情 ── */}
            {expandedSession !== null && changes[expandedSession] && (
              <div className="border-t border-apple-border/30 px-5 py-4 bg-apple-bg/35 space-y-3 animate-slide-up">
                <h4 className="text-xs font-semibold text-apple-text flex items-center gap-2">
                  <span className="text-apple-accent"><Icons.Doc /></span>
                  Session #{expandedSession} 变更记录
                </h4>
                <div className="space-y-2">
                  {changes[expandedSession].map(c => {
                    let sourceIds: number[] = [];
                    try { sourceIds = JSON.parse(c.source_ids); } catch { /* keep empty */ }
                    const typeCls = changeTypeStyle[c.change_type] || changeTypeStyle.archive;
                    return (
                      <div key={c.id}
                           className="flex items-start gap-3 text-xs bg-white rounded-lg border border-black/5 px-3.5 py-2.5 hover:shadow-sm transition-shadow">
                        <span className={`px-2 py-0.5 rounded-md border text-[11px] font-medium shrink-0 mt-px ${typeCls}`}>
                          {c.change_type}
                        </span>
                        <div className="flex-1 min-w-0">
                          {c.diff_summary && <p className="text-apple-text-secondary leading-relaxed">{c.diff_summary}</p>}
                          {sourceIds.length > 0 && (
                            <p className="text-apple-text-tertiary/80 text-[11px] mt-1 font-mono">
                              #{sourceIds.join(', #')}{c.target_id ? ` → #${c.target_id}` : ''}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
