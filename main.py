import streamlit as st
from main.pages import home, doc_extract, csv_manage, neo4j_import, knowledge_search, graph_visual, system_admin
import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(
    page_title="企业知识图谱平台",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = {
    "🏠 首页": home,
    "📄 文档抽取": doc_extract,
    "📋 CSV管理": csv_manage,
    "🔗 导入Neo4j": neo4j_import,
    "🔍 知识检索": knowledge_search,
    "🌐 图谱可视化": graph_visual,
    "⚙️ 系统管理": system_admin,
}

with st.sidebar:
    st.title("🏢 知识图谱平台")
    st.markdown("---")
    page_name = st.radio("导航菜单", list(PAGES.keys()), label_visibility="collapsed")
    st.markdown("---")
    st.caption("企业知识图谱平台 v1.0")
    st.caption("Python + LLM + Neo4j + CSV")

page_module = PAGES[page_name]
page_module.render()
