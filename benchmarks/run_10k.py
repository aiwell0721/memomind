"""
MemoMind 1 万条笔记性能基准测试
"""
import sys, os, time, json, random, tracemalloc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import Database
from core.search_service import SearchService
from core.tag_service import TagService
from core.link_service import LinkService
from core.export_service import ExportService

print('=' * 60)
print('MemoMind 性能基准测试 - 1 万条笔记')
print('=' * 60)

tracemalloc.start()
db = Database(':memory:')
search = SearchService(db)
tags_svc = TagService(db)
links_svc = LinkService(db)
export = ExportService(db)

tags_pool = ['AI', '技术', '编程', 'Python', '机器学习', '深度学习', 
             '数据库', '搜索', '标签', '版本', '链接', '笔记']

print('Generating 10000 test notes...')
t0 = time.perf_counter()
for i in range(10000):
    title = f'Note {i}'
    content = f'Content about {" ".join(random.choices(tags_pool, k=3))}. ' * random.randint(5, 15)
    tag_list = random.sample(tags_pool, random.randint(1, 4))
    db.execute('INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)',
               (title, content, json.dumps(tag_list)))
    if (i + 1) % 2000 == 0:
        print(f'  Generated {i+1}/10000')

db.commit()
gen_time = time.perf_counter() - t0
print(f'Data generation complete in {gen_time:.2f}s')

for tag in tags_pool:
    tags_svc.create_tag(tag)

for i in range(0, 9998, 2):
    links_svc.db.execute('INSERT INTO note_links (source_note_id, target_note_id) VALUES (?, ?)', (i+1, i+2))
links_svc.db.commit()

current, peak = tracemalloc.get_traced_memory()
print(f'Memory: {current/(1024*1024):.2f}MB (peak: {peak/(1024*1024):.2f}MB)')

# Search tests
print('\nSearch Performance Tests:')
search_results = {}
for query in ['AI', 'AI 技术', 'Python 机器学习', '数据库 搜索', '']:
    times = []
    for _ in range(10):
        t = time.perf_counter()
        search.search(query, limit=20)
        times.append((time.perf_counter() - t) * 1000)
    avg = sum(times)/len(times)
    search_results[query] = {'avg_ms': round(avg, 3), 'min_ms': round(min(times), 3), 'max_ms': round(max(times), 3)}
    print(f'  Search "{query}": {avg:.3f}ms')

# Tag tests
print('\nTag Performance Tests:')
t = time.perf_counter(); tags_svc.get_all_tags(); t1 = (time.perf_counter() - t) * 1000
t = time.perf_counter(); tags_svc.get_tag_tree(); t2 = (time.perf_counter() - t) * 1000
print(f'  Tag list: {t1:.3f}ms, Tag tree: {t2:.3f}ms')

# Link tests
print('\nLink Performance Tests:')
t = time.perf_counter(); links_svc.get_outgoing_links(1); t3 = (time.perf_counter() - t) * 1000
t = time.perf_counter(); links_svc.get_incoming_links(2); t4 = (time.perf_counter() - t) * 1000
t = time.perf_counter(); links_svc.get_link_graph(); t5 = (time.perf_counter() - t) * 1000
print(f'  Outgoing: {t3:.3f}ms, Incoming: {t4:.3f}ms, Graph: {t5:.3f}ms')

# Export tests
print('\nExport Performance Tests:')
import tempfile
t = time.perf_counter()
with tempfile.TemporaryDirectory() as tmpdir:
    export.export_all_to_markdown_files(tmpdir)
t6 = (time.perf_counter() - t) * 1000

t = time.perf_counter()
with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
    tmpfile = f.name
try:
    export.export_all_to_json(tmpfile)
    t7 = (time.perf_counter() - t) * 1000
finally:
    if os.path.exists(tmpfile): os.unlink(tmpfile)
print(f'  Markdown export: {t6:.1f}ms, JSON export: {t7:.1f}ms')

# DB size
temp_db = 'C:\\Users\\User\\AppData\\Local\\Temp\\memomind_10k_test.db'
db2 = Database(temp_db)
SearchService(db2); TagService(db2); LinkService(db2)
for i in range(10000):
    title = f'Note {i}'
    content = f'Content about {" ".join(random.choices(tags_pool, k=3))}. ' * random.randint(5, 15)
    tag_list = random.sample(tags_pool, random.randint(1, 4))
    db2.execute('INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)',
               (title, content, json.dumps(tag_list)))
db2.commit()
db2_size = os.path.getsize(temp_db)
db2.close(); os.unlink(temp_db)
print(f'\nDatabase file size (10K notes): {db2_size/(1024*1024):.2f}MB')

print('\n' + '=' * 60)
print('1 万条笔记性能基准测试完成')
print(f'  数据生成: {gen_time:.2f}s')
print(f'  内存使用: {current/(1024*1024):.2f}MB (峰值: {peak/(1024*1024):.2f}MB)')
print(f'  DB 文件大小: {db2_size/(1024*1024):.2f}MB')
print('=' * 60)

report = {
    'note_count': 10000,
    'data_generation_seconds': round(gen_time, 2),
    'memory_mb': round(current / (1024*1024), 2),
    'memory_peak_mb': round(peak / (1024*1024), 2),
    'db_size_mb': round(db2_size / (1024*1024), 2),
    'search': search_results,
    'tag_list_ms': round(t1, 3),
    'tag_tree_ms': round(t2, 3),
    'outgoing_links_ms': round(t3, 3),
    'incoming_links_ms': round(t4, 3),
    'link_graph_ms': round(t5, 3),
    'markdown_export_ms': round(t6, 1),
    'json_export_ms': round(t7, 1),
}

report_path = os.path.join(os.path.dirname(__file__), 'report_10k.json')
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f'\n📄 报告已保存到 {report_path}')
db.close()
