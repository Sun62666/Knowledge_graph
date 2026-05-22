import os

import streamlit as st
import tempfile
from modules.neo4j_ops.operations import Neo4jOperations
from utils.visualizer import build_graph_html, clear_cache
from utils.logger import get_logger

logger = get_logger()


def render():
    st.title("🌐 图谱可视化")
    st.markdown("展示Neo4j中的全量知识图谱，支持交互式操作")

    neo4j_ops = Neo4jOperations()

    st.markdown("---")
    st.subheader("🔌 数据库状态")

    ok, msg = neo4j_ops.test_connection()
    if ok:
        st.success(f"✅ {msg}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("节点数", neo4j_ops.get_node_count())
        with col2:
            st.metric("关系数", neo4j_ops.get_relation_count())
    else:
        st.error(f"❌ {msg}")
        st.info("请确保Neo4j服务已启动并已导入数据")
        return

    st.markdown("---")
    st.subheader("🌐 全量图谱")

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("🔄 加载图谱", type="primary"):
            st.session_state["load_graph"] = True
            st.session_state["graph_data"] = None

    with col2:
        if st.button("🗑️ 清除缓存"):
            clear_cache()
            st.session_state["graph_data"] = None
            st.session_state["graph_html_cache"] = None
            st.success("缓存已清除")

    if st.session_state.get("load_graph", False):
        if st.session_state.get("graph_data") is None:
            with st.spinner("正在从Neo4j加载全量图谱数据..."):
                data = neo4j_ops.query_all()
                st.session_state["graph_data"] = data
                st.session_state["graph_html_cache"] = None

        data = st.session_state["graph_data"]

        if not data:
            st.warning("图谱中暂无数据，请先在导入Neo4j页面导入数据")
            return

        st.info(f"共加载 **{len(data)}** 条关系数据")

        with st.expander("📋 查看数据列表", expanded=False):
            for i, r in enumerate(data):
                e1 = r.get("entity1", "")
                rel = r.get("relation", "")
                e2 = r.get("entity2", "")
                st.markdown(f"{i+1}. **{e1}** → _{rel}_ → **{e2}**")

        if st.session_state.get("graph_html_cache") is None:
            with st.spinner("正在生成交互式图谱..."):
                html = build_graph_html(data, title="企业知识图谱", height="650px")
                st.session_state["graph_html_cache"] = html
        else:
            html = st.session_state["graph_html_cache"]

        if html:
            old_file = st.session_state.get("graph_temp_file")
            if old_file and os.path.exists(old_file):
                try:
                    os.remove(old_file)
                    logger.debug(f"已删除旧临时文件: {old_file}")
                except Exception as e:
                    logger.warning(f"删除旧临时文件失败: {e}")
            if "graph_temp_file" not in st.session_state:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
                temp_file.write(html)
                temp_file.close()
                st.session_state["graph_temp_file"] = temp_file.name
            st.iframe(st.session_state["graph_temp_file"], height=700)
            st.caption("💡 图谱支持拖拽、缩放、高亮节点，点击节点可查看关联关系")
        else:
            st.error("图谱生成失败")

    st.markdown("---")
    st.subheader("📖 使用说明")
    st.markdown("""
    - 🖱️ **拖拽**：按住节点拖动调整位置
    - 🔍 **缩放**：鼠标滚轮缩放图谱
    - ✨ **高亮**：悬停节点高亮关联关系
    - 📌 **固定**：双击节点固定/释放位置
    - 🧭 **导航**：使用右下角导航按钮控制视图
    """)
