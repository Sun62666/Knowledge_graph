import os
import streamlit as st
from modules.file_parser.parser import parse_uploaded_file
from modules.nlp_processor.extractor import MultiTechniqueExtractor, LLMExtractor
from modules.nlp_processor.validator import TripletValidator
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
        extract_mode = st.radio(
            "抽取模式",
            ["智能模式（推荐）", "自定义模式"],
            index=0,
            help="智能模式：先用快速方法抽取，LLM仅处理未覆盖的片段，节省费用和时间"
        )

        if extract_mode == "自定义模式":
            techniques = st.multiselect(
                "选择抽取技术",
                [
                    "spacy_rule:spaCy+规则",
                    "spacy_template:spaCy+模板",
                    "spacy_dep:spaCy+依存句法",
                    "llm_zero_shot:LLM零样本",
                    "llm_few_shot:LLM少样本",
                ],
                default=["spacy_rule:spaCy+规则", "spacy_dep:spaCy+依存句法", "llm_few_shot:LLM少样本"],
            )
        else:
            techniques = [
                "spacy_rule:spaCy+规则", "spacy_dep:spaCy+依存句法",
                "llm_few_shot:LLM少样本",
            ]

    with col2:
        write_mode = st.radio("CSV写入模式", ["覆盖写入", "增量追加"], index=0)

    use_llm_cache = st.checkbox("启用LLM缓存（相同文本不重复调用，节省费用）", value=True)
    ai_validate = st.checkbox(
        "🤖 AI校验（用LLM验证抽取结果，过滤错误三元组）",
        value=False,
        help="抽取完成后，调用LLM对结果进行校验，过滤实体截断、关系错误、泛实体等问题。会额外消耗一次API调用。"
    )

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
        smart_mode = extract_mode == "智能模式（推荐）"

        progress_bar = st.progress(0, text="准备抽取...")

        def on_progress(pct, text_msg):
            progress_bar.progress(int(pct * 100), text=text_msg)

        extractor = MultiTechniqueExtractor(use_llm_cache=use_llm_cache)
        triplets = extractor.extract(
            text, techniques=selected_techniques,
            progress_callback=on_progress, smart_mode=smart_mode,
            ai_validate=ai_validate
        )

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

        validation_details = extractor.get_validation_details()
        if validation_details:
            st.markdown("#### 🤖 AI校验详情")
            valid_count = sum(1 for d in validation_details if d.get("valid", True))
            invalid_count = len(validation_details) - valid_count
            corrected_count = sum(1 for d in validation_details if d.get("correction"))

            v_cols = st.columns(3)
            with v_cols[0]:
                st.metric("✅ 通过校验", f"{valid_count}个")
            with v_cols[1]:
                st.metric("❌ 校验失败", f"{invalid_count}个")
            with v_cols[2]:
                st.metric("🔧 已修正", f"{corrected_count}个")

            with st.expander("📋 校验详情", expanded=False):
                for d in validation_details:
                    orig = d.get("original", [])
                    valid = d.get("valid", True)
                    reason = d.get("reason", "")
                    correction = d.get("correction")

                    if valid:
                        icon = "✅"
                    elif correction:
                        icon = "🔧"
                    else:
                        icon = "❌"

                    line = f"{icon} [{orig[0]}, {orig[1]}, {orig[2]}]"
                    if not valid:
                        line += f" — {reason}"
                    if correction:
                        line += f" → 修正为: [{correction[0]}, {correction[1]}, {correction[2]}]"
                    st.markdown(line)

        with st.expander("📋 三元组预览", expanded=True):
            for i, (e1, rel, e2) in enumerate(triplets[:50]):
                st.markdown(f"{i+1}. **{e1}** → _{rel}_ → **{e2}**")
            if len(triplets) > 50:
                st.info(f"仅展示前50条，共{len(triplets)}条")

    st.markdown("---")
    with st.expander("🔧 缓存管理"):
        st.markdown("LLM缓存可避免对相同文本重复调用API，节省费用和时间。")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("🗑️ 清除抽取缓存"):
                LLMExtractor.clear_cache()
                st.success("抽取缓存已清除")
        with col_b:
            if st.button("🗑️ 清除校验缓存"):
                TripletValidator.clear_cache()
                st.success("校验缓存已清除")
        with col_c:
            llm_cache_dir = LLMExtractor.LLM_CACHE_DIR
            val_cache_dir = TripletValidator.VALIDATOR_CACHE_DIR
            llm_count = len([f for f in os.listdir(llm_cache_dir) if f.endswith(".json")]) if os.path.exists(llm_cache_dir) else 0
            val_count = len([f for f in os.listdir(val_cache_dir) if f.endswith(".json")]) if os.path.exists(val_cache_dir) else 0
            st.info(f"抽取缓存: {llm_count}条 | 校验缓存: {val_count}条")
