#!/usr/bin/env python3
"""诊断 NovelOps LLM 配置问题"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("NovelOps LLM 配置诊断工具")
print("=" * 60)

# 1. 检查环境变量
print("\n1. 环境变量检查:")
print(f"  DEEPSEEK_API_KEY: {'SET' if os.getenv('DEEPSEEK_API_KEY') else 'NOT SET'}")
print(f"  RIGHTCODE_API_KEY: {'SET' if os.getenv('RIGHTCODE_API_KEY') else 'NOT SET'}")
print(f"  NOVELOPS_MODEL_CONFIG: {repr(os.getenv('NOVELOPS_MODEL_CONFIG'))}")

# 2. 检查 .env 文件
print("\n2. .env 文件检查:")
project_root = Path(__file__).resolve().parent
env_file = project_root / ".env"
print(f"  .env 路径: {env_file}")
print(f"  .env 存在: {env_file.is_file()}")
if env_file.is_file():
    print(f"  .env 内容预览:")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key = line.split('=')[0].strip()
                print(f"    {key}: SET")

# 3. 检查 models.json
print("\n3. models.json 检查:")
config_dir = project_root / "config"
models_json = config_dir / "models.json"
print(f"  路径: {models_json}")
print(f"  存在: {models_json.is_file()}")
if models_json.is_file():
    import json
    with open(models_json) as f:
        config = json.load(f)
    print(f"  assistant 配置: {config.get('assistant')}")

# 4. 测试配置加载
print("\n4. LLM 配置加载测试:")
try:
    sys.path.insert(0, str(project_root))
    from novelops.llm import settings_for_stage, _config_path
    
    print(f"  配置路径: {_config_path()}")
    
    for stage in ['assistant', 'planner', 'reviewer', 'draft_v1']:
        try:
            s = settings_for_stage(stage)
            key_status = 'SET' if s.resolved_api_key else 'NOT SET'
            print(f"  {stage}: model={s.model}, api_key_env={s.api_key_env}, key={key_status}")
        except Exception as e:
            print(f"  {stage}: ERROR - {e}")
            
except Exception as e:
    print(f"  加载失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 测试实际 LLM 调用
print("\n5. LLM 调用测试 (assistant 阶段):")
try:
    from novelops.llm import LLMClient
    client = LLMClient()
    settings = client.settings_for('assistant')
    print(f"  模型: {settings.model}")
    print(f"  API Key: {'SET' if settings.resolved_api_key else 'NOT SET'}")
    
    if settings.resolved_api_key:
        print("  尝试调用 LLM...")
        result = client.complete_json(
            '{"intent": "status", "project": "life_balance"}',
            system="只返回 JSON",
            stage="assistant",
            schema={"type": "json_object"}
        )
        print(f"  调用成功: {result}")
    else:
        print("  ERROR: API Key 未设置，无法调用")
        
except Exception as e:
    print(f"  调用失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
