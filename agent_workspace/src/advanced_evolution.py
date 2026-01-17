"""
高级进化机制 - Phase 4

实现三个核心进化能力：
1. 自主工具工厂
2. Prompt 自愈能力  
3. 环境自适应
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import hashlib


# ==================== 1. 自主工具工厂 ====================

@dataclass
class CommandPattern:
    """命令模式"""
    pattern_id: str
    commands: List[str]
    description: str
    usage_count: int
    first_used: str
    last_used: str
    task_type: str  # "system_check", "deployment", "monitoring", etc.


class ToolFactory:
    """自主工具工厂 - 自动将重复的命令流封装为标准工具"""
    
    def __init__(self, db_path: str = "./experience_db"):
        self.db_path = db_path
        self.patterns_file = os.path.join(db_path, "command_patterns.json")
        self.tools_dir = os.path.join(db_path, "generated_tools")
        
        os.makedirs(self.tools_dir, exist_ok=True)
        os.makedirs(self.db_path, exist_ok=True)
        
        self.patterns: Dict[str, CommandPattern] = {}
        self._load_patterns()
        
        # 工具模板
        self.tool_template = '''"""
自动生成的工具: {tool_name}

描述: {description}
生成时间: {timestamp}
来源: 由 ToolFactory 基于重复命令模式自动生成
"""

from typing import Dict, Any
import subprocess


def {tool_name}({params}) -> Dict[str, Any]:
    """{description}
    
    参数:
{param_docs}
    
    返回:
        Dict[str, Any]: 执行结果
    """
    try:
        {implementation}
        return {{
            "success": True,
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode
        }}
    except Exception as e:
        return {{
            "success": False,
            "error": str(e)
        }}
'''
    
    def _load_patterns(self):
        """加载已记录的命令模式"""
        if os.path.exists(self.patterns_file):
            try:
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for pattern_id, pattern_data in data.items():
                        self.patterns[pattern_id] = CommandPattern(**pattern_data)
            except Exception:
                pass
    
    def _save_patterns(self):
        """保存命令模式"""
        with open(self.patterns_file, 'w', encoding='utf-8') as f:
            json.dump(
                {pid: asdict(p) for pid, p in self.patterns.items()},
                f,
                ensure_ascii=False,
                indent=2
            )
    
    def record_command_usage(self, commands: List[str], task_type: str = "general"):
        """记录命令使用情况
        
        Args:
            commands: 命令列表
            task_type: 任务类型
        """
        # 生成模式指纹
        pattern_id = self._generate_pattern_id(commands)
        
        now = datetime.now().isoformat()
        
        if pattern_id in self.patterns:
            # 更新现有模式
            pattern = self.patterns[pattern_id]
            pattern.usage_count += 1
            pattern.last_used = now
            pattern.commands = commands  # 更新为最新版本
        else:
            # 创建新模式
            self.patterns[pattern_id] = CommandPattern(
                pattern_id=pattern_id,
                commands=commands,
                description=f"自动生成的 {task_type} 工具",
                usage_count=1,
                first_used=now,
                last_used=now,
                task_type=task_type
            )
        
        self._save_patterns()
        
        # 检查是否达到创建工具的阈值
        if self.patterns[pattern_id].usage_count >= 3:
            return self._create_tool_from_pattern(pattern_id)
        
        return None
    
    def _generate_pattern_id(self, commands: List[str]) -> str:
        """生成模式 ID"""
        # 规范化命令（去除空格、注释等）
        normalized = []
        for cmd in commands:
            # 移除注释，只保留命令
            cleaned = re.sub(r'#.*$', '', cmd).strip()
            if cleaned:
                normalized.append(cleaned)
        
        # 生成哈希
        pattern_str = '|'.join(normalized)
        return hashlib.md5(pattern_str.encode()).hexdigest()[:12]
    
    def _create_tool_from_pattern(self, pattern_id: str) -> Optional[str]:
        """从命令模式创建工具"""
        pattern = self.patterns[pattern_id]
        
        # 生成工具名称
        tool_name = f"auto_{pattern.task_type}_{pattern.pattern_id[:8]}"
        
        # 生成工具文件
        tool_file = os.path.join(self.tools_dir, f"{tool_name}.py")
        
        # 分析命令，提取参数和实现
        implementation_code = []
        params = []
        param_docs = []
        
        for i, cmd in enumerate(pattern.commands):
            # 检测参数（如 {package}, {file} 等）
            placeholders = re.findall(r'\{(\w+)\}', cmd)
            
            for ph in placeholders:
                if ph not in params:
                    params.append(ph)
                    param_docs.append(f"        {ph}: {ph} 参数")
            
            # 构建实现代码
            if placeholders:
                # 有参数的命令
                formatted_cmd = cmd.format(**{ph: f"{ph}" for ph in placeholders})
                implementation_code.append(
                    f'        result_{i} = subprocess.run("{formatted_cmd}", shell=True, capture_output=True, text=True)'
                )
            else:
                # 无参数的命令
                implementation_code.append(
                    f'        result_{i} = subprocess.run("{cmd}", shell=True, capture_output=True, text=True)'
                )
        
        # 添加检查逻辑
        impl = "\n".join(implementation_code)
        impl += "\n        return result_{} if 'result_{}' in locals() else None".format(
            len(implementation_code) - 1, len(implementation_code) - 1
        )
        
        # 填充模板
        tool_content = self.tool_template.format(
            tool_name=tool_name,
            description=pattern.description,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            params=", ".join(params) if params else "",
            param_docs="\n".join(param_docs) if param_docs else "        无",
            implementation=impl
        )
        
        # 写入文件
        try:
            with open(tool_file, 'w', encoding='utf-8') as f:
                f.write(tool_content)
            
            print(f"🔧 自主工具工厂: 创建新工具 {tool_name}")
            print(f"   来源: {len(pattern.commands)} 个命令，使用 {pattern.usage_count} 次")
            
            return tool_file
        except Exception as e:
            print(f"❌ 创建工具失败: {e}")
            return None
    
    def get_tool_suggestions(self) -> List[Dict]:
        """获取工具创建建议"""
        suggestions = []
        
        for pattern in self.patterns.values():
            if pattern.usage_count >= 2:  # 接近阈值
                suggestions.append({
                    "pattern_id": pattern.pattern_id,
                    "description": pattern.description,
                    "usage_count": pattern.usage_count,
                    "commands": pattern.commands,
                    "urgency": "high" if pattern.usage_count >= 3 else "medium"
                })
        
        return sorted(suggestions, key=lambda x: x['usage_count'], reverse=True)


# ==================== 2. Prompt 自愈能力 ====================

@dataclass
class PromptCorrection:
    """Prompt 纠偏记录"""
    correction_id: str
    timestamp: str
    issue_type: str  # "misunderstanding", "wrong_tool", "missing_step"
    original_prompt: str
    problem: str
    suggested_fix: str
    effectiveness: float  # 0-1


class PromptSelfHealing:
    """Prompt 自愈系统 - 基于纠偏记录自动优化 Prompt"""
    
    def __init__(self, prompt_file: str = None, db_path: str = "./experience_db"):
        # 自动定位 prompt 文件
        if prompt_file is None:
            # 尝试多个可能的路径
            possible_paths = [
                "prompts.py",
                "src/prompts.py",
                "./prompts.py"
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    prompt_file = path
                    break
            if prompt_file is None:
                prompt_file = "prompts.py"  # 默认值
        
        self.prompt_file = prompt_file
        self.corrections_file = os.path.join(db_path, "prompt_corrections.json")
        self.backup_dir = os.path.join(db_path, "prompt_backups")
        
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(db_path, exist_ok=True)
        
        self.corrections: List[PromptCorrection] = []
        self._load_corrections()
    
    def _load_corrections(self):
        """加载纠偏记录"""
        if os.path.exists(self.corrections_file):
            try:
                with open(self.corrections_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.corrections = [PromptCorrection(**c) for c in data]
            except Exception:
                pass
    
    def _save_corrections(self):
        """保存纠偏记录"""
        with open(self.corrections_file, 'w', encoding='utf-8') as f:
            json.dump(
                [asdict(c) for c in self.corrections],
                f,
                ensure_ascii=False,
                indent=2
            )
    
    def record_correction(
        self,
        issue_type: str,
        problem: str,
        suggested_fix: str
    ) -> str:
        """记录 Prompt 纠偏
        
        Args:
            issue_type: 问题类型
            problem: 问题描述
            suggested_fix: 建议修复方案
        
        Returns:
            str: 纠偏记录 ID
        """
        correction_id = f"corr_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 读取当前 prompt（简化版）
        original_prompt = "current_prompt_section"
        
        correction = PromptCorrection(
            correction_id=correction_id,
            timestamp=datetime.now().isoformat(),
            issue_type=issue_type,
            original_prompt=original_prompt,
            problem=problem,
            suggested_fix=suggested_fix,
            effectiveness=0.0  # 初始为 0，后续评估
        )
        
        self.corrections.append(correction)
        self._save_corrections()
        
        # 检查是否需要自动修复
        self._check_and_apply_healing()
        
        return correction_id
    
    def _check_and_apply_healing(self):
        """检查并应用自愈修复"""
        # 统计问题模式
        issue_counts = {}
        for c in self.corrections:
            key = f"{c.issue_type}:{c.problem[:50]}"
            issue_counts[key] = issue_counts.get(key, 0) + 1
        
        # 找出频繁出现的问题
        frequent_issues = [
            (issue, count) for issue, count in issue_counts.items() if count >= 3
        ]
        
        for issue, count in frequent_issues:
            issue_type, problem = issue.split(':', 1)
            print(f"🔍 Prompt 自愈: 检测到频繁问题 (出现 {count} 次)")
            print(f"   类型: {issue_type}")
            print(f"   问题: {problem}")
            
            # 获取相关的修复建议
            related_corrections = [
                c for c in self.corrections
                if c.issue_type == issue_type and problem in c.problem
            ]
            
            if related_corrections:
                # 应用最常见的修复
                self._apply_healing_fix(related_corrections[0])
    
    def _apply_healing_fix(self, correction: PromptCorrection):
        """应用自愈修复"""
        try:
            # 备份
            backup_path = os.path.join(
                self.backup_dir,
                f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            )
            import shutil
            shutil.copy2(self.prompt_file, backup_path)
            
            # 读取当前 prompt
            with open(self.prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 根据问题类型应用修复
            fix_applied = False
            
            if correction.issue_type == "misunderstanding":
                # 理解偏差 - 添加更明确的指导
                clarification = f"""
### 常见误解纠正
- {correction.problem}
- 解决方案: {correction.suggested_fix}
"""
                if "## 常见问题" not in content:
                    content += "\n## 常见问题\n" + clarification
                    fix_applied = True
            
            elif correction.issue_type == "wrong_tool":
                # 工具选择错误 - 添加工具选择指导
                tool_guidance = f"""
### 工具选择指导
- {correction.problem}: {correction.suggested_fix}
"""
                if "## 工具使用策略" in content and tool_guidance not in content:
                    content = content.replace(
                        "## 工具使用策略",
                        "## 工具使用策略" + tool_guidance
                    )
                    fix_applied = True
            
            elif correction.issue_type == "missing_step":
                # 缺少步骤 - 添加步骤提醒
                step_reminder = f"""
### 重要步骤提醒
- {correction.problem}: {correction.suggested_fix}
"""
                if "## 工作流程" in content and step_reminder not in content:
                    content = content.replace(
                        "## 工作流程",
                        "## 工作流程" + step_reminder
                    )
                    fix_applied = True
            
            if fix_applied:
                # 写入修改后的内容
                with open(self.prompt_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ Prompt 自愈: 已应用修复")
                print(f"   备份: {backup_path}")
            
        except Exception as e:
            print(f"❌ 应用自愈修复失败: {e}")


# ==================== 3. 环境自适应 ====================

@dataclass
class EnvironmentProfile:
    """环境配置文件"""
    distro: str  # "ubuntu", "centos", "debian", etc.
    version: str
    package_manager: str  # "apt", "yum", "dnf", etc.
    init_system: str  # "systemd", "init", etc.
    python_path: str
    node_path: str
    last_updated: str


class EnvironmentAdaptive:
    """环境自适应系统 - 根据系统环境自动调整行为"""
    
    def __init__(self, db_path: str = "./experience_db"):
        self.db_path = db_path
        self.profile_file = os.path.join(db_path, "environment_profile.json")
        
        os.makedirs(db_path, exist_ok=True)
        
        self.profile: Optional[EnvironmentProfile] = None
        self._load_or_detect_profile()
        
        # 命令映射表
        self.command_mappings = {
            "ubuntu": {
                "install": "apt install -y {package}",
                "update": "apt update && apt upgrade -y",
                "remove": "apt remove -y {package}",
                "search": "apt search {package}",
                "service_start": "systemctl start {service}",
                "service_stop": "systemctl stop {service}",
                "service_status": "systemctl status {service}"
            },
            "centos": {
                "install": "yum install -y {package}" if self._is_centos7() else "dnf install -y {package}",
                "update": "yum update -y" if self._is_centos7() else "dnf upgrade -y",
                "remove": "yum remove -y {package}" if self._is_centos7() else "dnf remove -y {package}",
                "search": "yum search {package}" if self._is_centos7() else "dnf search {package}",
                "service_start": "systemctl start {service}",
                "service_stop": "systemctl stop {service}",
                "service_status": "systemctl status {service}"
            },
            "debian": {
                "install": "apt-get install -y {package}",
                "update": "apt-get update && apt-get upgrade -y",
                "remove": "apt-get remove -y {package}",
                "search": "apt-cache search {package}",
                "service_start": "systemctl start {service}",
                "service_stop": "systemctl stop {service}",
                "service_status": "systemctl status {service}"
            }
        }
    
    def _is_centos7(self) -> bool:
        """检测是否为 CentOS 7"""
        try:
            result = subprocess.run(
                ["cat", "/etc/centos-release"],
                capture_output=True,
                text=True
            )
            return "7." in result.stdout
        except:
            return False
    
    def _load_or_detect_profile(self):
        """加载或检测环境配置"""
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.profile = EnvironmentProfile(**data)
                
                # 检查是否需要更新
                last_updated = datetime.fromisoformat(self.profile.last_updated)
                if (datetime.now() - last_updated).days > 7:
                    # 超过7天，重新检测
                    self._detect_environment()
            except Exception:
                self._detect_environment()
        else:
            self._detect_environment()
    
    def _detect_environment(self):
        """检测系统环境"""
        print("🔍 环境自适应: 检测系统环境...")
        
        distro = "unknown"
        version = "unknown"
        
        # 检测发行版
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", 'r') as f:
                    content = f.read()
                    
                if "ubuntu" in content.lower():
                    distro = "ubuntu"
                    match = re.search(r'VERSION_ID="([^"]+)"', content)
                    version = match.group(1) if match else "unknown"
                elif "centos" in content.lower():
                    distro = "centos"
                    match = re.search(r'VERSION_ID="([^"]+)"', content)
                    version = match.group(1) if match else "unknown"
                elif "debian" in content.lower():
                    distro = "debian"
                    match = re.search(r'VERSION_ID="([^"]+)"', content)
                    version = match.group(1) if match else "unknown"
        except Exception as e:
            print(f"   ⚠️  检测发行版失败: {e}")
        
        # 确定包管理器
        package_manager = "apt"
        if distro == "centos":
            package_manager = "yum" if self._is_centos7() else "dnf"
        elif distro == "debian":
            package_manager = "apt-get"
        
        # 检测 init 系统
        init_system = "systemd"
        try:
            subprocess.run(["which", "systemctl"], capture_output=True)
        except:
            init_system = "init"
        
        # 检测 Python 路径
        python_path = "/usr/bin/python3"
        try:
            result = subprocess.run(["which", "python3"], capture_output=True, text=True)
            if result.returncode == 0:
                python_path = result.stdout.strip()
        except:
            pass
        
        # 检测 Node.js 路径
        node_path = "/usr/bin/node"
        try:
            result = subprocess.run(["which", "node"], capture_output=True, text=True)
            if result.returncode == 0:
                node_path = result.stdout.strip()
        except:
            pass
        
        # 创建配置
        self.profile = EnvironmentProfile(
            distro=distro,
            version=version,
            package_manager=package_manager,
            init_system=init_system,
            python_path=python_path,
            node_path=node_path,
            last_updated=datetime.now().isoformat()
        )
        
        # 保存配置
        with open(self.profile_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.profile), f, indent=2)
        
        print(f"   ✅ 检测完成: {distro} {version}")
        print(f"   包管理器: {package_manager}")
        print(f"   Init 系统: {init_system}")
    
    def get_adapted_command(self, command_type: str, **kwargs) -> str:
        """获取适配的命令
        
        Args:
            command_type: 命令类型
            **kwargs: 命令参数
        
        Returns:
            str: 适配后的命令
        """
        if not self.profile:
            self._detect_environment()
        
        # 获取对应发行版的命令
        distro_commands = self.command_mappings.get(self.profile.distro, {})
        command_template = distro_commands.get(command_type)
        
        if command_template:
            # 替换参数
            try:
                return command_template.format(**kwargs)
            except KeyError as e:
                print(f"⚠️  命令参数缺失: {e}")
                return command_template
        
        # 回退到通用命令
        fallback_commands = {
            "install": "apt install -y {package}",
            "update": "apt update && apt upgrade -y",
            "remove": "apt remove -y {package}",
            "service_start": "systemctl start {service}",
            "service_stop": "systemctl stop {service}",
            "service_status": "systemctl status {service}"
        }
        
        return fallback_commands.get(command_type, "")
    
    def get_package_manager_command(self, action: str, package: str) -> str:
        """获取包管理器命令（便捷方法）
        
        Args:
            action: "install", "update", "remove", "search"
            package: 包名
        
        Returns:
            str: 完整命令
        """
        return self.get_adapted_command(action, package=package)
    
    def get_service_command(self, action: str, service: str) -> str:
        """获取服务管理命令（便捷方法）
        
        Args:
            action: "start", "stop", "status"
            service: 服务名
        
        Returns:
            str: 完整命令
        """
        return self.get_adapted_command(f"service_{action}", service=service)
    
    def relearn_environment(self):
        """重新学习环境配置"""
        self._detect_environment()
