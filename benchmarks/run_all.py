"""
一键运行所有基准测试

用法：python benchmarks/run_all.py
"""
import sys, os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmarks.chinese_search_benchmark import run as run_chinese_search
from benchmarks.locomo_simplified import run as run_locomo
from benchmarks.latency_benchmark import run as run_latency
from benchmarks.dreaming_benchmark import run as run_dreaming


def main():
    print("=" * 70)
    print("MemoMind 基准测试套件")
    print(f"运行时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    results = {}

    # 1. 中文搜索质量
    print("\n[1/4] 中文搜索质量基准")
    try:
        results['chinese_search'] = run_chinese_search()
    except Exception as e:
        print(f"  错误: {e}")
        results['chinese_search'] = {'error': str(e)}

    # 2. LoCoMo 检索准确率
    print("\n[2/4] LoCoMo 检索准确率")
    try:
        results['locomo'] = run_locomo()
    except Exception as e:
        print(f"  错误: {e}")
        results['locomo'] = {'error': str(e)}

    # 3. 搜索延迟
    print("\n[3/4] 搜索延迟基准")
    try:
        results['latency'] = run_latency()
    except Exception as e:
        print(f"  错误: {e}")
        results['latency'] = {'error': str(e)}

    # 4. Dreaming 框架
    print("\n[4/4] Dreaming 基准框架")
    try:
        results['dreaming'] = run_dreaming()
    except Exception as e:
        print(f"  错误: {e}")
        results['dreaming'] = {'error': str(e)}

    # 汇总
    print(f"\n{'='*70}")
    print("测试套件完成")
    print(f"{'='*70}")

    passed = 0
    failed = 0

    if 'chinese_search' in results and not isinstance(results['chinese_search'].get('error'), str):
        f1 = results['chinese_search'].get('avg_f1', 0)
        ok = f1 >= 0.75
        print(f"  中文搜索 F1: {f1:.1%} {'[OK]' if ok else '[X]'}")
        if ok: passed += 1
        else: failed += 1

    if 'locomo' in results and not isinstance(results['locomo'].get('error'), str):
        acc = results['locomo'].get('accuracy', 0)
        ok = acc >= 0.70
        print(f"  LoCoMo 准确率: {acc:.1%} {'[OK]' if ok else '[X]'}")
        if ok: passed += 1
        else: failed += 1

    latency_ok = False
    if 'latency' in results:
        lr = results['latency']
        if isinstance(lr, dict) and 2000 in lr:
            p95 = lr[2000]['p95']
            latency_ok = p95 < 50
            print(f"  搜索延迟 P95@2000: {p95:.2f}ms {'[OK]' if latency_ok else '[X]'}")
            if latency_ok: passed += 1
            else: failed += 1

    if 'dreaming' in results and isinstance(results['dreaming'], dict):
        dr = results['dreaming']
        compression = dr.get('compression_rate_pct', 0)
        f1_change = dr.get('accuracy_change', -1)
        compression_ok = compression >= 20.0
        accuracy_ok = f1_change >= -0.05
        print(f"  Dreaming 压缩率: {compression:.1f}% {'[OK]' if compression_ok else '[X]'}")
        print(f"  Dreaming F1 变化: {f1_change:+.1%} {'[OK]' if accuracy_ok else '[X]'}")
        if compression_ok and accuracy_ok:
            passed += 1
        else:
            failed += 1

    total = passed + failed
    print(f"\n通过: {passed}/{total} | 失败: {failed}/{total}")


if __name__ == '__main__':
    main()
