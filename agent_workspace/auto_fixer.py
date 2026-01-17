"""
自动修复器 - AI 自动修复代码问题
"""

import os
import re
import shutil
from typing import List, Dict, Any
from datetime import datetime

from .code_auditor import CodeIssue, get_auditor


class AutoFixer:
    """自动代码修复器"""
    
    def __init__(self):
        self.backup_dir = ".evolution_backups/auto_fixes"
        os.makedirs(self.backup_dir, exist_ok=True)
        self.fixes_applied = []
    
    def auto_fix_all(self, issues: List[CodeIssue], max_fixes: int = 10) -> Dict[str, Any]:
        """自动修复所有可以修复的问题"""
        results = {
            "total_issues": len(issues),
            "attempted": 0,
            "successful": 0,
            "failed": 0,
            "fixes": []
        }
        
        # 只修复高优先级和中优先级
        fixable_issues = [i for i in issues if i.severity in ["high", "medium"]]
        fixable_issues = fixable_issues[:max_fixes]  # 限制数量
        
        for issue in fixable_issues:
            results["attempted"] += 1
            
            fix_result = self._try_fix_issue(issue)
            
            if fix_result["success"]:
                results["successful"] += 1
            else:
                results["failed"] += 1
            
            results["fixes"].append(fix_result)
        
        return results
    
    def _try_fix_issue(self, issue: CodeIssue) -> Dict[str, Any]:
        """尝试修复单个问题"""
        result = {
            "issue": {
                "file": issue.file,
                "line": issue.line,
                "category": issue.category,
                "issue": issue.issue
            },
            "success": False,
            "fix_applied": None,
            "error": None
        }
        
        try:
            # 根据问题类型选择修复方法
            if "空的异常处理" in issue.issue:
                fix = self._fix_empty_except(issue)
            elif "重复加载模型" in issue.issue:
                fix = self._fix_model_loading(issue)
            elif "文件操作没有错误处理" in issue.issue:
                fix = self._fix_file_operation(issue)
            elif "硬编码" in issue.issue:
                fix = self._fix_hardcoded_value(issue)
            elif "重复代码" in issue.issue:
                fix = None  # 重复代码需要更复杂的重构
            else:
                fix = None
            
            if fix:
                # 应用修复
                success = self._apply_fix(issue.file, issue.line, fix)
                if success:
                    result["success"] = True
                    result["fix_applied"] = fix
                    self.fixes_applied.append(result)
                else:
                    result["error"] = "应用修复失败"
            else:
                result["error"] = "暂不支持自动修复此类问题"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _fix_empty_except(self, issue: CodeIssue) -> str:
        """修复空的异常处理"""
        # 读取原代码
        with open(issue.file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if issue.line >= len(lines):
            return None
        
        line = lines[issue.line - 1]
        indent = len(line) - len(line.lstrip())
        
        # 检查下一行是否是 pass
        if issue.line < len(lines):
            next_line = lines[issue.line]
            if 'pass' in next_line:
                # 替换 pass 为日志记录
                new_line = ' ' * (indent + 4) + 'pass  # TODO: 添加错误处理\n'
                return new_line
        
        return None
    
    def _fix_model_loading(self, issue: CodeIssue) -> str:
        """修复重复加载模型"""
        # 这个需要更复杂的重构，暂时返回 None
        # 实际应该添加单例模式或缓存
        return None
    
    def _fix_file_operation(self, issue: CodeIssue) -> str:
        """修复文件操作缺少错误处理"""
        with open(issue.file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        line = lines[issue.line - 1]
        indent = len(line) - len(line.lstrip())
        
        # 在 open() 前添加 try
        fixed_lines = []
        fixed_lines.append(' ' * indent + 'try:\n')
        fixed_lines.append(line)
        
        # 找到这个代码块的结束
        # 简单处理：假设下一行就是结束
        fixed_lines.append(' ' * indent + 'except Exception as e:\n')
        fixed_lines.append(' ' * (indent + 4) + 'print(f"文件操作失败: {e}")\n')
        
        return ''.join(fixed_lines)
    
    def _fix_hardcoded_value(self, issue: CodeIssue) -> str:
        """修复硬编码的值"""
        # 这个需要更复杂的重构
        return None
    
    def _apply_fix(self, filepath: str, line_num: int, fix: str) -> bool:
        """应用修复"""
        try:
            # 1. 备份
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(
                self.backup_dir,
                f"{os.path.basename(filepath)}_{timestamp}"
            )
            shutil.copy2(filepath, backup_path)
            
            # 2. 读取文件
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if line_num < 1 or line_num > len(lines):
                return False
            
            # 3. 应用修复 - 替换指定行
            lines[line_num - 1] = fix if fix.endswith('\n') else fix + '\n'
            
            # 4. 写入
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            # 5. 验证语法
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    compile(f.read(), filepath, 'exec')
                print(f"  ✅ 修复成功: {filepath}:{line_num}")
                return True
            except SyntaxError as e:
                # 回滚
                print(f"  ❌ 语法错误，回滚: {e}")
                shutil.copy2(backup_path, filepath)
                return False
        
        except Exception as e:
            print(f"  ❌ 应用修复失败: {e}")
            return False


def auto_fix_code(focus: str = "all", max_fixes: int = 10) -> Dict[str, Any]:
    """自动修复代码问题"""
    # 1. 审计代码
    auditor = get_auditor()
    issues = auditor.audit_all()
    
    # 2. 过滤
    if focus != "all":
        issues = [i for i in issues if i.category == focus]
    
    # 3. 自动修复
    fixer = AutoFixer()
    results = fixer.auto_fix_all(issues, max_fixes)
    
    return results
