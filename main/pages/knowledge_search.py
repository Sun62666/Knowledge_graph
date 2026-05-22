import os

import streamlit as st
import tempfile
from modules.neo4j_ops.operations import Neo4jOperations
from utils.visualizer import search_knowledge, build_graph_html
from utils.logger import get_logger

logger = get_logger()


def render():
    st.title("🔍 知识检索")
    st.markdown("通过关键词检索实体关系，查看检索结果与图谱可视化")

    neo4j_ops = Neo4jOperations()

    st.markdown("---")
    st.subheader("🔌 数据库状态")

    ok, msg = neo4j_ops.test_connection()
    if ok:
        st.success(f"✅ {msg}")
    else:
        st.error(f"❌ {msg}")
        st.info("请确保Neo4j服务已启动并已导入数据")
        return

    st.markdown("---")
    st.subheader("🔎 关键词检索")

    keyword = st.text_input("输入检索关键词", placeholder="例如：华为、马云、5G...", key="search_input")

    col1, col2 = st.columns([1, 4])
    with col1:
        search_clicked = st.button("🔍 检索", type="primary")

    if search_clicked or (keyword and st.session_state.get("search_input_entered") != keyword):
        if not keyword:
            st.warning("请输入检索关键词")
        else:
            st.session_state["search_keyword"] = keyword
            st.session_state["search_results"] = None
            st.session_state["search_input_entered"] = keyword

    if "search_keyword" in st.session_state and st.session_state["search_keyword"]:
        kw = st.session_state["search_keyword"]

        if st.session_state.get("search_results") is None:
            with st.spinner(f"正在检索 '{kw}'..."):
                results = search_knowledge(kw, neo4j_ops)
                st.session_state["search_results"] = results

        results = st.session_state["search_results"]

        if not results:
            st.warning(f"未找到与 '{kw}' 相关的结果")
        else:
            st.success(f"找到 **{len(results)}** 条相关结果")

            st.markdown("#### 📋 检索结果")
            for i, r in enumerate(results):
                e1 = r.get("entity1", "")
                rel = r.get("relation", "")
                e2 = r.get("entity2", "")
                st.markdown(f"{i+1}. **{e1}** → _{rel}_ → **{e2}**")

            st.markdown("---")
            st.markdown("#### 🌐 检索图谱可视化")

            with st.spinner("正在生成图谱..."):
                html = build_graph_html(results, title=f"检索: {kw}", height="500px")

            if html:
                old_file = st.session_state.get("search_temp_file")
                if old_file and os.path.exists(old_file):
                    try:
                        os.remove(old_file)
                        logger.debug(f"已删除旧临时文件: {old_file}")
                    except Exception as e:
                        logger.warning(f"删除旧临时文件失败: {e}")
                if "search_temp_file" not in st.session_state or st.session_state.get("last_search_kw") != kw:
                    temp_file = tempfile.NamedTemporaryFile(delete=False,suffix=".html",mode="w",encoding="utf-8")
                    temp_file.write(html)
                    temp_file.close()
                    st.session_state["search_temp_file"] = temp_file.name
                    st.session_state["last_search_kw"] = kw
                st.iframe(st.session_state["search_temp_file"], height=700)
            else:
                st.warning("图谱生成失败")

    st.markdown("---")
    st.subheader("💡 检索提示")
    st.markdown("""
    - 支持实体名称模糊匹配（包含关键词即可）
    - 检索结果会自动缓存，相同关键词再次检索速度更快
    - 图谱支持拖拽、缩放、高亮交互
    """)
