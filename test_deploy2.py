import requests, json, sys

sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://localhost:8000'
s = requests.Session()

print('='*50)
print('MemoMind 3.0.0 部署测试')
print('='*50)

# 1. 登录获取 Token
print('\n[1] 用户 GL-MMM 登录')
r = s.post(f'{BASE}/api/auth/login', json={'username': 'GL-MMM'})
print(f'    状态: {r.status_code}')
token_data = r.json()
token = token_data['access_token']
s.headers.update({'Authorization': f'Bearer {token}'})

# 2. 获取当前用户信息
print('\n[2] 当前用户信息')
r = s.get(f'{BASE}/api/auth/me')
print(f'    状态: {r.status_code} -> {json.dumps(r.json(), ensure_ascii=False)}')

# 3. 获取工作空间列表
print('\n[3] 工作空间列表')
r = s.get(f'{BASE}/api/workspaces')
print(f'    状态: {r.status_code}')
workspaces = r.json()
for ws in workspaces:
    print(f'    - ID:{ws["id"]} 名称:{ws["name"]} 描述:{ws.get("description","")}')
ws_id = workspaces[0]['id'] if workspaces else None

if not ws_id:
    print('    创建工作空间...')
    r = s.post(f'{BASE}/api/workspaces', json={'name': 'GL测试空间', 'description': '功能测试'})
    ws = r.json()
    ws_id = ws['id']
    print(f'    已创建: ID={ws_id}')

# 4. 创建笔记
print('\n[4] 创建测试笔记')
note1 = {
    'title': 'MemoMind 功能测试',
    'content': '这是测试笔记，用于验证搜索、标签、知识图谱等功能。\n\n## 功能清单\n- 笔记 CRUD\n- 标签系统\n- 全文搜索\n- 知识图谱\n- 活动日志\n- 版本管理',
    'tags': ['测试', '功能'],
    'workspace_id': ws_id
}
r = s.post(f'{BASE}/api/notes', json=note1)
print(f'    状态: {r.status_code} -> {json.dumps(r.json(), ensure_ascii=False)[:100]}')
note1_id = r.json().get('id')

note2 = {
    'title': '部署环境记录',
    'content': 'MemoMind 3.0.0 部署信息\n\n- Python: 3.14.3\n- Node.js: v24.14.0\n- OS: Windows 11\n- REST API: 端口 8000\n- MCP Server: 端口 8001\n- Web: 端口 3000',
    'tags': ['部署', '环境'],
    'workspace_id': ws_id
}
r = s.post(f'{BASE}/api/notes', json=note2)
print(f'    状态: {r.status_code} -> {json.dumps(r.json(), ensure_ascii=False)[:100]}')
note2_id = r.json().get('id')

# 5. 搜索笔记
print('\n[5] 全文搜索（关键词：测试）')
r = s.get(f'{BASE}/api/notes/search', params={'q': '测试'})
print(f'    状态: {r.status_code}')
results = r.json()
if isinstance(results, dict):
    count = results.get('count', len(results))
    items = results.get('results', results.get('notes', []))
    print(f'    找到 {count} 条结果')
    for item in items[:3]:
        if isinstance(item, dict):
            print(f'    - {item.get("title", item)}')
        else:
            print(f'    - {item}')
else:
    print(f'    找到 {len(results)} 条结果')
    for item in results[:3]:
        print(f'    - {item}')

# 6. 标签列表
print('\n[6] 标签列表')
r = s.get(f'{BASE}/api/tags')
print(f'    状态: {r.status_code}')
tags = r.json()
if isinstance(tags, list):
    print(f'    标签: {[t.get("name", str(t)) for t in tags]}')
else:
    print(f'    标签: {tags}')

# 7. 链接图谱
print('\n[7] 链接图谱')
r = s.get(f'{BASE}/api/links/graph')
print(f'    状态: {r.status_code}')
graph = r.json()
if isinstance(graph, dict):
    print(f'    节点: {len(graph.get("nodes", []))}, 边: {len(graph.get("edges", []))}')
else:
    print(f'    数据: {str(graph)[:200]}')

# 8. 获取笔记详情
print(f'\n[8] 笔记详情 (ID: {note1_id})')
r = s.get(f'{BASE}/api/notes/{note1_id}')
print(f'    状态: {r.status_code}')
note = r.json()
print(f'    标题: {note.get("title")}')
print(f'    标签: {note.get("tags", [])}')
print(f'    内容预览: {note.get("content", "")[:80]}...')

# 9. 活动日志
print('\n[9] 活动日志')
r = s.get(f'{BASE}/api/activity')
print(f'    状态: {r.status_code}')
activities = r.json()
print(f'    共 {len(activities)} 条活动')
for a in activities[:5]:
    action = a.get('action', a.get('type', 'unknown'))
    ts = a.get('created_at', a.get('timestamp', ''))
    print(f'    - [{ts}] {action}')

# 10. 更新笔记（测试编辑）
print(f'\n[10] 更新笔记 (ID: {note1_id})')
r = s.put(f'{BASE}/api/notes/{note1_id}', json={'title': 'MemoMind 功能测试（已更新）'})
print(f'    状态: {r.status_code} -> {json.dumps(r.json(), ensure_ascii=False)[:100]}')

# 11. 验证更新
print(f'\n[11] 验证更新')
r = s.get(f'{BASE}/api/notes/{note1_id}')
note = r.json()
print(f'    新标题: {note.get("title")}')

# 12. 删除笔记
print(f'\n[12] 删除笔记 (ID: {note1_id})')
r = s.delete(f'{BASE}/api/notes/{note1_id}')
print(f'    状态: {r.status_code}')

# 13. 验证删除
print(f'\n[13] 验证删除')
r = s.get(f'{BASE}/api/notes/{note1_id}')
print(f'    状态: {r.status_code} (应为 404)')

print('\n' + '='*50)
print('DEPLOYMENT TEST COMPLETE')
print('='*50)
