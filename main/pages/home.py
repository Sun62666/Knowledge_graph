import streamlit as st
from utils.config import NEO4J_URI, NEO4J_USER, LLM_MODEL_NAME, LLM_BASE_URL, CSV_FILE_PATH
from modules.neo4j_ops.operations import Neo4jOperations
from modules.csv_manager.manager import CSVManager
import os


def render():
    st.title("🏢 企业知识图谱平台")
    st.markdown("---")

    st.markdown("""
    ### 📖 平台简介
    本平台基于 **Python + LLM + Neo4j + CSV** 技术栈构建，整合全品类关系抽取技术，
    实现从文档解析、多技术关系抽取、CSV中间层存储、Neo4j图数据库构建到交互式可视化检索的全流程自动化。

    #### 🎯 核心能力
    - 📄 **文档解析**：支持PDF、DOCX、TXT格式文档上传与解析
    - 🧠 **多技术融合抽取**：整合规则、模板、ML、深度学习、预训练模型、LLM等9种关系抽取技术
    - 💾 **CSV中间层**：三元组数据可预览、编辑、导出，数据可追溯
    - 🔗 **Neo4j图谱构建**：一键导入图数据库，支持幂等性操作
    - 🔍 **知识检索**：关键词模糊检索，结果缓存加速
    - 🌐 **交互式可视化**：支持拖拽、缩放、高亮的图谱展示
    """)

    st.markdown("---")
    st.subheader("🔌 系统连接状态")

    col1, col2, col3 = st.columns(3)

    with col1:
        neo4j_ops = Neo4jOperations()
        ok, msg = neo4j_ops.test_connection()
        if ok:
            st.success(f"✅ Neo4j\n{NEO4J_URI}")
        else:
            st.error(f"❌ Neo4j\n{msg}")

    with col2:
        csv_mgr = CSVManager()
        if os.path.exists(csv_mgr.csv_path):
            df = csv_mgr.read_triplets()
            st.info(f"📋 CSV数据\n{len(df)}条三元组")
        else:
            st.warning("📋 CSV数据\n文件未创建")

    with col3:
        from utils.config import LLM_API_KEY
        if LLM_API_KEY and LLM_API_KEY != "your_api_key":
            st.success(f"🤖 LLM模型\n{LLM_MODEL_NAME}")
        else:
            st.warning("🤖 LLM模型\nAPI密钥未配置")

    st.markdown("---")
    st.markdown("""
    #### 🚀 快速开始
    1. 📄 在 **文档抽取** 页面上传文档，进行知识抽取
    2. 📋 在 **CSV管理** 页面查看、编辑三元组数据
    3. 🔗 在 **导入Neo4j** 页面将数据导入图数据库
    4. 🔍 在 **知识检索** 页面进行关键词检索
    5. 🌐 在 **图谱可视化** 页面查看交互式图谱
    """)
