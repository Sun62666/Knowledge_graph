from modules.neo4j_ops.operations import Neo4jOperations
from modules.nlp_processor.extractor import MultiTechniqueExtractor
from modules.csv_manager.manager import CSVManager
from utils.cql_utils import escape_relation_type

print("1. Neo4jOperations - OK")
print(f"   escape_relation_type: {escape_relation_type('创建')}")
print(f"   escape_relation_type: {escape_relation_type('FOUNDER')}")

print("2. MultiTechniqueExtractor - OK")
ext = MultiTechniqueExtractor()
result = ext.extract(
    "华为总部位于深圳。任正非创立了华为。",
    techniques=["rule", "template"],
    progress_callback=lambda p, t: print(f"   进度: {p:.0%} - {t}")
)
print(f"   抽取结果: {result}")

print("3. CSVManager - OK")
print("4. All modules imported successfully!")
