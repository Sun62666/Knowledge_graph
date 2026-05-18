import streamlit as st
from modules.neo4j_ops.operations import Neo4jOperations
from modules.csv_manager.manager import CSVManager
from utils.logger import get_logger

logger = get_logger()


def render():
    st.title("🔗 导入Neo4j")
    st.markdown("将三元组数据导入Neo4j图数据库")

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
        col1, col2 = st.columns(2)
        with col1:
            node_count = neo4j_ops.get_node_count()
            st.metric("节点数", node_count)
        with col2:
            rel_count = neo4j_ops.get_relation_count()
            st.metric("关系数", rel_count)

    st.markdown("---")
    st.subheader("📝 CQL脚本预览")

    cql = csv_mgr.generate_cql()
    triplets = csv_mgr.get_triplet_list()

    if not triplets:
        st.warning("CSV中暂无三元组数据，请先在文档抽取页面进行抽取")
        return

    st.info(f"共 {len(triplets)} 条CQL语句待执行")

    with st.expander("📄 查看CQL脚本", expanded=False):
        st.code(cql[:5000], language="cypher")
        if len(cql) > 5000:
            st.info(f"脚本过长，仅展示前5000字符，共{len(cql)}字符")

    st.markdown("---")
    st.subheader("🚀 执行导入")

    import_method = st.radio("导入方式", ["从CSV三元组直接导入", "从CQL脚本文件导入"])

    if st.button("🚀 开始导入", type="primary", disabled=not ok):
        if not ok:
            st.error("Neo4j连接不可用，请先检查连接")
            return

        with st.spinner("正在导入数据到Neo4j..."):
            if import_method == "从CSV三元组直接导入":
                success, msg, count = neo4j_ops.import_triplets(triplets)
            else:
                success, msg, count = neo4j_ops.import_cql_script(cql)

        if success:
            st.success(f"✅ {msg}")
            st.balloons()
        else:
            st.error(f"❌ {msg}")

    st.markdown("---")
    st.subheader("⚠️ 危险操作")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清空Neo4j所有数据", type="secondary"):
            ok_clear, msg_clear = neo4j_ops.clear_all()
            if ok_clear:
                st.success(msg_clear)
            else:
                st.error(msg_clear)

    with col2:
        if st.button("🔄 刷新状态"):
            st.rerun()
