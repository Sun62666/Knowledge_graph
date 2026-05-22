import re
from typing import List, Tuple, Optional, Dict, Set
from utils.logger import get_logger
from utils.config import ENTITY_TYPES, RELATION_TYPES

logger = get_logger()

_spacy_nlp_instance = None
_spacy_model_name = None


def _get_spacy_model(model_name: str = "zh_core_web_sm"):
    global _spacy_nlp_instance, _spacy_model_name
    if _spacy_nlp_instance is not None and _spacy_model_name == model_name:
        return _spacy_nlp_instance
    try:
        import spacy
        _spacy_nlp_instance = spacy.load(model_name)
        _spacy_model_name = model_name
        logger.info(f"spaCy模型加载成功(单例): {model_name}")
        return _spacy_nlp_instance
    except ImportError:
        logger.error("spacy未安装, 请执行: pip install spacy")
        return None
    except OSError:
        logger.error(f"spaCy模型未下载, 请执行: python -m spacy download {model_name}")
        return None


def _has_chinese(s: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', s))


_GENERIC_NOUNS = frozenset({
    "所有", "日常", "工作", "整体", "业务", "事务", "服务", "售后",
    "前端", "后端", "软件", "硬件", "测试", "开发", "运营", "管理",
    "采购", "绩效", "薪酬", "核算", "招聘", "考勤", "请假", "加班",
    "报销", "保密", "出差", "办公", "会议室", "印章", "档案", "安全",
    "网络", "培训", "平面", "视频", "运动", "休闲", "养生", "健身",
    "兼职", "编程", "剪辑", "口译", "笔译", "客服", "营销", "销售",
    "上传", "下单", "生产", "安装", "维修", "装备", "钢带", "管材",
    "薄板", "炼钢", "涂装", "润滑", "夹具", "模具", "量具", "图纸",
    "会计", "出纳", "法务", "法律", "税务", "审计", "文案", "设计",
    "推广", "媒体", "广告", "活动", "方案", "流程", "制度", "规范",
    "条例", "办法", "计划", "进度", "预算", "成本", "报价", "合同",
    "发票", "单据", "凭证", "台账", "档案", "资产", "设备", "设施",
    "办公用品", "办公设备", "监控设备", "网络设备", "空调设备",
    "状态", "资料", "文件", "文档", "数据", "信息", "通知", "公告",
    "申请", "审批", "审核", "核准", "批准", "检验", "验收", "验收单",
    "入库", "出库", "领用", "借用", "归还", "报修", "维修", "报废",
    "客户", "供应", "合作", "资源", "成果", "表", "单", "流程",
    "业务", "并发", "实时", "事务", "期末", "工种", "工序", "工位",
    "项目", "上下", "正式", "标准", "内件", "拆", "框",
    "员工", "主任", "主管", "总监", "经理", "部长", "总裁",
    "应聘", "通知", "对象", "平台", "区域", "方面", "部分",
    "高精密", "精细", "高度", "突发", "附加", "特殊",
    "总部", "旗下", "费用", "产品", "部门", "中心", "催收",
    "奋进", "团结", "创新", "务实", "效益", "质量", "保障",
    "文化", "愿景", "使命", "目标", "诚信", "责任", "担当",
    "防控", "管控", "合规", "检查", "监督", "机制", "体系",
    "能力", "水平", "素质", "意识", "效率", "执行力",
    "演示文稿", "幻灯片", "日报", "周报", "月报", "年报",
    "产品线", "版本", "行业", "领域", "系统", "等级",
    "规格", "类型", "组装", "包装", "检测", "存储",
    "余额", "往来", "计提", "折旧", "摊销", "税费",
    "付款", "收款", "结算", "汇款", "退款", "充值",
    "请假条", "加班单", "出差单", "报销单", "采购单",
    "订单", "入库单", "出库单", "退货", "索赔", "投诉",
    "议案", "题案", "议题", "纪要", "决议", "结论",
    "辅导", "带教", "实习", "试用", "转正", "晋升",
    "调岗", "调薪", "降职", "免职", "辞退", "裁员",
    "入职", "离职", "请假", "出差", "加班", "调休",
    "社保", "公积金", "五险一金", "一金", "节日", "福利",
    "团队", "建设", "拓展", "创新", "实施", "执行",
    "优化", "改进", "升级", "完善",
    "晚餐", "餐费", "交通", "住宿",
    "办公区", "办公区域", "工位", "会议室",
    "用品", "场所", "需求", "分析",
})

_ENTITY_BOUNDARY_FIX = re.compile(r'^(隶|隶于|属于|包|包括|拥有|设|设有|下辖|负责|管理|担任|的|着|于|在)')
_ENTITY_BOUNDARY_FIX_SUFFIX = re.compile(r'(隶|隶于|属于|包|包括|拥有|设|设有|下辖|负责|管理|担任|的|着|于|在)$')


def _clean_spacy_entity(text: str) -> str:
    text = text.strip()
    prev = None
    while text != prev:
        prev = text
        text = _ENTITY_BOUNDARY_FIX.sub('', text, count=1).strip()
    prev = None
    while text != prev:
        prev = text
        m = _ENTITY_BOUNDARY_FIX_SUFFIX.search(text)
        if m:
            text = text[:m.start()].strip()
        else:
            break
    return text


def _is_valid_entity(text: str) -> bool:
    if len(text) < 2 or len(text) > 30:
        return False
    if not _has_chinese(text):
        return False
    if re.match(r'^\d{1,4}年\d{0,2}月?\d{0,2}日?[前后]?$', text):
        return True
    if text in _GENERIC_NOUNS:
        return False
    if re.search(r'\d{4}', text) and re.search(r'[\u4e00-\u9fff]{2,}', text):
        return False
    pure = re.sub(r'[\u4e00-\u9fff]', '', text)
    if len(pure) > len(text) * 0.7:
        return False
    if re.search(r'\d{3,}', text) and len(re.sub(r'\d', '', text)) < 3:
        return False
    return True


_PERSON_SURNAMES = re.compile(
    r'^(王|李|张|刘|陈|杨|赵|黄|周|吴|徐|孙|胡|朱|高|林|何|郭|马|罗|梁|宋|郑|谢|韩|唐|冯|于|董|萧|程|曹|袁|邓|许|傅|沈|曾|彭|吕|苏|卢|蒋|蔡|贾|丁|魏|薛|叶|阎|余|潘|杜|戴|夏|钟|汪|田|任|姜|范|方|石|姚|谭|廖|邹|熊|金|陆|郝|孔|白|崔|康|毛|邱|秦|江|史|顾|侯|邵|孟|龙|万|段|雷|钱|汤|尹|黎|易|常|武|乔|贺|赖|龚|文)'
)

_ORG_SUFFIXES = frozenset({
    "公司", "集团", "企业", "银行", "大学", "学院", "医院",
    "部门", "研究所", "研究院", "中心", "基金", "协会",
})

def _infer_entity_type(text: str, original_type: str) -> str:
    if original_type not in ("组织名", "其他"):
        return original_type
    if _PERSON_SURNAMES.match(text) and len(text) >= 2 and len(text) <= 4:
        if text not in _ORG_SUFFIXES and text not in _GENERIC_NOUNS:
            return "人名"
    return original_type


class BaseSpacyExtractor:
    SPACY_TO_LOCAL = {
        "PERSON": "人名", "LOC": "地名", "GPE": "地名",
        "ORG": "组织名", "PRODUCT": "产品名",
        "EVENT": "事件", "DATE": "时间", "TIME": "时间",
        "FAC": "地名", "NORP": "组织名", "WORK_OF_ART": "作品名",
    }

    TYPE_COMPAT: Dict[Tuple[str, str], List[str]] = {
        ("人名", "组织名"): ["任职", "创建", "担任", "属于", "管理"],
        ("人名", "职位"): ["任职", "担任"],
        ("人名", "人名"): ["管理"],
        ("组织名", "人名"): [],
        ("组织名", "组织名"): ["包含", "属于", "合作", "投资", "收购", "管理"],
        ("组织名", "地名"): ["位于"],
        ("组织名", "产品名"): ["研发", "生产", "包含"],
        ("组织名", "时间"): ["成立"],
        ("人名", "时间"): ["成立"],
        ("地名", "组织名"): ["位于"],
        ("地名", "地名"): ["位于"],
        ("职位", "组织名"): ["任职"],
        ("人名", "产品名"): ["研发", "发明", "创建"],
        ("人名", "作品名"): ["创建"],
        ("作品名", "人名"): ["创建"],
    }

    TIME_ENTITIES = {"DATE", "TIME", "CARDINAL", "ORDINAL"}
    LOC_ENTITIES = {"GPE", "LOC", "FAC"}

    def __init__(self, model_name: str = "zh_core_web_sm"):
        self._model_name = model_name

    @property
    def nlp(self):
        return _get_spacy_model(self._model_name)

    @property
    def is_ready(self) -> bool:
        return self.nlp is not None

    def _extract_ner_entities(self, doc) -> List[dict]:
        entities = []
        for ent in doc.ents:
            local_type = self.SPACY_TO_LOCAL.get(ent.label_)
            if local_type not in ENTITY_TYPES:
                continue
            text = _clean_spacy_entity(ent.text)
            if not _is_valid_entity(text):
                continue
            entities.append({
                "text": text, "local_type": _infer_entity_type(text, local_type),
                "start": ent.start_char, "end": ent.end_char,
            })
        return entities

    def _extract_sent_entities(self, doc, sent) -> List[dict]:
        sent_start = sent.start_char
        sent_end = sent.end_char
        ner_spans = set()
        sent_entities = []

        for ent in doc.ents:
            if not (ent.start >= sent.start and ent.end <= sent.end):
                continue
            local_type = self.SPACY_TO_LOCAL.get(ent.label_)
            if local_type not in ENTITY_TYPES:
                continue
            text = _clean_spacy_entity(ent.text)
            if not _is_valid_entity(text):
                continue
            sent_entities.append({
                "text": text, "local_type": _infer_entity_type(text, local_type),
                "start": ent.start_char - sent_start,
                "end": ent.end_char - sent_start,
                "spacy_label": ent.label_,
            })
            for idx in range(ent.start, ent.end):
                ner_spans.add(idx)

        for token in sent:
            if token.i in ner_spans:
                continue
            if token.pos_ == "PROPN" and _has_chinese(token.text):
                text = _clean_spacy_entity(token.text)
                if _is_valid_entity(text) and text not in _GENERIC_NOUNS:
                    sent_entities.append({
                        "text": text, "local_type": "组织名",
                        "start": token.idx - sent_start,
                        "end": token.idx - sent_start + len(token.text),
                    })
                    ner_spans.add(token.i)
            elif token.pos_ == "NOUN" and _has_chinese(token.text) and len(token.text) >= 2:
                text = token.text.strip()
                if text not in _GENERIC_NOUNS and (
                    text.endswith(("部", "组", "组)", "中心", "处", "室", "科", "所", "院", "会"))
                    or token.ent_type_
                ):
                    compound_tokens = [token]
                    for t in sent:
                        if t.head.i == token.i and t.dep_ == "compound:nn":
                            sub = self._collect_compound_children(t, sent)
                            for st in sub:
                                if st not in compound_tokens:
                                    compound_tokens.append(st)
                    compound_tokens.sort(key=lambda t: t.i)
                    if compound_tokens[-1].i - compound_tokens[0].i + 1 != len(compound_tokens):
                        compound_tokens = [token]
                    full_text = "".join(t.text for t in compound_tokens)
                    full_text = _clean_spacy_entity(full_text)
                    if _is_valid_entity(full_text):
                        start_char = compound_tokens[0].idx - sent_start
                        end_char = compound_tokens[-1].idx - sent_start + len(compound_tokens[-1].text)
                        sent_entities.append({
                            "text": full_text, "local_type": "组织名",
                            "start": start_char, "end": end_char,
                        })
                        for ct in compound_tokens:
                            ner_spans.add(ct.i)

        merged = _merge_adjacent_entities(sent_entities, sent.text)
        for ent in merged:
            ent["local_type"] = _infer_entity_type(ent["text"], ent["local_type"])
        return merged

    def _get_paired_relations(self, e1_type: str, e2_type: str) -> List[str]:
        return self.TYPE_COMPAT.get((e1_type, e2_type), [])

    def _collect_compound_children(self, token, sent) -> List:
        result = [token]
        for t in sent:
            if t.head.i == token.i and t.dep_ == "compound:nn":
                sub = self._collect_compound_children(t, sent)
                for st in sub:
                    if st not in result:
                        result.append(st)
        return result


def _merge_adjacent_entities(entities: List[dict], sent_text: str) -> List[dict]:
    if len(entities) <= 1:
        return entities
    entities = sorted(entities, key=lambda e: e["start"])
    deduped = []
    seen_spans = set()
    for e in entities:
        span = (e["start"], e["end"])
        if span not in seen_spans:
            seen_spans.add(span)
            deduped.append(e)
    entities = deduped
    merged = []
    skip = set()
    for i in range(len(entities)):
        if i in skip:
            continue
        e = entities[i]
        for j in range(i + 1, len(entities)):
            if j in skip:
                continue
            e2 = entities[j]
            gap = e2["start"] - e["end"]
            if gap < 0:
                continue
            if gap > 3:
                break
            gap_text = sent_text[e["end"]:e2["start"]].strip()
            if gap_text and not re.match(r'^[的之和与及、,，/·]+$', gap_text):
                break
            types_compat = (e["local_type"] == e2["local_type"]
                            or e["local_type"] == "组织名" or e2["local_type"] == "组织名")
            if types_compat:
                combined_text = sent_text[e["start"]:e2["end"]]
                if re.search(r'[。！？；;]', combined_text):
                    break
                combined = _clean_spacy_entity(combined_text)
                if _is_valid_entity(combined) and len(combined) <= 25:
                    e = {
                        "text": combined, "local_type": "组织名",
                        "start": e["start"], "end": e2["end"],
                    }
                    skip.add(j)
        merged.append(e)
    return merged


class SpacyRuleExtractor(BaseSpacyExtractor):

    RELATION_KEYWORDS: Dict[str, List[str]] = {
        "任职": ["担任", "出任", "就任", "任", "任职"],
        "属于": ["隶属于", "所属", "属于", "归属"],
        "包含": ["包含", "拥有", "设有", "设有:", "设立了", "下辖", "下设有"],
        "管理": ["负责管理", "负责", "管理", "管辖"],
        "创建": ["创立", "创办", "创建", "成立", "建立", "组建", "创办了"],
        "位于": ["坐落于", "总部位于", "坐落", "位于", "地处"],
        "研发": ["研发了", "推出了", "研发", "开发", "研制", "推出"],
        "合作": ["合作", "联合", "携手", "配合"],
        "投资": ["投资了", "投资", "注资", "入股"],
        "收购": ["收购了", "收购", "并购", "兼并"],
        "生产": ["生产", "制造", "加工"],
        "发明": ["发明了", "发明", "发明出"],
        "发现": ["发现了", "发现"],
        "组成": ["组成", "构成", "由...组成"],
        "著有": ["著有", "著作有", "代表作有"],
        "担任": ["担任", "出任", "担任了"],
    }

    RELATION_PATTERNS = [
        (re.compile(r'总部位于|坐落于|地处|坐落|位于'), "位于"),
        (re.compile(r'创立了|创办了|创建了|成立了|建立了|组建了|创立|创办|创建|成立|建立|组建'), "创建"),
        (re.compile(r'担任了|出任了|就任了|担任|出任|就任'), "任职"),
        (re.compile(r'研发了|开发了|研制了|推出了|研发|开发|研制|推出'), "研发"),
        (re.compile(r'投资了|注资了|入股了|投资|注资|入股'), "投资"),
        (re.compile(r'收购了|并购了|兼并了|收购|并购|兼并'), "收购"),
        (re.compile(r'合作了|联合了|携手了|合作|联合|携手'), "合作"),
        (re.compile(r'生产了|制造了|生产|制造'), "生产"),
        (re.compile(r'发明了|发明出|发明'), "发明"),
        (re.compile(r'发现了|发现'), "发现"),
        (re.compile(r'隶属于|属于|归属'), "属于"),
        (re.compile(r'包含|包括|拥有|设有|下辖'), "包含"),
        (re.compile(r'负责管理|负责|管理|管辖'), "管理"),
    ]

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        if not self.is_ready:
            return []

        doc = self.nlp(text)
        triplets = []
        used: Set[Tuple[str, str, str]] = set()

        for sent in doc.sents:
            sent_text = sent.text
            sent_entities = self._extract_sent_entities(doc, sent)

            if len(sent_entities) < 2:
                continue

            time_entities = [e for e in sent_entities if e["local_type"] == "时间"]
            non_time_entities = [e for e in sent_entities if e["local_type"] != "时间"]

            for i in range(len(non_time_entities)):
                for j in range(i + 1, len(non_time_entities)):
                    e1, e2 = non_time_entities[i], non_time_entities[j]
                    if e1["end"] > e2["start"]:
                        continue

                    between = sent_text[e1["end"]:e2["start"]].strip()
                    if re.search(r'[。！？；;]', between):
                        continue
                    if len(between) < 1 or len(between) > 25:
                        continue
                    if re.search(r'[，；！？。\n,;!?]', between):
                        continue

                    rel = self._match_relation(between, e1["local_type"], e2["local_type"])
                    if not rel:
                        continue

                    key = (e1["text"], rel, e2["text"])
                    if key in used:
                        continue
                    used.add(key)
                    triplets.append((e1["text"], rel, e2["text"]))

            for e1 in non_time_entities:
                for e2 in time_entities:
                    if e1["end"] > e2["start"]:
                        continue
                    between = sent_text[e1["end"]:e2["start"]].strip()
                    if not between or len(between) > 15:
                        continue
                    rel = self._match_relation(between, e1["local_type"], e2["local_type"])
                    if not rel:
                        continue
                    key = (e1["text"], rel, e2["text"])
                    if key not in used:
                        used.add(key)
                        triplets.append((e1["text"], rel, e2["text"]))

        logger.info(f"SpacyRule抽取完成: {len(triplets)}个三元组")
        return triplets

    def _match_relation(self, between: str, e1_type: str, e2_type: str) -> Optional[str]:
        compat = self.TYPE_COMPAT.get((e1_type, e2_type), [])

        for pattern, rel in self.RELATION_PATTERNS:
            if compat and rel not in compat:
                continue
            m = pattern.search(between)
            if m:
                if len(between) <= 8 or pattern.match(between):
                    return rel

        if compat and len(compat) == 1 and len(between) <= 6:
            return compat[0]

        return None


class SpacyTemplateExtractor(BaseSpacyExtractor):

    TEMPLATES = [
        {"pattern": "{e1}隶属于{e2}", "relation": "属于", "e1_type": "人名", "e2_type": "组织名"},
        {"pattern": "{e1}属于{e2}", "relation": "属于", "e1_type": None, "e2_type": None},
        {"pattern": "{e1}的所属部门是{e2}", "relation": "属于", "e1_type": "人名", "e2_type": "组织名"},
        {"pattern": "{e1}在{e2}担任{e3}", "relation": "任职", "e1_type": "人名", "e2_type": "组织名", "e3_type": "职位",
         "triple_mode": True},
        {"pattern": "{e1}是{e2}的{e3}", "relation": "任职", "e1_type": "人名", "e2_type": "组织名", "e3_type": "职位",
         "triple_mode": True},
        {"pattern": "{e1}在{e2}担任", "relation": "任职", "e1_type": "人名", "e2_type": "组织名"},
        {"pattern": "{e1}负责{e2}", "relation": "管理", "e1_type": None, "e2_type": None},
        {"pattern": "{e1}负责管理{e2}", "relation": "管理", "e1_type": None, "e2_type": None},
        {"pattern": "{e1}管理{e2}", "relation": "管理", "e1_type": None, "e2_type": None},
        {"pattern": "{e1}包含{e2}", "relation": "包含", "e1_type": "组织名", "e2_type": "组织名"},
        {"pattern": "{e1}设有{e2}", "relation": "包含", "e1_type": "组织名", "e2_type": "组织名"},
        {"pattern": "{e1}下辖{e2}", "relation": "包含", "e1_type": "组织名", "e2_type": "组织名"},
        {"pattern": "{e1}由{e2}担任", "relation": "任职", "e1_type": "职位", "e2_type": "人名"},
        {"pattern": "{e1}由{e2}负责", "relation": "管理", "e1_type": "组织名", "e2_type": "人名"},
        {"pattern": "{e1}是{e2}的负责人", "relation": "管理", "e1_type": "人名", "e2_type": "组织名"},
        {"pattern": "{e1}的负责人是{e2}", "relation": "管理", "e1_type": "组织名", "e2_type": "人名"},
        {"pattern": "{e1}总部位于{e2}", "relation": "位于", "e1_type": "组织名", "e2_type": "地名"},
        {"pattern": "{e1}由{e2}创立", "relation": "创建", "e1_type": "组织名", "e2_type": "人名"},
        {"pattern": "{e1}由{e2}于{e3}创立", "relation": "创建", "e1_type": "组织名", "e2_type": "人名", "e3_type": "时间",
         "triple_mode": True},
        {"pattern": "{e1}由{e2}创建", "relation": "创建", "e1_type": "组织名", "e2_type": "人名"},
        {"pattern": "{e1}研发了{e2}", "relation": "研发", "e1_type": "组织名", "e2_type": "产品名"},
        {"pattern": "{e1}推出了{e2}", "relation": "研发", "e1_type": "组织名", "e2_type": "产品名"},
        {"pattern": "{e1}开发了{e2}", "relation": "研发", "e1_type": "组织名", "e2_type": "产品名"},
        {"pattern": "{e1}投资了{e2}", "relation": "投资", "e1_type": "组织名", "e2_type": "组织名"},
        {"pattern": "{e1}收购了{e2}", "relation": "收购", "e1_type": "组织名", "e2_type": "组织名"},
        {"pattern": "{e1}位于{e2}", "relation": "位于", "e1_type": None, "e2_type": "地名"},
        {"pattern": "{e1}的CEO是{e2}", "relation": "任职", "e1_type": "组织名", "e2_type": "人名"},
        {"pattern": "{e1}担任{e2}", "relation": "任职", "e1_type": "人名", "e2_type": "职位"},
        {"pattern": "{e1}担任{e2}的", "relation": "任职", "e1_type": "人名", "e2_type": "职位"},
        {"pattern": "{e1}担任{e2}的{e3}", "relation": "任职", "e1_type": "人名", "e2_type": "组织名", "e3_type": "职位",
         "triple_mode": True},
        {"pattern": "{e1}创立于{e2}", "relation": "成立", "e1_type": "组织名", "e2_type": "时间"},
        {"pattern": "{e1}成立于{e2}", "relation": "成立", "e1_type": "组织名", "e2_type": "时间"},
        {"pattern": "{e1}创建于{e2}", "relation": "成立", "e1_type": "组织名", "e2_type": "时间"},
    ]

    RELATION_WORDS_RE = re.compile(
        r'(隶属于|所属部门是|总部位于|坐落于|由|在|位于|担任|出任|就任|负责管理|负责'
        r'|管理|包含|设有|下辖|研发了|开发了|推出了|投资了|收购了|创立于'
        r'|成立于|创建于|创立|创建|成立|研制|推出|属于)'
    )

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        if not self.is_ready:
            return []

        doc = self.nlp(text)
        triplets = []
        used: Set[Tuple[str, str, str]] = set()

        all_entities = self._extract_ner_entities(doc)

        for sent in doc.sents:
            sent_text = sent.text
            sent_entities = self._extract_sent_entities(doc, sent)

            for tmpl in self.TEMPLATES:
                relation = tmpl["relation"]
                has_triple = tmpl.get("triple_mode", False)

                if has_triple:
                    result = self._match_triple_template(sent_text, sent_entities, tmpl)
                    if result and result not in used:
                        used.add(result)
                        triplets.append(result)
                else:
                    results = self._match_pair_template(sent_text, sent_entities, tmpl, all_entities)
                    for r in results:
                        if r not in used:
                            used.add(r)
                            triplets.append(r)

        logger.info(f"SpacyTemplate抽取完成: {len(triplets)}个三元组")
        return triplets

    def _match_pair_template(self, sent_text: str, sent_entities: List[dict],
                              tmpl: dict, all_entities: List[dict]) -> List[Tuple[str, str, str]]:
        relation = tmpl["relation"]
        e1_type = tmpl.get("e1_type")
        e2_type = tmpl.get("e2_type")
        pattern = tmpl["pattern"]
        parts = self.RELATION_WORDS_RE.split(pattern)
        results = []

        for i in range(len(sent_entities)):
            for j in range(len(sent_entities)):
                if i == j:
                    continue
                e1, e2 = sent_entities[i], sent_entities[j]

                if e1_type and e1["local_type"] != e1_type:
                    continue
                if e2_type and e2["local_type"] != e2_type:
                    continue
                if e1["end"] > e2["start"]:
                    continue

                between = sent_text[e1["end"]:e2["start"]]
                if re.search(r'[。！？；;]', between):
                    continue
                candidate = e1["text"] + between + e2["text"]

                if self._tokens_match_pattern(candidate, e1["text"], e2["text"], tmpl):
                    compat = self.TYPE_COMPAT.get((e1["local_type"], e2["local_type"]), [])
                    if e1_type is None and e2_type is None:
                        if compat and relation in compat:
                            results.append((e1["text"], relation, e2["text"]))
                    elif compat and relation in compat:
                        results.append((e1["text"], relation, e2["text"]))

        return results

    def _match_triple_template(self, sent_text: str, sent_entities: List[dict],
                                tmpl: dict) -> Optional[Tuple[str, str, str]]:
        relation = tmpl["relation"]
        e1_type = tmpl.get("e1_type")
        e2_type = tmpl.get("e2_type")
        e3_type = tmpl.get("e3_type")

        for i in range(len(sent_entities)):
            e1 = sent_entities[i]
            if e1_type and e1["local_type"] != e1_type:
                continue
            remaining = [e for e in sent_entities[i + 1:] if e["start"] > e1["end"]]
            if len(remaining) < 2:
                continue
            for j in range(len(remaining)):
                for k in range(j + 1, len(remaining)):
                    e2_cand, e3_cand = remaining[j], remaining[k]
                    type_ok = True
                    if e3_type and e3_cand["local_type"] != e3_type:
                        type_ok = False
                    if e2_type and e2_cand["local_type"] != e2_type:
                        type_ok = False
                    if not type_ok:
                        continue
                    if e3_cand["start"] < e2_cand["start"]:
                        continue
                    segment = sent_text[e1["start"]:e3_cand["end"]]
                    pattern = tmpl["pattern"]
                    regex_parts = []
                    idx = 0
                    for part in self.RELATION_WORDS_RE.split(pattern):
                        if part in ("{e1}", "{e2}", "{e3}"):
                            continue
                        escaped = re.escape(part)
                        regex_parts.append(escaped)
                        idx += 1

                    rx = pattern.replace("{e1}", re.escape(e1["text"]))
                    rx = rx.replace("{e2}", re.escape(e2_cand["text"]))
                    rx = rx.replace("{e3}", re.escape(e3_cand["text"]))
                    try:
                        if re.search(rx, sent_text):
                            return (e1["text"], relation, e2_cand["text"])
                    except re.error:
                        continue

        return None

    def _tokens_match_pattern(self, candidate: str, e1: str, e2: str,
                               tmpl: dict) -> bool:
        pattern = tmpl["pattern"]
        rel_words = self.RELATION_WORDS_RE.findall(pattern)
        if not rel_words:
            return False
        idx = candidate.find(e2, len(e1))
        if idx <= len(e1):
            return False
        mid = candidate[len(e1):idx]
        for rw in rel_words:
            if rw in mid:
                return True
        return False


class SpacyDependencyExtractor(BaseSpacyExtractor):

    VERB_RELATIONS = {
        "创立": "创建", "创办": "创建", "创建": "创建", "成立": "成立",
        "建立": "创建", "组建": "创建", "位于": "位于", "坐落": "位于",
        "担任": "任职", "出任": "任职", "就任": "任职", "任职": "任职",
        "研发": "研发", "开发": "研发", "研制": "研发", "推出": "研发",
        "投资": "投资", "注资": "投资",
        "收购": "收购", "并购": "收购", "兼并": "收购",
        "合作": "合作", "联合": "合作", "配合": "合作",
        "生产": "生产", "制造": "生产", "加工": "生产",
        "发明": "发明", "发明出": "发明",
        "发现": "发现", "发现出": "发现",
        "属于": "属于", "隶属": "属于",
        "包含": "包含", "包括": "包含", "设有": "包含",
        "拥有": "包含", "下辖": "包含",
        "管理": "管理", "负责": "管理", "管辖": "管理",
        "负责管理": "管理",
        "主编": "创建",
        "推出": "研发",
        "开发出": "研发",
        "创作": "创建",
        "发表": "创建",
        "撰写": "创建",
    }

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        if not self.is_ready:
            return []

        doc = self.nlp(text)
        triplets = []
        seen: Set[Tuple[str, str, str]] = set()

        for sent in doc.sents:
            verb_tokens = [
                t for t in sent
                if t.pos_ == "VERB"
                and (t.text in self.VERB_RELATIONS or t.lemma_ in self.VERB_RELATIONS)
            ]

            for verb in verb_tokens:
                verb_text = verb.lemma_ if verb.lemma_ and verb.lemma_ in self.VERB_RELATIONS else verb.text
                rel_label = self.VERB_RELATIONS.get(verb_text)
                if not rel_label:
                    continue

                subjs = []
                objs = []
                times = []
                locs = []

                for child in verb.children:
                    dep = child.dep_
                    if dep in ("nsubj", "nsubj:pass"):
                        subjs.append(child)
                    elif dep in ("obj", "dobj", "attr", "nsubj"):
                        if dep in ("obj", "dobj", "attr"):
                            objs.append(child)
                    elif dep.startswith("obl") and child.ent_type_ in self.TIME_ENTITIES:
                        times.append(child)
                    elif dep.startswith("obl") and child.ent_type_ in self.LOC_ENTITIES:
                        locs.append(child)

                if not subjs or not objs:
                    continue

                for subj in subjs:
                    e1 = self._extract_entity_span(subj)
                    if not e1 or not _is_valid_entity(e1):
                        continue

                    for obj in objs:
                        e2 = self._extract_entity_span(obj)
                        if not e2 or not _is_valid_entity(e2):
                            continue
                        if e1 == e2:
                            continue

                        key = (e1, rel_label, e2)
                        if key in seen:
                            continue
                        seen.add(key)
                        triplets.append((e1, rel_label, e2))

                        for tm in times[:1]:
                            tm_text = self._extract_entity_span(tm)
                            if tm_text and _is_valid_entity(tm_text):
                                tkey = (e1, "成立", tm_text)
                                if tkey not in seen:
                                    seen.add(tkey)
                                    triplets.append((e1, "成立", tm_text))

                        for lm in locs[:1]:
                            lm_text = self._extract_entity_span(lm)
                            if lm_text and _is_valid_entity(lm_text):
                                lkey = (e1, "位于", lm_text)
                                if lkey not in seen:
                                    seen.add(lkey)
                                    triplets.append((e1, "位于", lm_text))

        logger.info(f"SpacyDependency抽取完成: {len(triplets)}个三元组")
        return triplets

    def _extract_entity_span(self, token) -> Optional[str]:
        if token.ent_type_:
            local_type = self.SPACY_TO_LOCAL.get(token.ent_type_, "其他")
            if local_type in ENTITY_TYPES:
                text = _clean_spacy_entity(token.text)
                if _is_valid_entity(text):
                    return text
                return None
        span_tokens = self._collect_compound(token)
        if span_tokens:
            text = "".join(t.text for t in span_tokens)
            text = _clean_spacy_entity(text)
            if _is_valid_entity(text):
                return text
        text = token.text.strip()
        if _has_chinese(text) and len(text) >= 2 and text not in _GENERIC_NOUNS:
            return text
        return None

    def _collect_compound(self, token) -> List:
        tokens = []
        if token.dep_ == "compound" and token.ent_type_:
            tokens.append(token)
        for child in token.children:
            if child.dep_ == "compound":
                sub = self._collect_compound(child)
                if sub:
                    tokens.extend(sub)
        tokens.append(token)
        tokens.sort(key=lambda t: t.i)
        dedup = []
        seen_i = set()
        for t in tokens:
            if t.i not in seen_i:
                seen_i.add(t.i)
                dedup.append(t)
        return dedup if len(dedup) > 1 else []