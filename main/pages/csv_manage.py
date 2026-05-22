import streamlit as st
import os
import hashlib
import pandas as pd
from modules.csv_manager.manager import CSVManager
from utils.logger import get_logger
from utils.config import CSV_FILE_PATH

logger = get_logger()


@st.cache_data(ttl=300, show_spinner="加载CSV数据...")
def _cached_read_csv(csv_path: str, _file_hash: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        return pd.DataFrame(columns=["实体1", "关系", "实体2"])
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        df = df.dropna(subset=["实体1", "关系", "实体2"])
        return df
    except Exception as e:
        logger.error(f"CSV读取失败: {e}")
        return pd.DataFrame(columns=["实体1", "关系", "实体2"])


def _get_file_hash(path: str) -> str:
    if not os.path.exists(path):
        return ""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_data(csv_path: str) -> pd.DataFrame:
    file_hash = _get_file_hash(csv_path)
    return _cached_read_csv(csv_path, file_hash)


def _invalidate_cache():
    CSVManager.invalidate_cache()


def render():
    st.title("📋 CSV管理")
    st.markdown("查看、编辑、导出三元组数据，生成CQL导入脚本")

    if "csv_msg" in st.session_state:
        msg_type, msg_text = st.session_state["csv_msg"]
        if msg_type == "success":
            st.success(msg_text, icon="✅")
        elif msg_type == "warning":
            st.warning(msg_text, icon="⚠️")
        elif msg_type == "error":
            st.error(msg_text, icon="❌")
        del st.session_state["csv_msg"]

    csv_mgr = CSVManager()

    st.markdown("---")
    st.subheader("📊 数据概览")

    df = _load_data(csv_mgr.csv_path)
    stats = csv_mgr.get_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("三元组总数", stats["total"])
    with col2:
        st.metric("实体数", stats["entities"])
    with col3:
        st.metric("关系数", stats["relations"])
    with col4:
        st.metric("关系类型数", len(stats.get("relation_types", [])))

    if stats.get("relation_types"):
        st.markdown("**关系类型分布:** " + "、".join(stats["relation_types"]))

    st.markdown("---")
    st.subheader("📋 数据表格")

    if df.empty:
        st.info("暂无数据，请先在文档抽取页面上传文档进行抽取")
    else:
        page_size = 20
        total_pages = (len(df) - 1) // page_size + 1
        page = st.number_input("页码", min_value=1, max_value=total_pages, value=1)
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, len(df))

        st.dataframe(
            df.iloc[start_idx:end_idx],
            width='stretch',
            height=400,
        )
        st.caption(f"显示第 {start_idx+1}-{end_idx} 条，共 {len(df)} 条")

    st.markdown("---")
    st.subheader("✏️ 数据编辑")

    edit_tab1, edit_tab2, edit_tab3 = st.tabs(["修改", "新增", "删除"])

    with edit_tab1:
        if not df.empty:
            idx = st.number_input("选择行号（从0开始）", min_value=0, max_value=len(df)-1, value=0)
            if idx < len(df):
                e1 = st.text_input("实体1", value=str(df.iloc[idx]["实体1"]))
                rel = st.text_input("关系", value=str(df.iloc[idx]["关系"]))
                e2 = st.text_input("实体2", value=str(df.iloc[idx]["实体2"]))
                if st.button("💾 保存修改"):
                    if e1 and rel and e2:
                        csv_mgr.update_triplet(idx, e1, rel, e2)
                        st.session_state["csv_msg"] = ("success", f"修改成功！第{idx}行已更新为：{e1} → {rel} → {e2}")
                        st.rerun()
                    else:
                        st.warning("实体1、关系、实体2不能为空")
        else:
            st.info("暂无数据可编辑")

    with edit_tab2:
        new_e1 = st.text_input("新实体1", key="new_e1")
        new_rel = st.text_input("新关系", key="new_rel")
        new_e2 = st.text_input("新实体2", key="new_e2")
        if st.button("➕ 新增三元组"):
            if new_e1 and new_rel and new_e2:
                csv_mgr.add_triplet(new_e1, new_rel, new_e2)
                st.session_state["csv_msg"] = ("success", f"新增成功！{new_e1} → {new_rel} → {new_e2}")
                st.rerun()
            else:
                st.warning("请填写完整的三元组信息")

    with edit_tab3:
        if not df.empty:
            del_idx = st.number_input("删除行号（从0开始）", min_value=0, max_value=len(df)-1, value=0, key="del_idx")
            if del_idx < len(df):
                row = df.iloc[del_idx]
                st.caption(f"将删除：{row['实体1']} → {row['关系']} → {row['实体2']}")
            if st.button("🗑️ 删除该行"):
                if del_idx < len(df):
                    row = df.iloc[del_idx]
                    csv_mgr.delete_triplet(del_idx)
                    st.session_state["csv_msg"] = ("success", f"删除成功！已移除：{row['实体1']} → {row['关系']} → {row['实体2']}")
                    st.rerun()
                else:
                    st.warning("行号超出范围")
        else:
            st.info("暂无数据可删除")

    st.markdown("---")
    st.subheader("🔧 文件操作")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🗑️ 清空CSV"):
            csv_mgr.clear_csv()
            st.session_state["csv_msg"] = ("success", "CSV已清空，所有三元组数据已移除")
            st.rerun()

    with col2:
        if st.button("📤 导出CSV"):
            export_path = csv_mgr.csv_path.replace(".csv", "_export.csv")
            csv_mgr.export_csv(export_path)
            if os.path.exists(export_path):
                with open(export_path, "rb") as f:
                    st.download_button(
                        "⬇️ 下载CSV文件",
                        data=f.read(),
                        file_name="triplets_export.csv",
                        mime="text/csv",
                    )
                st.session_state["csv_msg"] = ("success", f"导出成功！文件已保存至 {export_path}")
            else:
                st.session_state["csv_msg"] = ("warning", "导出失败，CSV无数据")
                st.rerun()

    with col3:
        if st.button("🔧 生成CQL脚本"):
            cql = csv_mgr.generate_cql()
            if cql:
                st.session_state["csv_msg"] = ("success", f"CQL脚本生成成功！共{len(csv_mgr.get_triplet_list())}条语句")
                st.session_state["cql_display"] = True
                st.session_state["cql"] = cql
                st.rerun()
            else:
                st.session_state["csv_msg"] = ("warning", "无数据可生成CQL")
                st.rerun()

    if "cql_display" not in st.session_state:
        st.session_state["cql_display"] = False

    if st.session_state["cql_display"]:
        cql = st.session_state.get("cql")
        if cql:
            with st.expander("📄 查看CQL脚本", expanded=True):
                st.code(cql[:3000], language="cypher")
                if len(cql) > 3000:
                    st.info(f"脚本过长，仅展示前3000字符，共{len(cql)}字符")
        st.session_state["cql_display"] = False

