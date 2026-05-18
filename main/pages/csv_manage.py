import streamlit as st
from modules.csv_manager.manager import CSVManager
from utils.logger import get_logger

logger = get_logger()


def render():
    st.title("📋 CSV管理")
    st.markdown("查看、编辑、导出三元组数据，生成CQL导入脚本")

    csv_mgr = CSVManager()

    st.markdown("---")
    st.subheader("📊 数据概览")

    df = csv_mgr.read_triplets()
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
            df.iloc[start_idx:end_idx].reset_index(drop=True),
            use_container_width=True,
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
                    csv_mgr.update_triplet(idx, e1, rel, e2)
                    st.success("修改已保存")
                    st.rerun()
        else:
            st.info("暂无数据可编辑")

    with edit_tab2:
        new_e1 = st.text_input("新实体1", key="new_e1")
        new_rel = st.text_input("新关系", key="new_rel")
        new_e2 = st.text_input("新实体2", key="new_e2")
        if st.button("➕ 新增三元组"):
            if new_e1 and new_rel and new_e2:
                csv_mgr.add_triplet(new_e1, new_rel, new_e2)
                st.success("新增成功")
                st.rerun()
            else:
                st.warning("请填写完整的三元组信息")

    with edit_tab3:
        if not df.empty:
            del_idx = st.number_input("删除行号（从0开始）", min_value=0, max_value=len(df)-1, value=0, key="del_idx")
            if st.button("🗑️ 删除该行"):
                csv_mgr.delete_triplet(del_idx)
                st.success("删除成功")
                st.rerun()
        else:
            st.info("暂无数据可删除")

    st.markdown("---")
    st.subheader("🔧 文件操作")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🗑️ 清空CSV"):
            csv_mgr.clear_csv()
            st.success("CSV已清空")
            st.rerun()

    with col2:
        if st.button("📤 导出CSV"):
            export_path = csv_mgr.csv_path.replace(".csv", "_export.csv")
            csv_mgr.export_csv(export_path)
            with open(export_path, "rb") as f:
                st.download_button(
                    "⬇️ 下载CSV文件",
                    data=f.read(),
                    file_name="triplets_export.csv",
                    mime="text/csv",
                )

    with col3:
        if st.button("🔧 生成CQL脚本"):
            cql = csv_mgr.generate_cql()
            if cql:
                st.success("CQL脚本生成成功")
                with st.expander("📄 查看CQL脚本"):
                    st.code(cql[:3000], language="cypher")
                    if len(cql) > 3000:
                        st.info(f"脚本过长，仅展示前3000字符，共{len(cql)}字符")
            else:
                st.warning("无数据可生成CQL")
