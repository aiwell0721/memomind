import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { DreamingReport, DreamingSession, DreamingChange } from '../lib/api';

function formatTime(dateStr: string | null): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function statusBadge(status: string) {
  const map: Record<string, { label: string; cls: string }> = {
    running: { label: '运行中', cls: 'bg-amber-100 text-amber-700' },
    completed: { label: '已完成', cls: 'bg-emerald-100 text-emerald-700' },
    failed: { label: '失败', cls: 'bg-rose-100 text-rose-700' },
    rolled_back: { label: '已回滚', cls: 'bg-slate-100 text-slate-500' },
  };
  const s = map[status] || { label: status, cls: 'bg-slate-100 text-slate-500' };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.cls}`}>{s.label}</span>;
}

export default function Dreaming() {
  const [sessions, setSessions] = useState<DreamingSession[]>([]);
  const [changes, setChanges] = useState<Record<number, DreamingChange[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<DreamingReport | null>(null);
  const [strategy, setStrategy] = useState('default');
  const [dryRun, setDryRun] = useState(true);
  const [expandedSession, setExpandedSession] = useState<number | null>(null);
  const [rollbackMsg, setRollbackMsg] = useState('');

  const loadHistory = () => {
    api.dreaming.history(20).then(setSessions).catch(() => {});
  };

  useEffect(() => { loadHistory(); }, []);

  async function handleRun() {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const r = await api.dreaming.run({ strategy, dry_run: dryRun });
      setResult(r);
      if (!dryRun) loadHistory();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '执行失败');
    } finally {
      setLoading(false);
    }
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
    if (expandedSession === sessionId) {
      setExpandedSession(null);
      return;
    }
    if (!changes[sessionId]) {
      try {
        const c = await api.dreaming.changes(sessionId);
        setChanges(prev => ({ ...prev, [sessionId]: c }));
      } catch { return; }
    }
    setExpandedSession(sessionId);
  }

  const compressionPct = (s: DreamingSession) => {
    if (s.input_count === 0) return 0;
    return ((1 - s.output_count / s.input_count) * 100).toFixed(1);
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <h2 className="text-xl font-semibold text-apple-text mb-1">记忆整理</h2>
      <p className="text-sm text-apple-text-tertiary mb-6">
        基于 Embedding 聚类的离线记忆压缩。将相似主题笔记合并，减少信息冗余。
      </p>

      {/* ── 操作区 ── */}
      <div className="bg-white rounded-xl border border-apple-border p-5 mb-6 space-y-4">
        {/* 策略选择 */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-apple-text-secondary w-20">策略</span>
          {(['default', 'aggressive', 'conservative'] as const).map(s => (
            <button
              key={s}
              onClick={() => setStrategy(s)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                strategy === s
                  ? 'bg-apple-accent text-white border-apple-accent'
                  : 'bg-apple-bg text-apple-text-secondary border-apple-border hover:border-apple-accent'
              }`}
            >
              {{ default: '默认', aggressive: '激进', conservative: '保守' }[s]}
            </button>
          ))}
        </div>
        <p className="text-xs text-apple-text-tertiary ml-[5rem] -mt-2">
          默认阈值 0.70（压缩 46%）| 激进 0.65（压缩 60%）| 保守 0.75（压缩 28%）
        </p>

        {/* 预览 / 执行 */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-apple-text-secondary w-20">模式</span>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)}
                   className="w-4 h-4 rounded border-apple-border text-apple-accent" />
            预览模式（不写入数据库）
          </label>
          <button
            onClick={handleRun}
            disabled={loading}
            className="ml-auto px-5 py-2 bg-apple-accent text-white rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {loading ? '执行中...' : dryRun ? '预览' : '执行 Dreaming'}
          </button>
        </div>

        {error && <p className="text-sm text-rose-600 bg-rose-50 rounded-lg px-3 py-2">{error}</p>}
        {rollbackMsg && <p className={`text-sm rounded-lg px-3 py-2 ${rollbackMsg.includes('失败') ? 'text-rose-600 bg-rose-50' : 'text-emerald-600 bg-emerald-50'}`}>{rollbackMsg}</p>}

        {/* ── 结果报告 ── */}
        {result && (
          <div className="border border-apple-border rounded-lg p-4 bg-apple-bg space-y-2">
            <h4 className="text-sm font-semibold text-apple-text">
              {result.dry_run ? '预览报告' : `Dreaming #${result.session_id} 完成`}
            </h4>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div><span className="text-apple-text-tertiary">输入</span> <span className="font-medium">{result.input_count} 条</span></div>
              <div><span className="text-apple-text-tertiary">输出</span> <span className="font-medium">{result.output_count} 条</span></div>
              <div><span className="text-apple-text-tertiary">压缩率</span> <span className="font-medium">
                {result.input_count > 0
                  ? ((1 - result.output_count / result.input_count) * 100).toFixed(1) + '%'
                  : '—'}
              </span></div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-apple-text-tertiary">合并</span> <span className="font-medium">{result.merged_count} 条</span></div>
              <div><span className="text-apple-text-tertiary">归档</span> <span className="font-medium">{result.archived_count} 条</span></div>
            </div>
            {result.clusters.length > 0 && (
              <details className="text-xs text-apple-text-tertiary">
                <summary className="cursor-pointer">簇详情（{result.clusters.length} 个多元素簇）</summary>
                <ul className="mt-1 space-y-0.5 pl-4">
                  {result.clusters.map((c, i) => (
                    <li key={i}>簇 {i + 1}：notes #{c.join(', #')}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </div>

      {/* ── 历史记录 ── */}
      <h3 className="text-lg font-semibold text-apple-text mb-3">历史记录</h3>
      {sessions.length === 0 ? (
        <p className="text-sm text-apple-text-tertiary">暂无 Dreaming 记录</p>
      ) : (
        <div className="bg-white rounded-xl border border-apple-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-apple-border bg-apple-bg text-apple-text-tertiary text-xs">
                <th className="text-left px-4 py-2.5 font-medium">#</th>
                <th className="text-left px-4 py-2.5 font-medium">时间</th>
                <th className="text-left px-4 py-2.5 font-medium">策略</th>
                <th className="text-left px-4 py-2.5 font-medium">状态</th>
                <th className="text-right px-4 py-2.5 font-medium">输入</th>
                <th className="text-right px-4 py-2.5 font-medium">输出</th>
                <th className="text-right px-4 py-2.5 font-medium">压缩率</th>
                <th className="text-center px-4 py-2.5 font-medium">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-apple-border">
              {sessions.map(s => {
                const isExpanded = expandedSession === s.id;
                const canRollback = s.status === 'completed';
                return (
                  <tr key={s.id} className="hover:bg-apple-bg/50 transition-colors">
                    <td className="px-4 py-2.5 text-apple-text-tertiary">{s.id}</td>
                    <td className="px-4 py-2.5">{formatTime(s.started_at)}</td>
                    <td className="px-4 py-2.5 capitalize">{s.trigger}</td>
                    <td className="px-4 py-2.5">{statusBadge(s.status)}</td>
                    <td className="px-4 py-2.5 text-right">{s.input_count}</td>
                    <td className="px-4 py-2.5 text-right">{s.output_count}</td>
                    <td className="px-4 py-2.5 text-right font-medium">{compressionPct(s)}%</td>
                    <td className="px-4 py-2.5 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => toggleChanges(s.id)}
                          className="text-xs text-apple-accent hover:underline"
                        >
                          {isExpanded ? '收起' : '详情'}
                        </button>
                        {canRollback && (
                          <button
                            onClick={() => handleRollback(s.id)}
                            className="text-xs text-rose-500 hover:underline"
                          >
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
          {/* ── 展开详情 ── */}
          {expandedSession !== null && changes[expandedSession] && (
            <div className="border-t border-apple-border px-4 py-3 bg-apple-bg">
              <h4 className="text-xs font-semibold text-apple-text mb-2">
                Session #{expandedSession} 变更记录
              </h4>
              <div className="space-y-1.5">
                {changes[expandedSession].map(c => {
                  let sourceIds: number[] = [];
                  try { sourceIds = JSON.parse(c.source_ids); } catch { /* keep empty */ }
                  return (
                    <div key={c.id} className="text-xs text-apple-text-secondary flex items-center gap-2">
                      <span className="px-1.5 py-0.5 rounded bg-apple-border/30 text-apple-text-tertiary">{c.change_type}</span>
                      {c.diff_summary && <span>{c.diff_summary}</span>}
                      {sourceIds.length > 0 && (
                        <span className="text-apple-text-tertiary">
                          (源: #{sourceIds.join(', #')}
                          {c.target_id ? ` → #${c.target_id})` : ')'}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
