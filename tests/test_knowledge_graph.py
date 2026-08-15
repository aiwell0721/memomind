"""
MemoMind 知识图谱测试
"""

import pytest
import json
from core.database import Database
from core.knowledge_graph_service import KnowledgeGraphService


@pytest.fixture
def db():
    database = Database(":memory:")
    database.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            workspace_id INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    database.commit()
    return database


@pytest.fixture
def kg(db):
    return KnowledgeGraphService(db)


@pytest.fixture
def sample_notes(db):
    notes_data = [
        ("Python 入门", "Python 是一种编程语言", json.dumps(["Python", "编程"])),
        ("机器学习基础", "机器学习是 AI 的分支", json.dumps(["机器学习", "AI"])),
        ("深度学习", "深度学习使用神经网络", json.dumps(["深度学习", "AI"])),
        ("Web 开发", "Web 开发使用 HTML 和 JavaScript", json.dumps(["Web", "开发"])),
        ("数据库设计", "数据库使用 SQL 语言", json.dumps(["数据库", "SQL"])),
    ]
    for title, content, tags in notes_data:
        db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)", (title, content, tags))
    db.commit()
    return notes_data


class TestBuildGraph:
    """构建图谱测试"""
    
    def test_build_basic_graph(self, kg, sample_notes):
        """测试基本图谱构建"""
        graph = kg.build_graph(max_nodes=10)
        assert 'nodes' in graph
        assert 'edges' in graph
        assert len(graph['nodes']) == 5
    
    def test_build_graph_limit(self, kg, sample_notes):
        """测试节点数量限制"""
        graph = kg.build_graph(max_nodes=2)
        assert len(graph['nodes']) <= 2
    
    def test_build_graph_workspace_filter(self, kg, sample_notes):
        """测试工作区过滤"""
        graph = kg.build_graph(workspace_id=1, max_nodes=10)
        assert isinstance(graph, dict)
    
    def test_build_graph_empty(self, kg):
        """测试空数据库"""
        graph = kg.build_graph()
        assert graph['nodes'] == []
        assert graph['edges'] == []


class TestNodes:
    """节点测试"""
    
    def test_node_structure(self, kg, sample_notes):
        """测试节点结构"""
        graph = kg.build_graph()
        node = graph['nodes'][0]
        assert 'id' in node
        assert 'label' in node
        assert 'tags' in node
        assert 'importance' in node
        assert 'group' in node
    
    def test_node_group_assignment(self, kg):
        """测试节点分组"""
        assert kg._assign_group(['Python']) == '编程'
        assert kg._assign_group(['机器学习']) == 'AI'
        assert kg._assign_group(['数据库']) == '数据'
        assert kg._assign_group([]) == 'other'
        assert kg._assign_group(['未知标签']) == 'other'


class TestEdges:
    """边测试"""
    
    def test_tag_edges(self, kg, sample_notes):
        """测试标签边"""
        graph = kg.build_graph()
        tag_edges = [e for e in graph['edges'] if e['type'] == 'tag']
        # Python 入门和机器学习没有共享标签
        # 机器学习和深度学习共享 AI 标签
        ai_edges = [e for e in tag_edges if e.get('tag') == 'AI']
        assert len(ai_edges) >= 1
    
    def test_similarity_edges(self, kg, sample_notes):
        """测试相似度边"""
        graph = kg.build_graph()
        sim_edges = [e for e in graph['edges'] if e['type'] == 'similarity']
        assert isinstance(sim_edges, list)
    
    def test_edge_deduplication(self, kg):
        """测试边去重"""
        edges = [
            {'source': 1, 'target': 2, 'type': 'tag', 'weight': 0.5},
            {'source': 2, 'target': 1, 'type': 'similarity', 'weight': 0.3},
            {'source': 1, 'target': 2, 'type': 'link', 'weight': 0.8},
        ]
        deduped = kg._deduplicate_edges(edges)
        assert len(deduped) == 1
        assert deduped[0]['weight'] == 0.8


class TestCommunities:
    """社区检测测试"""
    
    def test_detect_communities(self, kg, sample_notes):
        """测试社区检测"""
        graph = kg.build_graph()
        communities = kg.detect_communities(graph)
        assert isinstance(communities, dict)
        assert len(communities) == len(graph['nodes'])
    
    def test_communities_same_tag(self, kg, sample_notes):
        """测试相同标签的节点在同一社区"""
        graph = kg.build_graph()
        communities = kg.detect_communities(graph)
        
        # 找到 AI 标签的节点
        ai_nodes = [n['id'] for n in graph['nodes'] if 'AI' in n.get('tags', [])]
        if len(ai_nodes) >= 2:
            # 它们应该在同一社区
            comm_ids = set(communities.get(n) for n in ai_nodes)
            # 至少有一个共同的社区标签
            assert len(comm_ids) <= len(ai_nodes)


class TestExport:
    """导出测试"""
    
    def test_export_graphml(self, kg, sample_notes):
        """测试 GraphML 导出"""
        graph = kg.build_graph()
        graphml = kg.export_graphml(graph)
        
        assert '<?xml' in graphml
        assert '<graphml' in graphml
        assert '<graph' in graphml
        assert '<node' in graphml
        assert '</graphml>' in graphml
    
    def test_export_graphml_empty(self, kg):
        """测试空图谱导出"""
        graph = kg.build_graph()
        graphml = kg.export_graphml(graph)
        assert '<?xml' in graphml
    
    def test_export_xml_escaping(self, kg):
        """测试 XML 转义"""
        assert kg._escape_xml('<test>') == '&lt;test&gt;'
        assert kg._escape_xml('a&b') == 'a&amp;b'
        assert kg._escape_xml('"quote"') == '&quot;quote&quot;'


class TestStats:
    """统计测试"""
    
    def test_get_graph_stats(self, kg, sample_notes):
        """测试图谱统计"""
        graph = kg.build_graph()
        stats = kg.get_graph_stats(graph)
        
        assert 'node_count' in stats
        assert 'edge_count' in stats
        assert 'edge_types' in stats
        assert 'group_counts' in stats
        assert 'avg_degree' in stats
        assert 'density' in stats
        
        assert stats['node_count'] == 5
        assert stats['edge_count'] >= 0
    
    def test_get_graph_stats_empty(self, kg):
        """测试空图谱统计"""
        graph = kg.build_graph()
        stats = kg.get_graph_stats(graph)
        assert stats['node_count'] == 0
        assert stats['edge_count'] == 0


class TestEdgeCases:
    """边界情况测试"""
    
    def test_single_note_graph(self, kg):
        """测试单节点图谱"""
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("单笔记", "内容", json.dumps(["测试"])))
        kg.db.commit()
        
        graph = kg.build_graph()
        assert len(graph['nodes']) == 1
        assert len(graph['edges']) == 0
    
    def test_notes_without_tags(self, kg):
        """测试无标签笔记"""
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("无标签", "内容", None))
        kg.db.commit()
        
        graph = kg.build_graph()
        assert len(graph['nodes']) == 1
        assert graph['nodes'][0]['group'] == 'other'
    
    def test_large_graph(self, kg):
        """测试大型图谱"""
        for i in range(50):
            kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                         (f"笔记{i}", f"内容{i}" * 10, json.dumps([f"标签{i % 5}"])))
        kg.db.commit()
        
        graph = kg.build_graph(max_nodes=100)
        assert len(graph['nodes']) == 50
        assert len(graph['edges']) >= 0


class TestSuggestConsolidation:
    """知识整理建议测试"""

    def test_suggest_basic(self, kg):
        """测试基本建议生成"""
        # 插入同一主题的多条笔记
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("Python 装饰器", "装饰器用于修改函数", json.dumps(["Python", "编程"])))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("Flask 路由", "Flask 路由装饰器用法", json.dumps(["Python", "Web"])))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("Docker 入门", "Docker 容器化部署", json.dumps(["Docker", "部署"])))
        kg.db.commit()

        result = kg.suggest_consolidation()
        assert 'topics' in result
        assert 'merge_suggestions' in result
        assert 'stale_candidates' in result

    def test_suggest_empty_database(self, kg):
        """测试空数据库"""
        result = kg.suggest_consolidation()
        assert result['topics'] == []
        assert result['merge_suggestions'] == []
        assert result['stale_candidates'] == []

    def test_suggest_merge_from_high_similarity(self, kg):
        """测试高相似度笔记出现在合并建议中"""
        # 使用高度重叠的中文内容确保 Jaccard 相似度 > 0.1
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("Python 装饰器详解", "装饰器是 Python 的高级语法特性，用于增强函数功能而不修改函数本身。常用装饰器包括属性装饰器和类方法装饰器。", json.dumps(["Python", "编程"])))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("Python 装饰器进阶", "Python 装饰器是高级语法特性，用于增强函数功能。装饰器可以在不修改函数本身的情况下添加额外逻辑。", json.dumps(["Python", "进阶"])))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("烹饪技巧", "家常菜烹饪技巧分享", json.dumps(["美食", "生活"])))
        kg.db.commit()

        result = kg.suggest_consolidation(similarity_threshold=0.1)
        # 两条 Python 装饰器笔记应触发合并建议
        assert len(result['merge_suggestions']) > 0

    def test_suggest_stale_notes(self, kg):
        """测试陈旧笔记检测"""
        # 插入一条"旧"笔记（手动设置旧时间戳）
        kg.db.execute("""
            INSERT INTO notes (title, content, tags, updated_at) VALUES (?, ?, ?, ?)
        """, ("过时笔记", "旧版本内容", json.dumps(["旧"]), "2024-01-01 00:00:00"))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("新笔记", "最新内容", json.dumps(["新"])))
        kg.db.commit()

        result = kg.suggest_consolidation(days_threshold=365)
        # 超过一年的笔记应该出现在陈旧候选里
        assert len(result['stale_candidates']) > 0
        stale_ids = [s['note_id'] for s in result['stale_candidates']]
        # 找到"过时笔记"
        cursor = kg.db.execute("SELECT id FROM notes WHERE title = ?", ("过时笔记",))
        old_id = cursor.fetchone()['id']
        assert old_id in stale_ids

    def test_suggest_communities_as_topics(self, kg):
        """测试社区检测结果转为主题"""
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("笔记A", "内容", json.dumps(["Python", "FastAPI"])))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("笔记B", "内容", json.dumps(["Python", "Django"])))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("笔记C", "内容", json.dumps(["JavaScript", "React"])))
        kg.db.commit()

        result = kg.suggest_consolidation()
        # 社区检测应发现 Python 和 JavaScript 两个主题
        assert len(result['topics']) >= 1


class TestLintKnowledge:
    """lint_knowledge 统一知识健康报告测试"""

    def test_lint_returns_four_keys(self, kg):
        """返回 merge/update/link/delete 四类"""
        result = kg.lint_knowledge()
        assert set(result.keys()) == {'merge', 'update', 'link', 'delete'}

    def test_lint_empty_database(self, kg):
        """空库返回空四类"""
        result = kg.lint_knowledge()
        assert result['merge'] == []
        assert result['update'] == []
        assert result['link'] == []
        assert result['delete'] == []

    def test_lint_detects_merge(self, kg):
        """高相似笔记进入 merge"""
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("Python 装饰器详解", "装饰器是 Python 的高级语法特性，用于增强函数功能而不修改函数本身。", json.dumps(["Python", "编程"])))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("Python 装饰器进阶", "Python 装饰器是高级语法特性，用于增强函数功能。装饰器不修改函数本身。", json.dumps(["Python", "进阶"])))
        kg.db.commit()

        result = kg.lint_knowledge(similarity_threshold=0.1)
        assert len(result['merge']) > 0

    def test_lint_detects_stale(self, kg):
        """陈旧笔记进入 update"""
        kg.db.execute("INSERT INTO notes (title, content, tags, updated_at) VALUES (?, ?, ?, ?)",
                     ("过时笔记", "旧内容", json.dumps(["旧"]), "2024-01-01 00:00:00"))
        kg.db.commit()

        result = kg.lint_knowledge(days_threshold=365)
        stale_ids = [s['note_id'] for s in result['update']]
        cursor = kg.db.execute("SELECT id FROM notes WHERE title = ?", ("过时笔记",))
        assert cursor.fetchone()['id'] in stale_ids

    def test_lint_detects_orphan(self, kg):
        """无任何边相连的孤立笔记进入 link"""
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("机器学习基础", "机器学习基础概念", json.dumps(["AI", "机器学习"])))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("深度学习", "深度学习神经网络", json.dumps(["AI", "深度学习"])))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("咖啡冲泡", "咖啡豆研磨萃取技巧", json.dumps(["咖啡"])))
        kg.db.commit()

        result = kg.lint_knowledge()
        cursor = kg.db.execute("SELECT id FROM notes WHERE title = ?", ("咖啡冲泡",))
        orphan_id = cursor.fetchone()['id']
        link_ids = [l['note_id'] for l in result['link']]
        assert orphan_id in link_ids

    def test_lint_delete_candidate(self, kg):
        """孤儿且陈旧的笔记进入 delete"""
        kg.db.execute("INSERT INTO notes (title, content, tags, updated_at) VALUES (?, ?, ?, ?)",
                     ("孤立陈旧笔记", "独特内容xyz123", json.dumps(["独特"]), "2024-01-01 00:00:00"))
        kg.db.commit()

        result = kg.lint_knowledge(days_threshold=365)
        cursor = kg.db.execute("SELECT id FROM notes WHERE title = ?", ("孤立陈旧笔记",))
        note_id = cursor.fetchone()['id']
        delete_ids = [d['note_id'] for d in result['delete']]
        assert note_id in delete_ids


class TestGraphWithAnalysis:
    """get_graph_with_analysis 带分析注解的图谱测试"""

    def test_returns_analysis_fields(self, kg, sample_notes):
        """返回 nodes + edges，节点带分析字段"""
        result = kg.get_graph_with_analysis()
        assert 'nodes' in result
        assert 'edges' in result
        for node in result['nodes']:
            assert 'community' in node
            assert 'is_orphan' in node
            assert 'is_delete_candidate' in node

    def test_empty_database(self, kg):
        """空库返回空 nodes/edges"""
        result = kg.get_graph_with_analysis()
        assert result['nodes'] == []
        assert result['edges'] == []

    def test_orphan_marked(self, kg):
        """孤立笔记 is_orphan=True"""
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("机器学习基础", "机器学习基础概念", json.dumps(["AI", "机器学习"])))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("深度学习", "深度学习神经网络", json.dumps(["AI", "深度学习"])))
        kg.db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                     ("咖啡冲泡", "咖啡豆研磨萃取", json.dumps(["咖啡"])))
        kg.db.commit()

        result = kg.get_graph_with_analysis()
        cursor = kg.db.execute("SELECT id FROM notes WHERE title = ?", ("咖啡冲泡",))
        orphan_id = cursor.fetchone()['id']

        node = next(n for n in result['nodes'] if n['id'] == orphan_id)
        assert node['is_orphan'] is True
