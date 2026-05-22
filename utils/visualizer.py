import os
import hashlib
import json
from typing import List, Dict, Tuple, Optional
from utils.logger import get_logger
from utils.config import CACHE_DIR

logger = get_logger()


def _data_hash(data) -> str:
    data_str = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(data_str.encode("utf-8")).hexdigest()[:12]


def _get_cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"graph_{key}.html")


def _get_search_cache_path(keyword: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    kw_hash = hashlib.md5(keyword.encode("utf-8")).hexdigest()[:12]
    return os.path.join(CACHE_DIR, f"search_{kw_hash}.json")


def search_knowledge(keyword: str, neo4j_ops) -> List[Dict]:
    if not keyword:
        return []
    cache_path = _get_search_cache_path(keyword)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            logger.info(f"检索结果缓存命中: {keyword}")
            return cached
        except Exception:
            pass
    results = neo4j_ops.search_by_keyword(keyword)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"检索结果缓存写入失败: {e}")
    return results


def build_graph_html(triplets: List[Dict], title: str = "知识图谱", height: str = "600px") -> str:
    if not triplets:
        return "<div style='text-align:center;padding:50px;color:#999;'>暂无图谱数据</div>"

    data_hash = _data_hash(triplets)
    cache_path = _get_cache_path(data_hash)
    if os.path.exists(cache_path):
        logger.info(f"图谱可视化缓存命中: {data_hash}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    try:
        import networkx as nx  # 图论与网络分析库（图数据结构，图算法，图分析）
        from pyvis.network import Network # 交互式图可视化库（交互式可视化，力导向布局，生成html，基于vis.js）
    except ImportError:
        logger.error("networkx或pyvis未安装, 请执行: pip install networkx pyvis")
        return "<div style='text-align:center;padding:50px;color:red;'>可视化依赖未安装</div>"

    G = nx.DiGraph()
    for t in triplets:
        e1 = t.get("entity1", t.get("实体1", ""))
        rel = t.get("relation", t.get("关系", ""))
        e2 = t.get("entity2", t.get("实体2", ""))
        if not e1 or not e2:
            continue
        G.add_node(e1)
        G.add_node(e2)
        G.add_edge(e1, e2, label=rel, title=rel)

    net = Network(
        height=height,
        width="100%",
        directed=True,  # 有向
        notebook=False,
        bgcolor="#ffffff",
        font_color="#333333",
    )

    net.from_nx(G) # 将networkx的图结构转换为pyvis的节点/边列表

    color_palette = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
        "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
        "#BB8FCE", "#85C1E9", "#F0B27A", "#82E0AA",
    ]

    for i, node in enumerate(net.nodes):
        node["color"] = color_palette[i % len(color_palette)]
        node["size"] = 20
        node["font"] = {"size": 14, "color": "#333333"}
        node["borderWidth"] = 2

    for edge in net.edges:
        edge["color"] = {"color": "#999999", "highlight": "#FF6B6B"}
        edge["width"] = 1.5
        edge["font"] = {"size": 10, "color": "#666666", "align": "middle"}
        edge["arrows"] = "to"
        edge["smooth"] = {"type": "continuous"}

    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "barnesHut": { 
                "gravitationalConstant": -8000,
                "centralGravity": 0.3,
                "springLength": 150,
                "springConstant": 0.04,
                "damping": 0.09
            }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 200,
            "navigationButtons": true,
            "keyboard": true
        },
        "layout": {
            "improvedLayout": true
        }
    }
    """)

    try:
        html = net.generate_html()
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"图谱可视化生成完成: {data_hash}, 节点{G.number_of_nodes()}, 边{G.number_of_edges()}")
        return html
    except Exception as e:
        logger.error(f"图谱可视化生成失败: {e}")
        return f"<div style='text-align:center;padding:50px;color:red;'>可视化生成失败: {e}</div>"


def clear_cache():
    if not os.path.exists(CACHE_DIR):
        return
    for f in os.listdir(CACHE_DIR):
        fp = os.path.join(CACHE_DIR, f)
        if os.path.isfile(fp):
            os.remove(fp)
    logger.info("可视化缓存已清空")
