"""代码模式分析工具 - 分析设计模式、反模式、代码异味"""

import ast
import os
import glob
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class CodePattern:
    """发现的代码模式"""
    name: str
    type: str  # design_pattern, anti_pattern, code_smell
    file: str
    line: int
    description: str
    severity: str  # low, medium, high


class CodePatternAnalyzer(ast.NodeVisitor):
    """分析代码模式的AST访问器"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.patterns: List[CodePattern] = []
        self.class_names = []
        self.function_names = []
    
    def visit_ClassDef(self, node):
        """分析类定义"""
        self.class_names.append(node.name)
        
        # 检查单例模式
        singleton_indicators = []
        if node.name.endswith('Singleton'):
            singleton_indicators.append('name')
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id in ('_instance', '_instance'):
                        singleton_indicators.append('instance')
        if len(singleton_indicators) >= 2:
            self.patterns.append(CodePattern(
                name="Singleton Pattern",
                type="design_pattern",
                file=self.filepath,
                line=node.lineno,
                description=f"类 {node.name} 实现了单例模式",
                severity="low"
            ))
        
        # 检查大类（超过300行）
        if hasattr(node, 'end_lineno') and node.end_lineno:
            lines = node.end_lineno - node.lineno
            if lines > 300:
                self.patterns.append(CodePattern(
                    name="Large Class",
                    type="code_smell",
                    file=self.filepath,
                    line=node.lineno,
                    description=f"类 {node.name} 过大（{lines}行），建议拆分",
                    severity="medium"
                ))
        
        # 检查上帝类（太多方法）
        method_count = sum(1 for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)))
        if method_count > 15:
            self.patterns.append(CodePattern(
                name="God Class",
                type="code_smell",
                file=self.filepath,
                line=node.lineno,
                description=f"类 {node.name} 包含 {method_count} 个方法，可能是上帝类",
                severity="high"
            ))
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        """分析函数定义"""
        self.function_names.append(node.name)
        
        # 检查长函数（超过50行）
        if hasattr(node, 'end_lineno') and node.end_lineno:
            lines = node.end_lineno - node.lineno
            if lines > 50:
                self.patterns.append(CodePattern(
                    name="Long Function",
                    type="code_smell",
                    file=self.filepath,
                    line=node.lineno,
                    description=f"函数 {node.name} 过长（{lines}行），建议拆分",
                    severity="medium"
                ))
        
        # 检查参数过多的函数（超过7个参数）
        if len(node.args.args) > 7:
            self.patterns.append(CodePattern(
                name="Too Many Parameters",
                type="code_smell",
                file=self.filepath,
                line=node.lineno,
                description=f"函数 {node.name} 有 {len(node.args.args)} 个参数，考虑使用参数对象",
                severity="medium"
            ))
        
        # 检查重复代码（简单的判断）
        if 'duplicate' in node.name.lower() or 'copy' in node.name.lower():
            self.patterns.append(CodePattern(
                name="Potential Code Duplication",
                type="anti_pattern",
                file=self.filepath,
                line=node.lineno,
                description=f"函数名 '{node.name}' 暗示可能存在代码重复",
                severity="low"
            ))
        
        self.generic_visit(node)
    
    def visit_Try(self, node):
        """分析异常处理"""
        for handler in node.handlers:
            # 检查空的except块
            if not handler.type and not handler.body:
                self.patterns.append(CodePattern(
                    name="Bare Except with No Handler",
                    type="anti_pattern",
                    file=self.filepath,
                    line=node.lineno,
                    description="空的异常处理块，会吞掉所有错误",
                    severity="high"
                ))
            elif handler.type and not handler.body:
                self.patterns.append(CodePattern(
                    name="Empty Exception Handler",
                    type="anti_pattern",
                    file=self.filepath,
                    line=node.lineno,
                    description="空的异常处理，会吞掉错误",
                    severity="high"
                ))
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """检查import语句中的反模式"""
        # 检查通配符导入
        if node.names and any(alias.name == '*' for alias in node.names):
            self.patterns.append(CodePattern(
                name="Wildcard Import",
                type="anti_pattern",
                file=self.filepath,
                line=node.lineno,
                description="使用通配符导入（from module import *），污染命名空间",
                severity="medium"
            ))
        
        self.generic_visit(node)


def analyze_code_patterns(path: str, pattern_type: str = "all", file_pattern: str = "*.py", max_files: int = 50) -> Dict:
    """分析代码模式
    
    Args:
        path: 要分析的代码路径
        pattern_type: 分析的模式类型（design_patterns, anti_patterns, code_smells, all）
        file_pattern: 文件名模式
        max_files: 最大分析文件数
    
    Returns:
        包含分析结果的字典
    """
    result = {
        "summary": {
            "total_files": 0,
            "analyzed_files": 0,
            "design_patterns": 0,
            "anti_patterns": 0,
            "code_smells": 0
        },
        "patterns": []
    }
    
    # 收集文件
    files = []
    for pattern in [file_pattern, "**/" + file_pattern]:
        files.extend(glob.glob(os.path.join(path, pattern), recursive=True))
    
    files = list(set(files))[:max_files]
    result["summary"]["total_files"] = len(files)
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            analyzer = CodePatternAnalyzer(filepath)
            analyzer.visit(tree)
            
            result["summary"]["analyzed_files"] += 1
            
            for pattern in analyzer.patterns:
                if pattern_type == "all" or pattern.type == pattern_type:
                    result["patterns"].append({
                        "name": pattern.name,
                        "type": pattern.type,
                        "file": os.path.basename(filepath),
                        "line": pattern.line,
                        "description": pattern.description,
                        "severity": pattern.severity
                    })
                    
                    if pattern.type == "design_pattern":
                        result["summary"]["design_patterns"] += 1
                    elif pattern.type == "anti_pattern":
                        result["summary"]["anti_patterns"] += 1
                    elif pattern.type == "code_smell":
                        result["summary"]["code_smells"] += 1
        
        except Exception as e:
            # 跳过解析失败的文件
            continue
    
    # 按严重程度排序
    severity_order = {"high": 0, "medium": 1, "low": 2}
    result["patterns"].sort(key=lambda x: severity_order.get(x["severity"], 3))
    
    return result


if __name__ == "__main__":
    # 测试
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    result = analyze_code_patterns(path)
    print(f"分析完成：{result['summary']['analyzed_files']} 个文件")
    print(f"发现设计模式：{result['summary']['design_patterns']}")
    print(f"发现反模式：{result['summary']['anti_patterns']}")
    print(f"发现代码异味：{result['summary']['code_smells']}")
