"""
MemoMind 知识图谱服务
可视化笔记关系网络，支持社区检测
"""

import json
from typing import List, Optional, Dict, Set, Tuple
from collections import defaultdict, Counter
from .database import Database
from .tokenizer import get_tokenizer


class KnowledgeGraphService:
    """知识图谱服务"""
    
    def __init__(self, db: Database):
        self.db = db
        self.tokenizer = get_tokenizer()
    
    def build_graph(
        self,
        workspace_id: Optional[int] = None,
        max_nodes: int = 100
    ) -> Dict:
        """
        构建知识图谱
        
        Args:
            workspace_id: 工作区过滤
            max_nodes: 最大节点数
            
        Returns:
            图谱数据 {'nodes': [...], 'edges': [...]}
        """
        # 获取笔记
        try:
            if workspace_id:
                cursor = self.db.execute(
                    "SELECT id, title, content, tags FROM notes WHERE workspace_id = ? LIMIT ?",
                    (workspace_id, max_nodes))
            else:
                cursor = self.db.execute(
                    "SELECT id, title, content, tags FROM notes LIMIT ?",
                    (max_nodes,))
        except Exception:
            pass  # workspace_id 列不存在
        
        notes = []
        if 'cursor' not in locals():
            cursor = self.db.execute("SELECT id, title, content, tags FROM notes LIMIT ?", (max_nodes,))
        for row in cursor.fetchall():
            notes.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'tags': json.loads(row[3]) if row[3] else []
            })
        
        # 构建节点
        nodes = self._build_nodes(notes)
        
        # 构建边（基于链接、标签、相似度）
        edges = []
        edges.extend(self._build_link_edges(notes))
        edges.extend(self._build_tag_edges(notes))
        edges.extend(self._build_similarity_edges(notes))
        
        # 去重边
        edges = self._deduplicate_edges(edges)
        
        return {'nodes': nodes, 'edges': edges}
    
    def _build_nodes(self, notes: List[Dict]) -> List[Dict]:
        """构建节点"""
        nodes = []
        for note in notes:
            # 计算节点重要度（基于标签数量和标题长度）
            importance = len(note['tags']) * 0.5 + min(len(note['title']) / 20, 1.0)
            
            nodes.append({
                'id': note['id'],
                'label': note['title'],
                'tags': note['tags'],
                'importance': importance,
                'group': self._assign_group(note['tags'])
            })
        return nodes
    
    def _assign_group(self, tags: List[str]) -> str:
        """为节点分配分组"""
        if not tags:
            return 'other'
        
        # 使用第一个标签作为分组
        category_map = {
            'Python': '编程', 'JavaScript': '编程', '编程': '编程',
            '机器学习': 'AI', '深度学习': 'AI', 'AI': 'AI', 'NLP': 'AI',
            '数据库': '数据', 'SQL': '数据', '数据分析': '数据',
            'Web': '开发', '前端': '开发', '后端': '开发', '开发': '开发',
        }
        
        for tag in tags:
            if tag in category_map:
                return category_map[tag]
        return 'other'
    
    def _build_link_edges(self, notes: List[Dict]) -> List[Dict]:
        """基于笔记链接构建边"""
        edges = []
        try:
            cursor = self.db.execute("""
                SELECT source_note_id, target_note_id FROM note_links
            """)
            for row in cursor.fetchall():
                edges.append({
                    'source': row[0],
                    'target': row[1],
                    'type': 'link',
                    'weight': 1.0
                })
        except Exception:
            pass  # note_links table may not exist
        return edges
    
    def _build_tag_edges(self, notes: List[Dict]) -> List[Dict]:
        """基于共享标签构建边"""
        # 构建标签到笔记的映射
        tag_to_notes = defaultdict(list)
        for note in notes:
            for tag in note['tags']:
                tag_to_notes[tag].append(note['id'])
        
        edges = []
        for tag, note_ids in tag_to_notes.items():
            # 每对共享标签的笔记之间添加边
            for i in range(len(note_ids)):
                for j in range(i + 1, len(note_ids)):
                    edges.append({
                        'source': note_ids[i],
                        'target': note_ids[j],
                        'type': 'tag',
                        'weight': 0.5,
                        'tag': tag
                    })
        return edges
    
    def _build_similarity_edges(self, notes: List[Dict]) -> List[Dict]:
        """基于内容相似度构建边"""
        edges = []
        
        # 计算笔记间的词重叠
        note_terms = {}
        for note in notes:
            terms = set(self.tokenizer.tokenize(f"{note['title']} {note['content'][:200]}"))
            stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都'}
            note_terms[note['id']] = terms - stop_words
        
        note_ids = list(note_terms.keys())
        for i in range(len(note_ids)):
            for j in range(i + 1, len(note_ids)):
                id1, id2 = note_ids[i], note_ids[j]
                terms1, terms2 = note_terms[id1], note_terms[id2]
                
                if not terms1 or not terms2:
                    continue
                
                # Jaccard 相似度
                intersection = len(terms1 & terms2)
                union = len(terms1 | terms2)
                similarity = intersection / union if union > 0 else 0
                
                if similarity > 0.1:  # 阈值
                    edges.append({
                        'source': id1,
                        'target': id2,
                        'type': 'similarity',
                        'weight': similarity
                    })
        
        return edges
    
    def _deduplicate_edges(self, edges: List[Dict]) -> List[Dict]:
        """去重边（保留权重最高的）"""
        edge_map = {}
        for edge in edges:
            key = (min(edge['source'], edge['target']), max(edge['source'], edge['target']))
            if key not in edge_map or edge['weight'] > edge_map[key]['weight']:
                edge_map[key] = edge
        return list(edge_map.values())
    
    def detect_communities(self, graph: Dict) -> Dict[int, str]:
        """
        简单的社区检测（基于标签聚类）
        
        Args:
            graph: 图谱数据
            
        Returns:
            {node_id: community_name}
        """
        communities = {}
        
        # 基于标签分组
        tag_groups = defaultdict(list)
        for node in graph['nodes']:
            for tag in node.get('tags', []):
                tag_groups[tag].append(node['id'])
        
        # 分配社区
        for tag, node_ids in tag_groups.items():
            for node_id in node_ids:
                if node_id not in communities:
                    communities[node_id] = tag
        
        # 没有标签的节点分配到 'other'
        for node in graph['nodes']:
            if node['id'] not in communities:
                communities[node['id']] = 'other'
        
        return communities
    
    def export_graphml(self, graph: Dict) -> str:
        """
        导出为 GraphML 格式（可用于 Gephi 等工具）
        
        Args:
            graph: 图谱数据
            
        Returns:
            GraphML XML 字符串
        """
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
        lines.append('<graph edgedefault="undirected">')
        
        # 节点
        for node in graph['nodes']:
            lines.append(f'  <node id="{node["id"]}">')
            lines.append(f'    <data key="label">{self._escape_xml(node["label"])}</data>')
            lines.append(f'    <data key="group">{node.get("group", "other")}</data>')
            lines.append(f'    <data key="importance">{node.get("importance", 0):.2f}</data>')
            lines.append('  </node>')
        
        # 边
        for edge in graph['edges']:
            lines.append(f'  <edge source="{edge["source"]}" target="{edge["target"]}">')
            lines.append(f'    <data key="type">{edge["type"]}</data>')
            lines.append(f'    <data key="weight">{edge["weight"]:.4f}</data>')
            lines.append('  </edge>')
        
        lines.append('</graph>')
        lines.append('</graphml>')
        
        return '\n'.join(lines)
    
    def _escape_xml(self, text: str) -> str:
        """转义 XML 特殊字符"""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    
    def get_graph_stats(self, graph: Dict) -> Dict:
        """获取图谱统计信息"""
        node_count = len(graph['nodes'])
        edge_count = len(graph['edges'])
        
        # 边类型分布
        edge_types = Counter(e['type'] for e in graph['edges'])
        
        # 节点分组分布
        group_counts = Counter(n.get('group', 'other') for n in graph['nodes'])
        
        # 平均度
        degree_count = defaultdict(int)
        for edge in graph['edges']:
            degree_count[edge['source']] += 1
            degree_count[edge['target']] += 1
        
        avg_degree = sum(degree_count.values()) / max(node_count, 1)
        
        return {
            'node_count': node_count,
            'edge_count': edge_count,
            'edge_types': dict(edge_types),
            'group_counts': dict(group_counts),
            'avg_degree': avg_degree,
            'density': 2 * edge_count / max(node_count * (node_count - 1), 1)
        }
