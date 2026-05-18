from typing import List, Tuple, Optional, Dict
from utils.logger import get_logger
from utils.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = get_logger()


class Neo4jOperations:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.uri = uri or NEO4J_URI
        self.user = user or NEO4J_USER
        self.password = password or NEO4J_PASSWORD
        self._driver = None
        self._initialized = True
        self._connected = False

    def _get_driver(self):
        if self._driver is not None:
            return self._driver
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            self._driver.verify_connectivity()
            self._connected = True
            logger.info(f"Neo4j连接成功: {self.uri}")
            return self._driver
        except ImportError:
            logger.error("neo4j库未安装, 请执行: pip install neo4j")
            return None
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}")
            self._driver = None
            self._connected = False
            return None

    def test_connection(self) -> Tuple[bool, str]:
        try:
            driver = self._get_driver()
            if driver is None:
                return False, "Neo4j驱动初始化失败"
            with driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()
            return True, "Neo4j连接正常"
        except Exception as e:
            self._connected = False
            return False, f"Neo4j连接失败: {e}"

    def is_connected(self) -> bool:
        if not self._connected:
            _, _ = self.test_connection()
        return self._connected

    def execute_cql(self, cql: str) -> Tuple[bool, str]:
        driver = self._get_driver()
        if driver is None:
            return False, "Neo4j驱动未初始化"
        try:
            with driver.session() as session:
                session.run(cql)
            return True, "CQL执行成功"
        except Exception as e:
            logger.error(f"CQL执行失败: {e}, CQL: {cql[:100]}")
            return False, f"CQL执行失败: {e}"

    def import_triplets(self, triplets: List[Tuple[str, str, str]]) -> Tuple[bool, str, int]:
        if not triplets:
            return False, "无三元组数据", 0
        driver = self._get_driver()
        if driver is None:
            return False, "Neo4j驱动未初始化", 0

        success_count = 0
        fail_count = 0

        for e1, rel, e2 in triplets:
            e1_escaped = e1.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
            e2_escaped = e2.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')

            import re
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', rel):
                rel_type = rel
            else:
                rel_type = f"`{rel}`"

            cql = (
                f"MERGE (a:Entity {{name: '{e1_escaped}'}}) "
                f"MERGE (b:Entity {{name: '{e2_escaped}'}}) "
                f"MERGE (a)-[:{rel_type}]->(b)"
            )
            ok, _ = self.execute_cql(cql)
            if ok:
                success_count += 1
            else:
                fail_count += 1

        msg = f"导入完成: 成功{success_count}条, 失败{fail_count}条"
        logger.info(msg)
        return True, msg, success_count

    def import_cql_script(self, cql_script: str) -> Tuple[bool, str, int]:
        if not cql_script or not cql_script.strip():
            return False, "CQL脚本为空", 0

        statements = []
        for line in cql_script.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            statements.append(line)

        success_count = 0
        fail_count = 0

        for stmt in statements:
            ok, _ = self.execute_cql(stmt)
            if ok:
                success_count += 1
            else:
                fail_count += 1

        msg = f"CQL脚本执行完成: 成功{success_count}条, 失败{fail_count}条"
        logger.info(msg)
        return True, msg, success_count

    def query_all(self) -> List[Dict]:
        driver = self._get_driver()
        if driver is None:
            return []
        try:
            with driver.session() as session:
                result = session.run(
                    "MATCH (a:Entity)-[r]->(b:Entity) "
                    "RETURN a.name AS entity1, type(r) AS relation, b.name AS entity2"
                )
                data = []
                for record in result:
                    data.append({
                        "entity1": record["entity1"],
                        "relation": record["relation"],
                        "entity2": record["entity2"],
                    })
                logger.info(f"查询全量图谱: {len(data)}条关系")
                return data
        except Exception as e:
            logger.error(f"查询全量图谱失败: {e}")
            return []

    def search_by_keyword(self, keyword: str) -> List[Dict]:
        if not keyword:
            return []
        driver = self._get_driver()
        if driver is None:
            return []
        try:
            with driver.session() as session:
                result = session.run(
                    "MATCH (a:Entity)-[r]->(b:Entity) "
                    "WHERE a.name CONTAINS $kw OR b.name CONTAINS $kw "
                    "RETURN a.name AS entity1, type(r) AS relation, b.name AS entity2",
                    kw=keyword,
                )
                data = []
                for record in result:
                    data.append({
                        "entity1": record["entity1"],
                        "relation": record["relation"],
                        "entity2": record["entity2"],
                    })
                logger.info(f"关键词检索'{keyword}': {len(data)}条结果")
                return data
        except Exception as e:
            logger.error(f"关键词检索失败: {e}")
            return []

    def get_node_count(self) -> int:
        driver = self._get_driver()
        if driver is None:
            return 0
        try:
            with driver.session() as session:
                result = session.run("MATCH (n:Entity) RETURN count(n) AS cnt")
                record = result.single()
                return record["cnt"] if record else 0
        except Exception as e:
            logger.error(f"查询节点数失败: {e}")
            return 0

    def get_relation_count(self) -> int:
        driver = self._get_driver()
        if driver is None:
            return 0
        try:
            with driver.session() as session:
                result = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt")
                record = result.single()
                return record["cnt"] if record else 0
        except Exception as e:
            logger.error(f"查询关系数失败: {e}")
            return 0

    def clear_all(self) -> Tuple[bool, str]:
        driver = self._get_driver()
        if driver is None:
            return False, "Neo4j驱动未初始化"
        try:
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            logger.info("Neo4j数据已清空")
            return True, "Neo4j数据已清空"
        except Exception as e:
            logger.error(f"清空Neo4j失败: {e}")
            return False, f"清空失败: {e}"

    def close(self):
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("Neo4j连接已关闭")

    def __del__(self):
        self.close()
