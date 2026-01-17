#!/usr/bin/env python3
"""持续代码质量检查 - 在新增代码前先检查"""

import sys
import json
from code_pattern_analyzer import analyze_code_patterns
from datetime import datetime

def check_code_quality(path=".", threshold=0):
    """检查代码质量
    
    Args:
        path: 要检查的路径
        threshold: 允许的最大问题数
    
    Returns:
        (is_ok, report_dict)
    """
    result = analyze_code_patterns(path, pattern_type="all", file_pattern="*.py", max_files=100)
    
    # 分类问题
    high_issues = [p for p in result['patterns'] if p['severity'] == 'high']
    medium_issues = [p for p in result['patterns'] if p['severity'] == 'medium']
    low_issues = [p for p in result['patterns'] if p['severity'] == 'low']
    
    # 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_files": result['summary']['total_files'],
        "analyzed_files": result['summary']['analyzed_files'],
        "issues": {
            "high": len(high_issues),
            "medium": len(medium_issues),
            "low": len(low_issues),
            "total": len(result['patterns'])
        },
        "anti_patterns": result['summary']['anti_patterns'],
        "code_smells": result['summary']['code_smells'],
        "high_priority_issues": high_issues[:10],
        "medium_priority_issues": medium_issues[:10],
        "is_ok": len(high_issues) == 0 and result['summary']['anti_patterns'] == 0
    }
    
    # 如果总问题数超过阈值，返回False
    if len(result['patterns']) > threshold and threshold > 0:
        report['is_ok'] = False
    
    return report['is_ok'], report

def print_report(report):
    """打印质量报告"""
    print("=" * 70)
    print("📊 代码质量检查报告")
    print("=" * 70)
    print(f"\n时间: {report['timestamp']}")
    print(f"文件: {report['analyzed_files']}/{report['total_files']}")
    
    issues = report['issues']
    print(f"\n问题统计:")
    print(f"  🔴 高优先级: {issues['high']}")
    print(f"  🟡 中优先级: {issues['medium']}")
    print(f"  🟢 低优先级: {issues['low']}")
    print(f"  📦 总计: {issues['total']}")
    
    print(f"\n反模式: {report['anti_patterns']} {'✅ 无' if report['anti_patterns'] == 0 else '⚠️ 发现'}")
    print(f"代码异味: {report['code_smells']}")
    
    if report['high_priority_issues']:
        print(f"\n🔴 高优先级问题 (前{len(report['high_priority_issues'])}):")
        for issue in report['high_priority_issues']:
            print(f"  • {issue['name']} - {issue['file']}:{issue['line']}")
            print(f"    {issue['description']}")
    
    if report['medium_priority_issues']:
        print(f"\n🟡 中优先级问题 (前{len(report['medium_priority_issues'])}):")
        for issue in report['medium_priority_issues']:
            print(f"  • {issue['name']} - {issue['file']}:{issue['line']}")
    
    print("\n" + "=" * 70)
    if report['is_ok']:
        print("✅ 质量检查通过！")
    else:
        print("⚠️ 发现问题，建议修复")
    print("=" * 70)

def save_report(report, filename="quality_report.json"):
    """保存报告到JSON文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"📝 报告已保存到 {filename}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="持续代码质量检查")
    parser.add_argument("--path", default=".", help="要检查的路径")
    parser.add_argument("--threshold", type=int, default=0, help="允许的最大问题数")
    parser.add_argument("--save", action="store_true", help="保存报告到JSON")
    parser.add_argument("--quiet", action="store_true", help="安静模式，只输出结果")
    
    args = parser.parse_args()
    
    is_ok, report = check_code_quality(args.path, args.threshold)
    
    if not args.quiet:
        print_report(report)
    
    if args.save:
        save_report(report)
    
    sys.exit(0 if is_ok else 1)
