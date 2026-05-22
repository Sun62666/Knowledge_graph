from utils.cql_utils import escape_cql_value, escape_relation_type
from modules.csv_manager.manager import CSVManager
from modules.neo4j_ops.operations import Neo4jOperations
from utils.config import EXTRACTION_PRIORITY

print("1. CQL工具测试:")
print(f"  escape_cql_value: {escape_cql_value('test')}")
print(f"  escape_relation_type('创建'): {escape_relation_type('创建')}")
print(f"  escape_relation_type('FOUNDER'): {escape_relation_type('FOUNDER')}")

print("\n2. CSVManager:")
mgr = CSVManager()
print(f"  CSV路径: {mgr.csv_path}")

print("\n3. Neo4jOperations 单例:")
n1 = Neo4jOperations()
n2 = Neo4jOperations()
print(f"  同一个实例: {n1 is n2}")

print("\n4. EXTRACTION_PRIORITY:")
print(f"  {EXTRACTION_PRIORITY}")

print("\n=== 全部通过 ===")