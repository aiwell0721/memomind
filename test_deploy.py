import requests, json

BASE = 'http://localhost:8000'
s = requests.Session()

print('='*50)
print('1. 注册用户 GL-MMM')
r = s.post(f'{BASE}/api/users', json={'username': 'GL-MMM', 'display_name': 'GL-MMM'})
print(f'   状态: {r.status_code}')
if r.status_code == 409:
    print('   用户已存在，跳过')
    user_id = 1
else:
    user = r.json()
    print(f'   结果: {json.dumps(user, ensure_ascii=False)}')
    user_id = user.get('id')

print()
print('2. 登录获取 Token')
r = s.post(f'{BASE}/api/auth/login', json={'username': 'GL-MMM'})
print(f'   状态: {r.status_code}')
token_data = r.json()
token = token_data['access_token']
print(f'   Token: {token[:30]}...')

s.headers.update({'Authorization': f'Bearer {token}'})

print()
print('3. 当前用户信息')
r = s.get(f'{BASE}/api/auth/me')
print(f'   状态: {r.status_code}')
print(f'   结果: {json.dumps(r.json(), ensure_ascii=False)}')

print()
print('4. 创建工作空间')
r = s.post(f'{BASE}/api/workspaces', json={'name': 'GL测试空间', 'description': '功能测试'})
print(f'   状态: {r.status_code}')
if r.status_code != 201:
    print(f'   错误: {r.text}')
    # 尝试获取已有工作空间
    r = s.get(f'{BASE}/api/workspaces')
    workspaces = r.json()
    ws = workspaces[0] if workspaces else None
    if ws:
        ws_id = ws.get('id')
        print(f'   使用已有工作空间: {json.dumps(ws, ensure_ascii=False)}')
    else:
        print('   无工作空间，退出测试')
        exit(1)
else:
    ws = r.json()
    ws_id = ws.get('id')
    print(f'   结果: {json.dumps(ws, ensure_ascii=False)}')

print()
print('5. 创建笔记 #1')
note_data = {
    'title': 'MemoMind 测试笔记',
    'content': '这是第一条测试笔记，用于验证系统功能。\n\n## 功能列表\n- 笔记创建\n- 搜索\n- 标签\n- 知识图谱',
    'tags': ['测试', 'MemoMind'],
    'workspace_id': ws_id
}
r = s.post(f'{BASE}/api/notes', json=note_data)
print(f'   状态: {r.status_code}')
note = r.json()
note_id = note.get('id')
print(f'   结果: {json.dumps(note, ensure_ascii=False)[:200]}')

print()
print('6. 创建笔记 #2')
note2_data = {
    'title': '部署测试记录',
    'content': 'MemoMind 3.0.0 部署测试\n\n## 部署环境\n- Python 3.14.3\n- Node.js v24.14.0\n- Windows 11\n\n## 服务状态\n- REST API: 8000\n- MCP Server: 8001\n- Web Dashboard: 3000',
    'tags': ['部署', '测试'],
    'workspace_id': ws_id
}
r = s.post(f'{BASE}/api/notes', json=note2_data)
print(f'   状态: {r.status_code}')
note2 = r.json()
note2_id = note2.get('id')
print(f'   结果: {json.dumps(note2, ensure_ascii=False)[:200]}')

print()
print('7. 搜索测试相关笔记')
r = s.get(f'{BASE}/api/search', params={'q': '测试', 'workspace_id': ws_id})
print(f'   状态: {r.status_code}')
results = r.json()
print(f'   找到 {len(results)} 条结果')
for item in results:
    if isinstance(item, dict):
        title = item.get('title', 'unknown')
        nid = item.get('id')
    else:
        title = str(item)
        nid = item
    print(f'   - {title} (ID: {nid})')

print()
print('8. 标签列表')
r = s.get(f'{BASE}/api/tags')
print(f'   状态: {r.status_code}')
tags = r.json()
print(f'   标签: {json.dumps(tags, ensure_ascii=False)[:200]}')

print()
print('9. RAG 问答')
r = s.post(f'{BASE}/api/rag/ask', json={'question': 'MemoMind 部署在什么环境？'})
print(f'   状态: {r.status_code}')
answer = r.json()
print(f'   答案: {json.dumps(answer, ensure_ascii=False)[:300]}')

print()
print('10. 活动日志')
r = s.get(f'{BASE}/api/activity')
print(f'    状态: {r.status_code}')
activities = r.json()
print(f'    共 {len(activities)} 条活动')
for a in activities[:5]:
    action = a.get('action', 'unknown')
    detail = a.get('detail', '')[:50]
    print(f'    - {action} | {detail}')

print()
print('11. 知识图谱')
r = s.get(f'{BASE}/api/graph', params={'workspace_id': ws_id})
print(f'    状态: {r.status_code}')
graph = r.json()
nc = graph.get('node_count', 0)
ec = graph.get('edge_count', 0)
print(f'    节点数: {nc}, 边数: {ec}')

print()
print('12. 获取笔记详情')
r = s.get(f'{BASE}/api/notes/{note_id}')
print(f'    状态: {r.status_code}')
detail = r.json()
print(f'    标题: {detail.get("title")}')
print(f'    标签: {detail.get("tags", [])}')

print()
print('='*50)
print('✅ 全部测试完成！')
print(f'用户: GL-MMM (ID: {user_id})')
print(f'工作空间: GL测试空间 (ID: {ws_id})')
print(f'笔记数: 2 (ID: {note_id}, {note2_id})')
