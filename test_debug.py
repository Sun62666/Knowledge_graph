import sys
import traceback

def test_import(module_name, description):
    try:
        __import__(module_name)
        print(f"  ✅ {description} ({module_name})")
        return True
    except Exception as e:
        print(f"  ❌ {description} ({module_name}): {e}")
        traceback.print_exc()
        return False

print("=== 模块导入测试 ===")
results = []

results.append(test_import("utils.config", "系统配置"))
results.append(test_import("utils.logger", "日志模块"))
results.append(test_import("modules.file_parser.parser", "文档解析"))
results.append(test_import("modules.nlp_processor.extractor", "关系抽取"))
results.append(test_import("modules.csv_manager.manager", "CSV管理"))
results.append(test_import("modules.neo4j_ops.operations", "Neo4j操作"))
results.append(test_import("utils.visualizer", "可视化模块"))

print()
print("=== 页面模块导入测试 ===")
results.append(test_import("main.pages.home", "首页"))
results.append(test_import("main.pages.doc_extract", "文档抽取页"))
results.append(test_import("main.pages.csv_manage", "CSV管理页"))
results.append(test_import("main.pages.neo4j_import", "Neo4j导入页"))
results.append(test_import("main.pages.knowledge_search", "知识检索页"))
results.append(test_import("main.pages.graph_visual", "图谱可视化页"))
results.append(test_import("main.pages.system_admin", "系统管理页"))

print()
passed = sum(results)
total = len(results)
print(f"=== 结果: {passed}/{total} 通过 ===")
