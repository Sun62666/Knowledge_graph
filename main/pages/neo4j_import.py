import streamlit as st
from modules.neo4j_ops.operations import Neo4jOperations
from modules.csv_manager.manager import CSVManager
from utils.logger import get_logger

logger = get_logger()


def render():
    st.title("🔗 导入Neo4j")
    st.markdown("将三元组数据导入Neo4j图数据库")

    if "neo4j_msg" in st.session_state:
        msg_type, msg_text = st.session_state["neo4j_msg"]
        if msg_type == "success":
            st.success(msg_text, icon="✅")
        elif msg_type == "warning":
            st.warning(msg_text, icon="⚠️")
        elif msg_type == "error":
            st.error(msg_text, icon="❌")
        del st.session_state["neo4j_msg"]

    neo4j_ops = Neo4jOperations()
    csv_mgr = CSVManager()

    st.markdown("---")
    st.subheader("🔌 连接状态")

    ok, msg = neo4j_ops.test_connection()
    if ok:
        st.success(f"✅ {msg}")
    else:
        st.error(f"❌ {msg}")
        st.info("请确保Neo4j服务已启动，并在 utils/config.py 中配置正确的连接信息")

    st.markdown("---")
    st.subheader("📊 数据库状态")

    if ok:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("节点数", neo4j_ops.get_node_count())
        with col2:
            st.metric("关系数", neo4j_ops.get_relation_count())
        with col3:
            rel_types = neo4j_ops.get_relation_types()
            st.metric("关系类型数", len(rel_types))
        if rel_types:
            st.markdown("**关系类型:** " + "、".join(rel_types))

    st.markdown("---")
    st.subheader("📝 CQL脚本预览")

    triplets = csv_mgr.get_triplet_list()

    if not triplets:
        st.warning("CSV中暂无三元组数据，请先在文档抽取页面进行抽取")
        return

    st.info(f"共 **{len(triplets)}** 条三元组待导入")

    with st.expander("📄 查看CQL脚本", expanded=False):
        cql = csv_mgr.generate_cql()
        st.code(cql[:5000], language="cypher")
        if len(cql) > 5000:
            st.info(f"脚本过长，仅展示前5000字符，共{len(cql)}字符")

    st.markdown("---")
    st.subheader("🚀 执行导入")

    import_method = st.radio(
        "导入方式",
        ["批量导入（UNWIND，推荐）", "逐条导入（生成CQL脚本）"],
        help="批量导入使用UNWIND语句，按关系类型分组批量写入，速度远快于逐条执行"
    )

    col_batch1, col_batch2 = st.columns(2)
    with col_batch1:
        batch_size = st.selectbox(
            "批量大小",
            [100, 500, 1000, 2000],
            index=1,
            help="每批次导入的三元组数量，越大速度越快但内存占用越高"
        )
    with col_batch2:
        write_mode = st.radio(
            "写入模式",
            ["增量导入（MERGE，幂等）", "先清空再导入"],
            help="MERGE模式不会创建重复数据；先清空模式会删除所有已有数据再导入"
        )

    if st.button("🚀 开始导入", type="primary", disabled=not ok):
        if not ok:
            st.error("Neo4j连接不可用，请先检查连接")
            return

        if write_mode == "先清空再导入":
            with st.spinner("正在清空Neo4j数据..."):
                neo4j_ops.clear_all()

        total = len(triplets)
        progress_bar = st.progress(0, text=f"准备导入 {total} 条三元组...")

        def on_progress(current, total, success, fail):
            pct = int((current / total) * 100)
            progress_bar.progress(pct, text=f"导入进度: {current}/{total}")

        if import_method == "批量导入（UNWIND，推荐）":
            ok,msg,success_count = neo4j_ops.import_triplets(triplets,batch_size,progress_callback=on_progress)
            st.session_state["neo4j_msg"] = ("success", msg)
            st.rerun()

        else:
            cql = csv_mgr.generate_cql()
            ok,msg,success_count = neo4j_ops.import_cql_script(cql,progress_callback=on_progress)
            st.session_state["neo4j_msg"] = ("success", msg)
            st.rerun()

    st.markdown("---")
    st.subheader("⚠️ 危险操作")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清空Neo4j所有数据"):
            if "confirm_clear_neo4j" not in st.session_state:
                st.session_state["confirm_clear_neo4j"] = True
                st.warning("⚠️ 再次点击确认清空操作！此操作不可恢复！")
            else:
                ok_clear, msg_clear = neo4j_ops.clear_all()
                del st.session_state["confirm_clear_neo4j"]
                if ok_clear:
                    st.session_state["neo4j_msg"] = ("success", f"{msg_clear}")
                    st.rerun()
                else:
                    st.session_state["neo4j_msg"] = ("error", f"清空失败: {msg_clear}")
                    st.rerun()

    with col2:
        if st.button("🔄 刷新状态"):
            st.rerun()
