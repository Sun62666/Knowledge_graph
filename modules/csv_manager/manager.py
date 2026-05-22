import os
import traceback

import pandas as pd
from typing import List, Tuple, Optional
from utils.logger import get_logger
from utils.config import CSV_FILE_PATH, CQL_FILE_PATH
from utils.cql_utils import escape_cql_value, escape_relation_type

logger = get_logger()


class CSVManager:
    def __init__(self, csv_path: str = None, cql_path: str = None):
        self.csv_path = csv_path or CSV_FILE_PATH
        self.cql_path = cql_path or CQL_FILE_PATH
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)

    @staticmethod
    def invalidate_cache():
        try:
            from main.pages.csv_manage import _cached_read_csv
            _cached_read_csv.clear()
            logger.info("CSV缓存已清除")
        except Exception as e:
            logger.warning(f"清除CSV缓存失败: {e}")

    def write_triplets(self, triplets: List[Tuple[str, str, str]], mode: str = "overwrite"):
        if not triplets:
            logger.warning("无三元组数据可写入")
            return
        df_new = pd.DataFrame(triplets, columns=["实体1", "关系", "实体2"])
        if mode == "append" and os.path.exists(self.csv_path):
            try:
                df_existing = pd.read_csv(self.csv_path, encoding="utf-8-sig")
                df_new = pd.concat([df_existing, df_new], ignore_index=True)
                df_new = df_new.drop_duplicates(subset=["实体1", "关系", "实体2"], keep="first")
            except Exception as e:
                logger.warning(f"读取已有CSV失败, 将覆盖写入: {e}")
        df_new.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"CSV写入完成: {self.csv_path}, 共{len(df_new)}条记录")
        self.invalidate_cache()

    def read_triplets(self) -> pd.DataFrame:
        if not os.path.exists(self.csv_path):
            logger.warning(f"CSV文件不存在: {self.csv_path}")
            return pd.DataFrame(columns=["实体1", "关系", "实体2"])
        try:
            df = pd.read_csv(self.csv_path, encoding="utf-8-sig")
            df = df.dropna(subset=["实体1", "关系", "实体2"])
            return df
        except Exception as e:
            logger.error(f"CSV读取失败: {e}")
            return pd.DataFrame(columns=["实体1", "关系", "实体2"])

    def get_triplet_list(self) -> List[Tuple[str, str, str]]:
        df = self.read_triplets()
        if df.empty:
            return []
        return list(df.itertuples(index=False, name=None))

    def update_triplet(self, index: int, e1: str, rel: str, e2: str):
        df = self.read_triplets()
        if index < 0 or index >= len(df):
            logger.error(f"索引超出范围: {index}")
            return
        df.at[index, "实体1"] = e1
        df.at[index, "关系"] = rel
        df.at[index, "实体2"] = e2
        df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"CSV更新第{index}行: [{e1}, {rel}, {e2}]")
        self.invalidate_cache()

    def delete_triplet(self, index: int):
        df = self.read_triplets()
        if index < 0 or index >= len(df):
            logger.error(f"索引超出范围: {index}")
            return
        df = df.drop(index).reset_index(drop=True)
        df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"CSV删除第{index}行")
        self.invalidate_cache()

    def add_triplet(self, e1: str, rel: str, e2: str):
        df = self.read_triplets()
        new_row = pd.DataFrame([[e1, rel, e2]], columns=["实体1", "关系", "实体2"])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"CSV新增三元组: [{e1}, {rel}, {e2}]")
        self.invalidate_cache()

    def clear_csv(self):
        df = pd.DataFrame(columns=["实体1", "关系", "实体2"])
        df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
        logger.info("CSV已清空")
        self.invalidate_cache()

    def export_csv(self, export_path: str):
        df = self.read_triplets()
        if df.empty:
            logger.warning("CSV无数据可导出")
            return
        df.to_csv(export_path, index=False, encoding="utf-8-sig")
        logger.info(f"CSV导出完成: {export_path}")

    def generate_cql(self) -> str:
        triplets = self.get_triplet_list()
        # logger.info(f"【调用栈】{traceback.format_stack()}")
        if not triplets:
            logger.warning("无三元组数据, 无法生成CQL")
            return ""
        cql_lines = []
        cql_lines.append("// 企业知识图谱CQL导入脚本")
        cql_lines.append("// 自动生成，请勿手动修改")
        cql_lines.append("")
        for e1, rel, e2 in triplets:
            e1_escaped = escape_cql_value(str(e1))
            e2_escaped = escape_cql_value(str(e2))
            rel_escaped = escape_relation_type(str(rel))
            cql = (
                f"MERGE (a:Entity {{name: '{e1_escaped}'}}) "
                f"MERGE (b:Entity {{name: '{e2_escaped}'}}) "
                f"MERGE (a)-[:{rel_escaped}]->(b);"
            )
            cql_lines.append(cql)
        cql_script = "\n".join(cql_lines)
        os.makedirs(os.path.dirname(self.cql_path), exist_ok=True)
        with open(self.cql_path, "w", encoding="utf-8") as f:
            f.write(cql_script)
        logger.info(f"CQL脚本生成完成: {self.cql_path}, 共{len(triplets)}条语句")
        return cql_script

    def get_stats(self) -> dict:
        df = self.read_triplets()
        if df.empty:
            return {"total": 0, "entities": 0, "relations": 0, "relation_types": []}
        all_entities = set(df["实体1"].tolist() + df["实体2"].tolist())
        relation_types = df["关系"].unique().tolist()
        return {
            "total": len(df),
            "entities": len(all_entities),
            "relations": len(df),
            "relation_types": relation_types,
        }
