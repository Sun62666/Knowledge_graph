import streamlit as st
import os
from utils.config import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
    LLM_API_KEY, LLM_MODEL_NAME, LLM_BASE_URL,
    CSV_FILE_PATH, CQL_FILE_PATH, LOG_FILE_PATH,
    DATA_DIR, CACHE_DIR, SUPPORTED_FILE_TYPES,
    CHUNK_SIZE, CHUNK_OVERLAP, MAX_TEXT_LENGTH,
)
from modules.neo4j_ops.operations import Neo4jOperations
from modules.csv_manager.manager import CSVManager
from utils.visualizer import clear_cache
from utils.logger import get_logger

logger = get_logger()


def render():
    st.title("⚙️ 系统管理")
    st.markdown("查看系统配置、运行日志，执行系统重置")

    st.markdown("---")
    st.subheader("📋 配置参数")

    config_tab1, config_tab2, config_tab3 = st.tabs(["Neo4j配置", "LLM配置", "路径配置"])

    with config_tab1:
        st.code(f"URI: {NEO4J_URI}\n用户: {NEO4J_USER}\n密码: {'*' * len(NEO4J_PASSWORD)}")

    with config_tab2:
        masked_key = LLM_API_KEY[:8] + "..." if LLM_API_KEY and LLM_API_KEY != "your_api_key" else "未配置"
        st.code(f"API密钥: {masked_key}\n模型: {LLM_MODEL_NAME}\nBase URL: {LLM_BASE_URL}")

    with config_tab3:
        st.code(
            f"数据目录: {DATA_DIR}\n"
            f"CSV文件: {CSV_FILE_PATH}\n"
            f"CQL文件: {CQL_FILE_PATH}\n"
            f"日志文件: {LOG_FILE_PATH}\n"
            f"缓存目录: {CACHE_DIR}\n"
            f"支持格式: {SUPPORTED_FILE_TYPES}\n"
            f"分片大小: {CHUNK_SIZE}\n"
            f"分片重叠: {CHUNK_OVERLAP}\n"
            f"最大文本长度: {MAX_TEXT_LENGTH}"
        )

    st.markdown("---")
    st.subheader("📝 运行日志")

    if os.path.exists(LOG_FILE_PATH):
        try:
            with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
                log_content = f.read()
            log_lines = log_content.strip().split("\n")
            total_lines = len(log_lines)
            show_lines = st.slider("显示行数", 10, min(500, total_lines), min(100, total_lines))

            display_lines = log_lines[-show_lines:]
            st.code("\n".join(display_lines), language="log")
            st.caption(f"显示最近 {show_lines} 行，共 {total_lines} 行")
        except Exception as e:
            st.error(f"日志读取失败: {e}")
    else:
        st.info("暂无日志文件")

    st.markdown("---")
    st.subheader("🔄 系统重置")

    st.warning("⚠️ 以下操作不可恢复，请谨慎执行！")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🗑️ 清空CSV数据"):
            csv_mgr = CSVManager()
            csv_mgr.clear_csv()
            st.success("CSV数据已清空")

    with col2:
        if st.button("🗑️ 清空Neo4j数据"):
            neo4j_ops = Neo4jOperations()
            ok, msg = neo4j_ops.clear_all()
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    with col3:
        if st.button("🗑️ 清除所有缓存"):
            clear_cache()
            st.success("缓存已清除")

    if st.button("🔴 全部重置（CSV + Neo4j + 缓存）", type="secondary"):
        csv_mgr = CSVManager()
        csv_mgr.clear_csv()
        neo4j_ops = Neo4jOperations()
        neo4j_ops.clear_all()
        clear_cache()
        st.success("系统已全部重置")
