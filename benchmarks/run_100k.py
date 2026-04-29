"""
MemoMind 10 万条笔记性能基准测试
"""
import sys, os, time, json, random, string, tracemalloc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import Database
from core.search_service import SearchService
from core.version_service import VersionService
from core.tag_service import TagService
from core.link_service import LinkService

print('=' * 60)
print('MemoMind 性能基准测试 - 10 万条笔记')
print('=' * 60)

tracemalloc.start()
db = Database(':memory:')
search = SearchService(db)
tags = TagService(db)
links = LinkService(db)

tags_pool = ['AI', '技术', '编程', 'Python', '机器学习', '深度学习', 
             '数据库', '搜索', '标签', '版本', '链接', '笔记']

print('Generating 100000 test notes...')
t0 = time.perf_counter()
for i in range(100000):
    title = f'Note {i}'
    content = f'Content about {" ".join(random.choices(tags_pool, k=3))}. ' * random.randint(5, 15)
    tag_list = random.sample(tags_pool, random.randint(1, 4))
    db.execute('INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)',
               (title, content, json.dumps(tag_list)))
    if (i + 1) % 10000 == 0:
        elapsed = time.perf_counter() - t0
        print(f'  Generated {i+1}/100000 ({elapsed:.1f}s)')

db.commit()
gen_time = time.perf_counter() - t0
print(f'Data generation complete in {gen_time:.2f}s')

# Create tags
for tag in tags_pool:
    tags.create_tag(tag)

# Create links (every other note)
link_count = 0
for i in range(0, 100000, 2):
    if i + 1 < 100000:
        links.db.execute('INSERT INTO note_links (source_note_id, target_note_id) VALUES (?, ?)', (i+1, i+2))
        link_count += 1
        if link_count % 10000 == 0:
            links.db.commit()
links.db.commit()
print(f'Created {link_count} links')

# Memory
current, peak = tracemalloc.get_traced_memory()
print(f'Memory: {current/(1024*1024):.2f}MB (peak: {peak/(1024*1024):.2f}MB)')

# Search tests
print('\nSearch Performance Tests:')
queries = ['AI', 'AI 技术', 'Python 机器学习', '数据库 搜索', '']
search_results = {}
for query in queries:
    times = []
    for _ in range(5):
        t = time.perf_counter()
        results = search.search(query, limit=20)
        times.append((time.perf_counter() - t) * 1000)
    avg = sum(times)/len(times)
    search_results[query] = {'avg_ms': avg, 'min_ms': min(times), 'max_ms': max(times)}
    print(f'  Search "{query}": {avg:.2f}ms (min: {min(times):.2f}ms, max: {max(times):.2f}ms)')

# Tag tests
print('\nTag Performance Tests:')
t = time.perf_counter()
tags.get_all_tags()
t1 = (time.perf_counter() - t) * 1000
print(f'  Tag list: {t1:.2f}ms')

t = time.perf_counter()
tags.get_tag_tree()
t2 = (time.perf_counter() - t) * 1000
print(f'  Tag tree: {t2:.2f}ms')

# Link tests
print('\nLink Performance Tests:')
t = time.perf_counter()
links.get_outgoing_links(1)
t3 = (time.perf_counter() - t) * 1000
print(f'  Outgoing links: {t3:.2f}ms')

t = time.perf_counter()
links.get_incoming_links(2)
t4 = (time.perf_counter() - t) * 1000
print(f'  Incoming links: {t4:.2f}ms')

t = time.perf_counter()
links.get_link_graph()
t5 = (time.perf_counter() - t) * 1000
print(f'  Link graph: {t5:.2f}ms')

# Export test
print('\nExport Performance Tests:')
import tempfile
from core.export_service import ExportService
export = ExportService(db)

t = time.perf_counter()
with tempfile.TemporaryDirectory() as tmpdir:
    export.export_all_to_markdown_files(tmpdir)
t6 = (time.perf_counter() - t) * 1000
print(f'  Markdown export: {t6:.2f}ms')

t = time.perf_counter()
with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
    tmpfile = f.name
try:
    export.export_all_to_json(tmpfile)
    t7 = (time.perf_counter() - t) * 1000
    print(f'  JSON export: {t7:.2f}ms')
finally:
    if os.path.exists(tmpfile):
        os.unlink(tmpfile)

# DB file size on disk
temp_db = 'C:\\Users\\User\\AppData\\Local\\Temp\\memomind_100k_test.db'
db2 = Database(temp_db)
search2 = SearchService(db2)
tags2 = TagService(db2)
links2 = LinkService(db2)

t0 = time.perf_counter()
for i in range(100000):
    title = f'Note {i}'
    content = f'Content about {" ".join(random.choices(tags_pool, k=3))}. ' * random.randint(5, 15)
    tag_list = random.sample(tags_pool, random.randint(1, 4))
    db2.execute('INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)',
               (title, content, json.dumps(tag_list)))
db2.commit()
db2_size = os.path.getsize(temp_db)
db2.close()
os.unlink(temp_db)
print(f'\nDatabase file size (100K notes): {db2_size/(1024*1024):.2f}MB')

print('\n' + '=' * 60)
print('10 万条笔记性能基准测试完成')
print(f'  数据生成: {gen_time:.2f}s')
print(f'  内存使用: {current/(1024*1024):.2f}MB (峰值: {peak/(1024*1024):.2f}MB)')
print(f'  DB 文件大小: {db2_size/(1024*1024):.2f}MB')
print('=' * 60)

# Save report
report = {
    'note_count': 100000,
    'data_generation_seconds': gen_time,
    'memory_mb': current / (1024*1024),
    'memory_peak_mb': peak / (1024*1024),
    'db_size_mb': db2_size / (1024*1024),
    'search': search_results,
    'tag_list_ms': t1,
    'tag_tree_ms': t2,
    'outgoing_links_ms': t3,
    'incoming_links_ms': t4,
    'link_graph_ms': t5,
    'markdown_export_ms': t6,
    'json_export_ms': t7,
}

report_path = os.path.join(os.path.dirname(__file__), 'report_100k.json')
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f'\n📄 报告已保存到 {report_path}')

db.close()
