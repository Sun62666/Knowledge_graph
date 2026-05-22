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


def _read_tail_lines(file_path: str, max_lines: int = 2000):
    with open(file_path, "r", encoding="utf-8") as f:
        f.seek(0, 2)
        file_size = f.tell()
        buf_size = min(file_size, 65536)
        f.seek(max(0, file_size - buf_size))
        tail = f.read().strip().split("\n")
        if len(tail) > max_lines:
            tail = tail[-max_lines:]
        return tail


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
            log_lines = _read_tail_lines(LOG_FILE_PATH, 2000)
            total_lines = len(log_lines)
            show_lines = st.slider("显示行数", 10, min(500, total_lines), min(100, total_lines))
            display_lines = log_lines[-show_lines:]
            st.code("\n".join(display_lines), language="log")
            st.caption(f"显示最近 {show_lines} 行，共 {total_lines} 行（已读取最后2000行）")
        except Exception as e:
            st.error(f"日志读取失败: {e}")
    else:
        st.info("暂无日志文件")

    st.markdown("---")
    st.subheader("🔄 系统重置")

    if "admin_msg" in st.session_state:
        msg_type, msg_text = st.session_state["admin_msg"]
        if msg_type == "success":
            st.success(msg_text, icon="✅")
        elif msg_type == "warning":
            st.warning(msg_text, icon="⚠️")
        elif msg_type == "error":
            st.error(msg_text, icon="❌")
        del st.session_state["admin_msg"]

    st.warning("⚠️ 以下操作不可恢复，请谨慎执行！")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🗑️ 清空CSV数据"):
            if "confirm_clear_csv" not in st.session_state:
                st.session_state["confirm_clear_csv"] = True
                st.warning("⚠️ 再次点击确认清空CSV！")
            else:
                csv_mgr = CSVManager()
                csv_mgr.clear_csv()
                del st.session_state["confirm_clear_csv"]
                st.session_state["admin_msg"] = ("success", "CSV数据已清空")
                st.rerun()

    with col2:
        if st.button("🗑️ 清空Neo4j数据"):
            if "confirm_clear_neo4j" not in st.session_state:
                st.session_state["confirm_clear_neo4j"] = True
                st.warning("⚠️ 再次点击确认清空Neo4j！")
            else:
                neo4j_ops = Neo4jOperations()
                ok, msg = neo4j_ops.clear_all()
                del st.session_state["confirm_clear_neo4j"]
                if ok:
                    st.session_state["admin_msg"] = ("success", "Neo4j数据已清空")
                else:
                    st.session_state["admin_msg"] = ("error", f"清空失败: {msg}")
                st.rerun()

    with col3:
        if st.button("🗑️ 清除所有缓存"):
            clear_cache()
            st.session_state["admin_msg"] = ("success", "缓存已清除")
            st.rerun()

    if st.button("🔴 全部重置（CSV + Neo4j + 缓存）"):
        if "confirm_reset_all" not in st.session_state:
            st.session_state["confirm_reset_all"] = True
            st.warning("⚠️ 再次点击确认全部重置！此操作将清空所有数据！")
        else:
            csv_mgr = CSVManager()
            csv_mgr.clear_csv()
            neo4j_ops = Neo4jOperations()
            neo4j_ops.clear_all()
            clear_cache()
            del st.session_state["confirm_reset_all"]
            st.session_state["admin_msg"] = ("success", "系统已全部重置")
            st.rerun()
