"""测试导入是否正常"""

print("测试导入各个模块...")

try:
    import agent
    print("✅ agent.py 导入成功")
except Exception as e:
    print(f"❌ agent.py 导入失败: {e}")

try:
    import experience_rag
    print("✅ experience_rag.py 导入成功")
except Exception as e:
    print(f"❌ experience_rag.py 导入失败: {e}")

try:
    import multi_agent
    print("✅ multi_agent.py 导入成功")
except Exception as e:
    print(f"❌ multi_agent.py 导入失败: {e}")

try:
    import self_diagnosis
    print("✅ self_diagnosis.py 导入成功")
except Exception as e:
    print(f"❌ self_diagnosis.py 导入失败: {e}")

try:
    import self_evolution
    print("✅ self_evolution.py 导入成功")
except Exception as e:
    print(f"❌ self_evolution.py 导入失败: {e}")

try:
    import web_app
    print("✅ web_app.py 导入成功")
except Exception as e:
    print(f"❌ web_app.py 导入失败: {e}")

try:
    import code_pattern_analyzer
    print("✅ code_pattern_analyzer.py 导入成功")
except Exception as e:
    print(f"❌ code_pattern_analyzer.py 导入失败: {e}")

print("\n所有导入测试完成！")
