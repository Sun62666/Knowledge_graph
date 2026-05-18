import streamlit as st
from modules.file_parser.parser import parse_uploaded_file
from modules.nlp_processor.extractor import MultiTechniqueExtractor
from modules.csv_manager.manager import CSVManager
from utils.logger import get_logger
from utils.config import SUPPORTED_FILE_TYPES

logger = get_logger()


def render():
    st.title("📄 文档抽取")
    st.markdown("上传企业文档，自动解析并抽取实体关系三元组")

    st.markdown("---")

    st.subheader("📤 文件上传")
    uploaded_file = st.file_uploader(
        "选择文件",
        type=SUPPORTED_FILE_TYPES,
        help=f"支持格式: {', '.join(SUPPORTED_FILE_TYPES)}",
    )

    if uploaded_file is not None:
        st.info(f"已选择文件: **{uploaded_file.name}** ({uploaded_file.size} bytes)")

    st.markdown("---")
    st.subheader("⚙️ 抽取配置")

    col1, col2 = st.columns(2)
    with col1:
        techniques = st.multiselect(
            "选择抽取技术",
            [
                "rule:规则抽取",
                "template:模板抽取",
                "traditional_ml:传统ML",
                "deep_learning:深度学习",
                "pretrained_model:预训练模型",
                "llm_zero_shot:LLM零样本",
                "llm_few_shot:LLM少样本",
                "remote_supervision:远程监督",
                "knowledge_distillation:知识蒸馏",
                "joint_extraction:联合抽取",
            ],
            default=["rule:规则抽取", "template:模板抽取", "llm_zero_shot:LLM零样本"],
        )
    with col2:
        write_mode = st.radio("CSV写入模式", ["覆盖写入", "增量追加"], index=1)

    if st.button("🚀 开始抽取", type="primary", disabled=uploaded_file is None):
        if uploaded_file is None:
            st.warning("请先上传文件")
            return

        with st.spinner("正在解析文档..."):
            text = parse_uploaded_file(uploaded_file)

        if not text or not text.strip():
            st.error("文档解析结果为空，请检查文件内容")
            return

        st.success(f"文档解析完成，文本长度: {len(text)} 字符")

        with st.expander("📖 查看解析文本", expanded=False):
            st.text_area("解析结果", text[:5000], height=300, disabled=True)

        selected_techniques = [t.split(":")[0] for t in techniques]

        progress_text = "正在进行多技术融合关系抽取..."
        progress_bar = st.progress(0, text=progress_text)

        extractor = MultiTechniqueExtractor()
        progress_bar.progress(30, text="规则/模板抽取中...")

        triplets = extractor.extract(text, techniques=selected_techniques)
        progress_bar.progress(80, text="结果清洗与合并中...")

        if not triplets:
            st.warning("未抽取到任何三元组，请尝试更换抽取技术或检查文档内容")
            progress_bar.empty()
            return

        csv_mgr = CSVManager()
        mode = "append" if write_mode == "增量追加" else "overwrite"
        csv_mgr.write_triplets(triplets, mode=mode)
        progress_bar.progress(100, text="抽取完成！")

        st.success(f"✅ 抽取完成！共获得 **{len(triplets)}** 个三元组")

        stats = extractor.get_stats()
        if stats:
            st.markdown("#### 📊 各技术抽取统计")
            stat_cols = st.columns(min(len(stats), 5))
            for i, (tech, count) in enumerate(stats.items()):
                with stat_cols[i % len(stat_cols)]:
                    st.metric(tech, f"{count}个")

        with st.expander("📋 三元组预览", expanded=True):
            for i, (e1, rel, e2) in enumerate(triplets[:50]):
                st.markdown(f"{i+1}. **{e1}** → _{rel}_ → **{e2}**")
            if len(triplets) > 50:
                st.info(f"仅展示前50条，共{len(triplets)}条")
