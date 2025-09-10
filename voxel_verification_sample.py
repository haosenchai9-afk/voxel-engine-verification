#!/usr/bin/env python3
# =============================================================================
# 样例：Voxel Engine提交日期验证脚本（针对voxel-engine-docs仓库）
# 功能：验证voxel-engine-docs仓库中Voxel Engine相关提交日期与文档完整性
# 依赖: requests, python-dotenv (安装：pip install requests python-dotenv)
# 使用说明：1. 本地创建.mcp_env配置令牌；2. 确保目标分支存在；3. 直接运行脚本
# =============================================================================

import sys
import os
import requests
import base64
import re
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv


# -----------------------------
# 1) 配置（基于模板填充实际值）
# -----------------------------
CONFIG = {
    # 环境配置
    "ENV_CONFIG": {
        "github_token_var": "MCP_GITHUB_TOKEN",
        "github_org_var": "GITHUB_EVAL_ORG",
        "env_file": ".mcp_env"
    },

    # GitHub仓库配置
    "REPO_CONFIG": {
        "repo_name": "voxel-engine-docs",  # 实际仓库名（可后续修改）
        "target_branch": "main",           # 实际目标分支
        "api_version": "v3",
        "timeout": 10
    },

    # 验证目标文件配置
    "FILES_TO_VERIFY": {
        # 答案文件配置
        "answer_file": {
            "path": "ANSWER.md",
            "must_exist": True,
            "encoding": "utf-8",
            "content_schema": {
                "format": "date",
                "pattern": r'^\d{4}-\d{2}-\d{2}$',
                "expected_value": "2023-11-15"  # 实际提交日期（可后续修改）
            }
        },
        # 参考文件配置
        "reference_file": {
            "path": "README.md",
            "must_exist": True,
            "encoding": "utf-8",
            "content_checks": {
                "required_section": "## Voxel Engine Implementation",  # 实际章节名
                "required_entries": [
                    "C++ Voxel Engine Fundamentals",  # 实际条目1
                    "Vulkan-based Voxel Rendering"     # 实际条目2
                ],
                "check_entries": True
            }
        }
    },

    # 验证流程配置
    "VERIFICATION_FLOW": {
        "check_answer_file_existence": True,
        "check_answer_format": True,
        "verify_answer_value": True,
        "check_reference_file": True,
        "check_section_existence": True,
        "check_required_entries": True
    }
}


# -----------------------------
# 2) 工具函数（与模板一致，未修改）
# -----------------------------
def _load_environment() -> Tuple[Optional[str], Optional[str]]:
    """加载环境变量（从配置的env_file读取）"""
    load_dotenv(CONFIG["ENV_CONFIG"]["env_file"])
    
    # 获取GitHub令牌和组织名
    github_token = os.environ.get(CONFIG["ENV_CONFIG"]["github_token_var"])
    github_org = os.environ.get(CONFIG["ENV_CONFIG"]["github_org_var"])
    
    # 验证环境变量完整性
    if not github_token:
        print(f"❌ 未找到环境变量 {CONFIG['ENV_CONFIG']['github_token_var']}（检查{CONFIG['ENV_CONFIG']['env_file']}）", file=sys.stderr)
    if not github_org:
        print(f"❌ 未找到环境变量 {CONFIG['ENV_CONFIG']['github_org_var']}（检查{CONFIG['ENV_CONFIG']['env_file']}）", file=sys.stderr)
    
    return github_token, github_org


def _build_headers(github_token: str) -> Dict[str, str]:
    """构建GitHub API请求头"""
    return {
        "Authorization": f"Bearer {github_token}",
        "Accept": f"application/vnd.github.{CONFIG['REPO_CONFIG']['api_version']}+json",
        "User-Agent": "voxel-engine-verifier"
    }


def _call_github_api(
    endpoint: str,
    headers: Dict[str, str],
    org: str
) -> Tuple[bool, Optional[Dict]]:
    """调用GitHub API获取数据"""
    repo_name = CONFIG["REPO_CONFIG"]["repo_name"]
    api_url = f"https://api.github.com/repos/{org}/{repo_name}/{endpoint}"
    
    try:
        response = requests.get(
            api_url,
            headers=headers,
            timeout=CONFIG["REPO_CONFIG"]["timeout"]
        )
        
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 404:
            print(f"⚠️ API资源未找到：{endpoint}（404）", file=sys.stderr)
            return False, None
        else:
            print(f"❌ API请求失败：{endpoint}（状态码：{response.status_code}）", file=sys.stderr)
            return False, None
            
    except Exception as e:
        print(f"❌ API调用异常：{endpoint}（错误：{str(e)}）", file=sys.stderr)
        return False, None


def _get_file_content(
    file_path: str,
    headers: Dict[str, str],
    org: str,
    ref: Optional[str] = None
) -> Optional[str]:
    """从GitHub仓库获取文件内容（Base64解码）"""
    # 使用配置的目标分支，允许传入特定分支覆盖
    branch = ref or CONFIG["REPO_CONFIG"]["target_branch"]
    success, file_data = _call_github_api(
        endpoint=f"contents/{file_path}?ref={branch}",
        headers=headers,
        org=org
    )
    
    if not success or not file_data:
        print(f"❌ 未在分支 '{branch}' 找到文件 '{file_path}'", file=sys.stderr)
        return None
    
    # 解码文件内容
    try:
        base64_content = file_data.get("content", "").replace("\n", "")
        return base64.b64decode(base64_content).decode(CONFIG["FILES_TO_VERIFY"]["answer_file"]["encoding"])
    except Exception as e:
        print(f"❌ 文件 '{file_path}' 解码失败（错误：{str(e)}）", file=sys.stderr)
        return None


# -----------------------------
# 3) 核心验证逻辑（与模板一致，未修改）
# -----------------------------
def _verify_answer_file_existence(content: Optional[str]) -> bool:
    """验证答案文件是否存在"""
    if CONFIG["VERIFICATION_FLOW"]["check_answer_file_existence"]:
        if not content:
            print(f"❌ 验证失败：{CONFIG['FILES_TO_VERIFY']['answer_file']['path']} 不存在或无法读取", file=sys.stderr)
            return False
        print(f"✅ 验证通过：{CONFIG['FILES_TO_VERIFY']['answer_file']['path']} 存在")
    return True


def _verify_answer_format(content: str) -> bool:
    """验证答案文件内容格式"""
    if CONFIG["VERIFICATION_FLOW"]["check_answer_format"]:
        pattern = CONFIG["FILES_TO_VERIFY"]["answer_file"]["content_schema"]["pattern"]
        if not re.match(pattern, content.strip()):
            print(f"❌ 验证失败：内容格式不符合要求（预期：{pattern}）", file=sys.stderr)
            return False
        print(f"✅ 验证通过：内容格式正确（匹配 {pattern}）")
    return True


def _verify_answer_value(content: str) -> bool:
    """验证答案文件内容值"""
    if CONFIG["VERIFICATION_FLOW"]["verify_answer_value"]:
        expected = CONFIG["FILES_TO_VERIFY"]["answer_file"]["content_schema"]["expected_value"]
        if content.strip() != expected:
            print(f"❌ 验证失败：内容值不匹配（预期：{expected}，实际：{content.strip()}）", file=sys.stderr)
            return False
        print(f"✅ 验证通过：内容值正确（{expected}）")
    return True


def _verify_reference_file(content: Optional[str]) -> bool:
    """验证参考文件（如README.md）"""
    if CONFIG["VERIFICATION_FLOW"]["check_reference_file"] and not content:
        print(f"❌ 验证失败：{CONFIG['FILES_TO_VERIFY']['reference_file']['path']} 不存在或无法读取", file=sys.stderr)
        return False
    
    if CONFIG["VERIFICATION_FLOW"]["check_reference_file"]:
        print(f"✅ 验证通过：{CONFIG['FILES_TO_VERIFY']['reference_file']['path']} 存在")
    return True


def _verify_required_section(content: str) -> bool:
    """验证参考文件中必需章节是否存在"""
    if CONFIG["VERIFICATION_FLOW"]["check_section_existence"]:
        section = CONFIG["FILES_TO_VERIFY"]["reference_file"]["content_checks"]["required_section"]
        if section not in content:
            print(f"❌ 验证失败：{CONFIG['FILES_TO_VERIFY']['reference_file']['path']} 中未找到 '{section}' 章节", file=sys.stderr)
            return False
        print(f"✅ 验证通过：找到 '{section}' 章节")
    return True


def _verify_required_entries(content: str) -> bool:
    """验证参考文件中必需条目是否存在"""
    if CONFIG["VERIFICATION_FLOW"]["check_required_entries"] and CONFIG["FILES_TO_VERIFY"]["reference_file"]["content_checks"]["check_entries"]:
        entries = CONFIG["FILES_TO_VERIFY"]["reference_file"]["content_checks"]["required_entries"]
        all_present = True
        
        for entry in entries:
            if entry not in content:
                print(f"⚠️ 警告：{CONFIG['FILES_TO_VERIFY']['reference_file']['path']} 中未找到条目 '{entry}'", file=sys.stderr)
                all_present = False
        
        if all_present:
            print(f"✅ 验证通过：所有必需条目均存在（共{len(entries)}条）")
        else:
            print(f"❌ 验证失败：部分必需条目缺失", file=sys.stderr)
            return False
    return True


# -----------------------------
# 4) 主流程控制（与模板一致，未修改）
# -----------------------------
def run_verification() -> bool:
    """执行完整验证流程"""
    print("🔍 开始Voxel Engine提交日期验证流程...")
    print("=" * 60)

    # 步骤1：加载环境配置
    print("\n【步骤1/3】加载环境配置...")
    github_token, github_org = _load_environment()
    if not github_token or not github_org:
        print("❌ 环境配置不完整，终止验证", file=sys.stderr)
        return False
    
    headers = _build_headers(github_token)
    print(f"✅ 环境配置加载完成（组织：{github_org}，仓库：{CONFIG['REPO_CONFIG']['repo_name']}）")

    # 步骤2：验证答案文件
    print("\n【步骤2/3】验证答案文件...")
    answer_content = _get_file_content(
        file_path=CONFIG["FILES_TO_VERIFY"]["answer_file"]["path"],
        headers=headers,
        org=github_org
    )
    
    # 执行答案文件相关验证
    if not all([
        _verify_answer_file_existence(answer_content),
        _verify_answer_format(answer_content) if answer_content else False,
        _verify_answer_value(answer_content) if answer_content else False
    ]):
        print("\n❌ 答案文件验证失败", file=sys.stderr)
        return False

    # 步骤3：验证参考文件
    print("\n【步骤3/3】验证参考文件...")
    reference_content = _get_file_content(
        file_path=CONFIG["FILES_TO_VERIFY"]["reference_file"]["path"],
        headers=headers,
        org=github_org
    )
    
    # 执行参考文件相关验证
    if not all([
        _verify_reference_file(reference_content),
        _verify_required_section(reference_content) if reference_content else False,
        _verify_required_entries(reference_content) if reference_content else False
    ]):
        print("\n❌ 参考文件验证失败", file=sys.stderr)
        return False

    # 所有验证通过
    print("\n" + "=" * 60)
    print("🎉 所有Voxel Engine提交日期验证项通过！")
    print(f"📋 验证汇总：")
    print(f"   - 仓库：{github_org}/{CONFIG['REPO_CONFIG']['repo_name']}")
    print(f"   - 分支：{CONFIG['REPO_CONFIG']['target_branch']}")
    print(f"   - 答案文件：{CONFIG['FILES_TO_VERIFY']['answer_file']['path']}（值：{CONFIG['FILES_TO_VERIFY']['answer_file']['content_schema']['expected_value']}）")
    print(f"   - 参考文件：{CONFIG['FILES_TO_VERIFY']['reference_file']['path']}（章节：{CONFIG['FILES_TO_VERIFY']['reference_file']['content_checks']['required_section']}）")
    print("=" * 60)
    return True


# -----------------------------
# 执行入口
# -----------------------------
if __name__ == "__main__":
    verification_result = run_verification()
    sys.exit(0 if verification_result else 1)
