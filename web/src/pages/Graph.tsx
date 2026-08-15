import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as echarts from 'echarts/core';
import { GraphChart } from 'echarts/charts';
import { TooltipComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { api } from '../lib/api';
import type { GraphData, GraphNode } from '../lib/api';

echarts.use([GraphChart, TooltipComponent, LegendComponent, CanvasRenderer]);

const communityColors = [
  '#0071e3', '#30b158', '#f09824', '#ee4b40',
  '#ac4ee0', '#00b8b0', '#ff9500', '#ff69b4',
];

export default function Graph() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState<{ nodes: number; edges: number } | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = echarts.init(containerRef.current);
    chartRef.current = chart;

    chart.on('click', (params: any) => {
      if (params.dataType === 'node' && params.data?.id != null) {
        navigate(`/notes/${params.data.id}`);
      }
    });

    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);

    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
      chartRef.current = null;
    };
  }, [navigate]);

  useEffect(() => {
    api.graph({ max_nodes: 100 })
      .then((data) => {
        setStats({ nodes: data.nodes.length, edges: data.edges.length });
        setLoading(false);
        chartRef.current?.setOption(buildOption(data));
      })
      .catch((e: Error) => {
        setLoading(false);
        setError(e.message || '加载失败');
      });
  }, []);

  return (
    <div style={{ padding: '1.5rem 2rem' }}>
      <div className="flex items-center justify-between" style={{ marginBottom: '0.75rem' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em' }}>知识图谱</h1>
          <p style={{ fontSize: 12, color: 'var(--apple-text-secondary)', marginTop: 2 }}>
            节点大小 = 重要度 · 颜色 = 社区 · 灰框 = 孤儿 · 红色 = 删除候选
          </p>
        </div>
        {stats && (
          <div style={{ fontSize: 12, color: 'var(--apple-text-secondary)' }}>
            {stats.nodes} 节点 · {stats.edges} 边
          </div>
        )}
      </div>

      {loading && (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--apple-text-secondary)' }}>
          加载图谱中...
        </div>
      )}
      {error && (
        <div style={{ padding: '1rem', color: 'var(--danger)' }}>
          加载失败：{error}
        </div>
      )}

      <div
        ref={containerRef}
        style={{
          width: '100%',
          height: 'calc(100vh - 160px)',
          border: '0.5px solid var(--apple-border)',
          borderRadius: 'var(--radius-md)',
          background: 'var(--apple-surface)',
        }}
      />
    </div>
  );
}

function buildOption(data: GraphData): Record<string, unknown> {
  const communitySet = new Set(data.nodes.map((n) => n.community));
  const colorMap: Record<string, string> = {};
  [...communitySet].forEach((c, i) => {
    colorMap[c] = communityColors[i % communityColors.length];
  });

  const nodes = data.nodes.map((n: GraphNode) => ({
    id: String(n.id),
    name: n.label,
    symbolSize: n.is_orphan ? 8 : Math.min(12 + n.importance * 12, 48),
    itemStyle: {
      color: n.is_delete_candidate ? '#ee4b40' : colorMap[n.community] || '#999',
      borderColor: n.is_orphan ? '#bbb' : 'transparent',
      borderWidth: n.is_orphan ? 1.5 : 0,
    },
    category: n.community,
  }));

  const edges = data.edges.map((e) => ({
    source: String(e.source),
    target: String(e.target),
    lineStyle: {
      color: e.type === 'similarity' ? '#0071e3' : e.type === 'tag' ? '#30b158' : '#bbb',
      opacity: 0.35,
      width: 1,
    },
  }));

  const categories = [...communitySet].map((c) => ({ name: c }));

  return {
    tooltip: {
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const node = data.nodes.find((n) => String(n.id) === params.data.id);
          if (!node) return params.name;
          const badges: string[] = [];
          if (node.is_orphan) badges.push('孤儿');
          if (node.is_delete_candidate) badges.push('删除候选');
          const tagText = node.tags.length ? node.tags.join('、') : '无';
          return `${node.label}<br/>标签：${tagText}${badges.length ? `<br/>⚠ ${badges.join(' · ')}` : ''}`;
        }
        return `${params.data?.source} → ${params.data?.target}`;
      },
    },
    legend: [{ data: categories.map((c) => c.name), bottom: 0, textStyle: { fontSize: 11 } }],
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: edges,
      categories,
      roam: true,
      draggable: true,
      label: {
        show: true,
        position: 'right',
        fontSize: 10,
        color: 'var(--apple-text-secondary)',
        formatter: (params: any) =>
          params.name.length > 12 ? `${params.name.slice(0, 12)}…` : params.name,
      },
      force: {
        repulsion: 220,
        edgeLength: 90,
      },
      emphasis: { focus: 'adjacency', label: { show: true, fontSize: 12 } },
    }],
  };
}
