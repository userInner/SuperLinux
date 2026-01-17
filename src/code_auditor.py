"""
代码审计器 - AI 主动审计自己的代码并提出改进
"""

import os
import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class CodeIssue:
    """代码问题"""
    file: str
    line: int
    severity: str  # high, medium, low
    category: str  # performance, security, maintainability, bug
    issue: str
    suggestion: str
    code_snippet: str


class CodeAuditor:
    """代码审计器"""
    
    def __init__(self):
        self.source_files = [
            "src/tools.py",
            "src/prompts.py",
            "src/agent.py",
            "src/experience_rag.py",
            "src/self_diagnosis.py",
            "src/self_evolution.py",
            "src/web_app.py"
        ]
    
    def audit_all(self) -> List[CodeIssue]:
        """审计所有源代码"""
        issues = []
        
        for filepath in self.source_files:
            if not os.path.exists(filepath):
                continue
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # 运行各种检查
            issues.extend(self._check_performance(filepath, lines))
            issues.extend(self._check_error_handling(filepath, lines))
            issues.extend(self._check_code_quality(filepath, lines))
            issues.extend(self._check_security(filepath, lines))
        
        # 按严重程度排序
        severity_order = {"high": 0, "medium": 1, "low": 2}
        issues.sort(key=lambda x: severity_order.get(x.severity, 3))
        
        return issues
    
    def _check_performance(self, filepath: str, lines: List[str]) -> List[CodeIssue]:
        """检查性能问题"""
        issues = []
        
        for i, line in enumerate(lines, 1):
            # 检查重复的文件读取
            if 'open(' in line and 'for' in ''.join(lines[max(0, i-5):i]):
                if self._is_in_loop(lines, i):
                    issues.append(CodeIssue(
                        file=filepath,
                        line=i,
                        severity="medium",
                        category="performance",
                        issue="在循环中打开文件",
                        suggestion="将文件操作移到循环外，或使用缓存",
                        code_snippet=line.strip()
                    ))
            
            # 检查重复的模型加载
            if 'SentenceTransformer' in line or 'load_model' in line:
                issues.append(CodeIssue(
                    file=filepath,
                    line=i,
                    severity="high",
                    category="performance",
                    issue="可能重复加载模型",
                    suggestion="使用单例模式或全局缓存",
                    code_snippet=line.strip()
                ))
            
            # 检查大量字符串拼接
            if line.count('+') > 3 and ('"' in line or "'" in line):
                issues.append(CodeIssue(
                    file=filepath,
                    line=i,
                    severity="low",
                    category="performance",
                    issue="使用 + 拼接多个字符串",
                    suggestion="使用 f-string 或 join()",
                    code_snippet=line.strip()
                ))
        
        return issues
    
    def _check_error_handling(self, filepath: str, lines: List[str]) -> List[CodeIssue]:
        """检查错误处理"""
        issues = []
        
        for i, line in enumerate(lines, 1):
            # 检查空的 except
            if 'except:' in line or 'except Exception:' in line:
                next_line = lines[i] if i < len(lines) else ""
                if 'pass' in next_line:
                    issues.append(CodeIssue(
                        file=filepath,
                        line=i,
                        severity="high",
                        category="bug",
                        issue="空的异常处理，吞掉了错误",
                        suggestion="至少记录日志或返回错误信息",
                        code_snippet=line.strip()
                    ))
            
            # 检查没有错误处理的文件操作
            if 'open(' in line:
                # 检查前后5行是否有 try
                has_try = any('try:' in lines[j] for j in range(max(0, i-5), min(len(lines), i+2)))
                if not has_try:
                    issues.append(CodeIssue(
                        file=filepath,
                        line=i,
                        severity="medium",
                        category="bug",
                        issue="文件操作没有错误处理",
                        suggestion="使用 try-except 或 with 语句",
                        code_snippet=line.strip()
                    ))
        
        return issues
    
    def _check_code_quality(self, filepath: str, lines: List[str]) -> List[CodeIssue]:
        """检查代码质量"""
        issues = []
        
        for i, line in enumerate(lines, 1):
            # 检查过长的函数
            if line.strip().startswith('def ') or line.strip().startswith('async def '):
                func_length = self._get_function_length(lines, i)
                if func_length > 100:
                    issues.append(CodeIssue(
                        file=filepath,
                        line=i,
                        severity="low",
                        category="maintainability",
                        issue=f"函数过长 ({func_length} 行)",
                        suggestion="拆分成多个小函数",
                        code_snippet=line.strip()
                    ))
            
            # 检查硬编码的值
            if re.search(r'sleep\(\d+\)', line):
                issues.append(CodeIssue(
                    file=filepath,
                    line=i,
                    severity="low",
                    category="maintainability",
                    issue="硬编码的等待时间",
                    suggestion="使用配置参数",
                    code_snippet=line.strip()
                ))
            
            # 检查重复代码
            if line.strip() and len(line.strip()) > 30:
                count = sum(1 for l in lines if l.strip() == line.strip())
                if count > 2:
                    issues.append(CodeIssue(
                        file=filepath,
                        line=i,
                        severity="low",
                        category="maintainability",
                        issue=f"重复代码 (出现 {count} 次)",
                        suggestion="提取为函数或常量",
                        code_snippet=line.strip()[:50] + "..."
                    ))
        
        return issues
    
    def _check_security(self, filepath: str, lines: List[str]) -> List[CodeIssue]:
        """检查安全问题"""
        issues = []
        
        for i, line in enumerate(lines, 1):
            # 检查 SQL 注入风险
            if 'execute(' in line and ('+' in line or 'f"' in line or "f'" in line):
                issues.append(CodeIssue(
                    file=filepath,
                    line=i,
                    severity="high",
                    category="security",
                    issue="可能的 SQL 注入风险",
                    suggestion="使用参数化查询",
                    code_snippet=line.strip()
                ))
            
            # 检查命令注入风险
            if ('os.system' in line or 'subprocess' in line) and ('+' in line or 'f"' in line):
                issues.append(CodeIssue(
                    file=filepath,
                    line=i,
                    severity="high",
                    category="security",
                    issue="可能的命令注入风险",
                    suggestion="验证和清理输入，使用参数列表",
                    code_snippet=line.strip()
                ))
            
            # 检查硬编码的密钥
            if re.search(r'(api_key|password|secret|token)\s*=\s*["\'][\w-]{20,}["\']', line, re.IGNORECASE):
                issues.append(CodeIssue(
                    file=filepath,
                    line=i,
                    severity="high",
                    category="security",
                    issue="硬编码的密钥或密码",
                    suggestion="使用环境变量或配置文件",
                    code_snippet="[已隐藏敏感信息]"
                ))
        
        return issues
    
    def _is_in_loop(self, lines: List[str], line_num: int) -> bool:
        """检查某行是否在循环中"""
        # 简单检查：向上查找 for/while
        for i in range(max(0, line_num - 10), line_num):
            if lines[i].strip().startswith(('for ', 'while ')):
                return True
        return False
    
    def _get_function_length(self, lines: List[str], start_line: int) -> int:
        """获取函数长度"""
        indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
        length = 0
        
        for i in range(start_line, len(lines)):
            line = lines[i]
            if line.strip() and not line.startswith(' ' * (indent + 1)):
                break
            length += 1
        
        return length
    
    def generate_improvement_plan(self, issues: List[CodeIssue]) -> Dict[str, Any]:
        """生成改进计划"""
        if not issues:
            return {
                "status": "excellent",
                "message": "代码质量良好，未发现明显问题",
                "improvements": []
            }
        
        # 按类别分组
        by_category = {}
        for issue in issues:
            if issue.category not in by_category:
                by_category[issue.category] = []
            by_category[issue.category].append(issue)
        
        # 生成改进计划
        improvements = []
        
        for category, category_issues in by_category.items():
            high_priority = [i for i in category_issues if i.severity == "high"]
            
            if high_priority:
                improvements.append({
                    "category": category,
                    "priority": "high",
                    "issue_count": len(high_priority),
                    "description": f"发现 {len(high_priority)} 个高优先级 {category} 问题",
                    "action": self._get_action_for_category(category),
                    "issues": [
                        {
                            "file": i.file,
                            "line": i.line,
                            "issue": i.issue,
                            "suggestion": i.suggestion
                        }
                        for i in high_priority[:3]  # 只显示前3个
                    ]
                })
        
        return {
            "status": "needs_improvement",
            "total_issues": len(issues),
            "high_priority": len([i for i in issues if i.severity == "high"]),
            "improvements": improvements
        }
    
    def _get_action_for_category(self, category: str) -> str:
        """获取类别对应的行动建议"""
        actions = {
            "performance": "优化性能瓶颈，减少重复计算和 I/O 操作",
            "security": "修复安全漏洞，防止注入攻击和信息泄露",
            "bug": "改进错误处理，避免程序崩溃",
            "maintainability": "重构代码，提高可读性和可维护性"
        }
        return actions.get(category, "改进代码质量")


# 全局实例
_auditor: CodeAuditor = None


def get_auditor() -> CodeAuditor:
    """获取全局审计器"""
    global _auditor
    if _auditor is None:
        _auditor = CodeAuditor()
    return _auditor
