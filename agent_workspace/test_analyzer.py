from code_pattern_analyzer import analyze_code_patterns

result = analyze_code_patterns(".", pattern_type="all", file_pattern="*.py", max_files=50)

print("=" * 60)
print("代码模式分析报告")
print("=" * 60)
print(f"\n总文件数: {result['summary']['total_files']}")
print(f"已分析文件: {result['summary']['analyzed_files']}")
print(f"\n发现的模式:")
print(f"  - 设计模式: {result['summary']['design_patterns']}")
print(f"  - 反模式: {result['summary']['anti_patterns']}")
print(f"  - 代码异味: {result['summary']['code_smells']}")

if result['patterns']:
    print(f"\n发现的 {len(result['patterns'])} 个问题:")
    print("-" * 60)
    for p in result['patterns'][:20]:  # 显示前20个
        print(f"[{p['severity'].upper()}] {p['name']}")
        print(f"  文件: {p['file']}:{p['line']}")
        print(f"  类型: {p['type']}")
        print(f"  描述: {p['description']}")
        print()
