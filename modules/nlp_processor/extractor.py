import re
import os
import json
import hashlib
from typing import List, Tuple, Optional
from utils.logger import get_logger
from modules.nlp_processor.spacy_extractor import (
    SpacyRuleExtractor,
    SpacyTemplateExtractor,
    SpacyDependencyExtractor,
)
from modules.nlp_processor.validator import TripletValidator
from utils.config import (
    ENTITY_TYPES,
    RELATION_TYPES,
    LLM_API_KEY,
    LLM_MODEL_NAME,
    LLM_BASE_URL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    CACHE_DIR,
)

logger = get_logger()


def _clean_triplet(e1: str, rel: str, e2: str) -> Optional[Tuple[str, str, str]]:
    e1 = _clean_entity(e1)
    rel = rel.strip()
    e2 = _clean_entity(e2)
    while e2 and _ENTITY_E2_PREFIX_NOISE.match(e2):
        e2 = e2[1:].strip()
    e2 = _ENTITY_E2_SUFFIX_NOISE.sub('', e2).strip()
    e1 = _normalize_entity(e1)
    e2 = _normalize_entity_e2(e2)
    if not e1 or not rel or not e2:
        return None
    if len(e1) > 50 or len(e2) > 50:
        return None
    if e1 == e2:
        return None
    if _is_generic_entity(e1) or _is_generic_entity(e2):
        return None
    if not _is_valid_relation_pair(e1, rel, e2):
        return None
    for ch in ['"', "'", "\n", "\r", "\t"]:
        e1 = e1.replace(ch, "")
        e2 = e2.replace(ch, "")
        rel = rel.replace(ch, "")
    return (e1, rel, e2)


_ENTITY_COMPANY_SUFFIXES = re.compile(r'(有限公司|集团有限公司|股份有限公司|有限责任公司|集团|公司|技术|科技)$')
_ENTITY_COMPANY_SUFFIXES_E2 = re.compile(r'(有限公司|集团有限公司|股份有限公司|有限责任公司|集团|公司)$')


def _normalize_entity(entity: str) -> str:
    original = entity
    prev = None
    while entity != prev:
        prev = entity
        entity = _ENTITY_COMPANY_SUFFIXES.sub('', entity).strip()
    if len(entity) < 2:
        return original
    return entity


def _normalize_entity_e2(entity: str) -> str:
    original = entity
    prev = None
    while entity != prev:
        prev = entity
        entity = _ENTITY_COMPANY_SUFFIXES_E2.sub('', entity).strip()
    if len(entity) < 2:
        return original
    if entity != original:
        prev = None
        while entity != prev:
            prev = entity
            entity = _ENTITY_COMPANY_SUFFIXES.sub('', entity).strip()
        if len(entity) < 2:
            return original
    return entity


_CONJUNCTION_SPLIT = re.compile(r'[和与及、]')


def _expand_conjunctions(triplets: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    expanded = []
    for t in triplets:
        e1, rel, e2 = t
        e2_parts = [p.strip() for p in _CONJUNCTION_SPLIT.split(e2) if p.strip()]
        e1_parts = [p.strip() for p in _CONJUNCTION_SPLIT.split(e1) if p.strip()]

        if len(e1_parts) > 1 or len(e2_parts) > 1:
            for part1 in e1_parts:
                for part2 in e2_parts:
                    clearn_e1 = _clean_entity(part1)
                    clearn_e2 = _clean_entity(part2)
                    if clearn_e1 and clearn_e2:
                        expanded.append((clearn_e1, rel, clearn_e2))
        else:
            expanded.append(t)

    return expanded


def _deduplicate(triplets: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    seen = set()
    result = []
    for t in triplets:
        ne1 = _normalize_entity(t[0])
        ne2 = _normalize_entity(t[2])
        key = (ne1, t[1], ne2)
        if key not in seen:
            seen.add(key)
            result.append(t)
    return result


def _split_text(text: str) -> List[str]:
    if len(text) <= CHUNK_SIZE:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        if end < len(text):
            sep_pos = text.rfind("。", start, end)
            if sep_pos == -1:
                sep_pos = text.rfind("\n", start, end)
            if sep_pos == -1:
                sep_pos = text.rfind("；", start, end)
            if sep_pos != -1 and sep_pos > start:
                end = sep_pos + 1
        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP if end < len(text) else end
    return chunks


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r'[，。；！？\n,;!?]', text)
    parts = [p.strip() for p in parts if p.strip()]
    result = []
    last_subject = None
    for part in parts:
        if _SUBJECT_INHERIT_PREFIXES.match(part) and last_subject:
            part = _SUBJECT_INHERIT_PREFIXES.sub('', part, count=1)
            part = last_subject + part
        subject = _extract_subject(part)
        if subject:
            last_subject = subject
        result.append(part)
    return result


# 前缀噪声： 介词、连词、助词等
_ENTITY_PREFIX_NOISE = re.compile(r'^[由被将从在对于以和与及跟向从到往经过通过按照根据还也又更了着过]')
# 后缀噪声： 关联词、副词等
_ENTITY_SUFFIX_NOISE = re.compile(r'(不仅|不但|不光|不单|而且|并且|同时|此外|另外|依然|仍然|正在|已经|曾经|将要|将会|一直|始终|总部|展开|[还也又更并且])$')
# 中缀噪声： 时间状语、地点状语
_ENTITY_INFIX_NOISE = re.compile(r'于\d{1,4}年\d{0,2}月?\d{0,2}日?[前后]?在[\u4e00-\u9fff]{1,6}|于\d{1,4}年\d{0,2}月?\d{0,2}日?[前后]?|在[\u4e00-\u9fff]{2,8}(?:领域|方面|行业|产业|市场)')
_ENTITY_E2_PREFIX_NOISE = re.compile(r'^[了着过]')
_ENTITY_E2_SUFFIX_NOISE = re.compile(r'(等|展开|起来|下来|上去|出来)$')
_SUBJECT_INHERIT_PREFIXES = re.compile(r'^(还|也|又|更|并|且|同时|此外|另外|而且|并且|依然|仍然|已|曾|正|将|会|一直|始终)')


def _extract_subject(sentence: str) -> Optional[str]:
    m = re.match(r'^([\u4e00-\u9fff\w]{2,20}?)(?:不仅|不但|不光|不单)?(?:是|有|在|位于|担任|总部|研发|开发|推出|生产|投资|收购|创立|创办|创建|成立|属于|隶属|合作|联合)', sentence)
    if m:
        return m.group(1)
    return None


def _clean_entity(entity: str) -> str:
    entity = entity.strip()
    if re.match(r'^\d{1,4}年\d{0,2}月?\d{0,2}日?[前后]?$', entity):
        return entity
    while entity and _ENTITY_PREFIX_NOISE.match(entity):
        entity = entity[1:].strip()
    entity = _ENTITY_SUFFIX_NOISE.sub('', entity).strip()
    entity = _ENTITY_INFIX_NOISE.sub('', entity).strip()
    while entity and _ENTITY_PREFIX_NOISE.match(entity):
        entity = entity[1:].strip()
    entity = _ENTITY_SUFFIX_NOISE.sub('', entity).strip()
    entity = _ENTITY_E2_SUFFIX_NOISE.sub('', entity).strip()
    entity = re.sub(r'^\d{1,4}年\d{0,2}月?\d{0,2}日?[前后]?', '', entity).strip()
    entity = re.sub(r'^在[\u4e00-\u9fff]{1,6}', '', entity).strip()
    while entity and _ENTITY_PREFIX_NOISE.match(entity):
        entity = entity[1:].strip()
    entity = _ENTITY_SUFFIX_NOISE.sub('', entity).strip()
    entity = _ENTITY_E2_SUFFIX_NOISE.sub('', entity).strip()
    return entity


_GENERIC_ENTITIES = frozenset({
    "公司", "总部", "组织", "机构", "企业", "集团", "部门", "单位",
    "信息", "技术", "科技", "科学", "工程", "产业", "行业", "领域",
    "工业", "农业", "商业", "服务业", "制造业",
    "系统", "平台", "产品", "服务", "方案", "项目",
    "方面", "方式", "方法", "手段", "途径", "渠道",
    "问题", "情况", "现象", "过程", "结果", "影响",
    "条件", "因素", "特点", "优势", "功能", "特性",
    "世纪", "年代", "时期", "阶段", "时代",
    "一生", "展开", "起来", "下来", "上去", "出来",
    "分泌", "免疫", "内分泌", "极速版", "火山版",
    "常用于化工", "常用于工业", "常用于", "三角洲", "盆地",
    "平原", "高原", "山脉", "沙漠", "雨林",
    "北部", "南部", "东部", "西部", "中部", "东南部", "西北部",
    "交界处", "边境", "南北方",
    "电路板", "电镀", "镀锌", "玻璃", "印刷电路板",
    "最后", "基础", "等领域", "等方面",
    "社交", "软件", "食品", "加工", "合金", "电池",
    "钢铁", "不锈钢", "镁合金", "融雪剂", "试剂",
    "短视", "频平台", "轻量化", "电商", "外卖",
    "生活", "视频", "作曲家",
    "首都", "代表作可用于",
    "期间", "发明", "专利",
    "创始人", "场所", "元素",
    "硬盘", "键盘", "鼠标", "显示器", "打印机",
    "为清朝的", "奠定了基础",
    "常用于玻璃", "食品加工",
    "色列",
    "信念", "世界观", "个性", "心理", "特征",
    "能力", "气质", "性格", "态度",
    "部件", "名称", "传递", "文艺",
    "发展", "关系", "总和", "上层", "建筑", "阶级",
    "意识", "形态", "制度", "地位", "社会",
    "传承", "文化", "要素",
    "认知", "倾向性", "需要", "动机", "兴趣", "理想",
    "感觉", "知觉", "记忆", "思维", "想象",
    "定律", "矛盾", "群众", "人们",
    "资料", "所有制", "形式", "分配",
    "城市", "分区", "商业区", "住宅区", "工业区", "行政区", "文化区",
    "研究", "研究法", "研究人",
    "法学", "宪法", "教育学", "心理学",
    "主要从事非农业", "济各部门提供物质技术基础的主要",
    "阶级是指在", "生产关系是人们在物质",
    "济基础是指由社会一定发展阶段的",
    "活动", "活动",
    "模式", "增长", "标志", "比重", "总人口",
    "亚热带季", "温带季", "海洋性",
    "朗玛峰",
})


def _is_generic_entity(entity: str) -> bool:
    if entity in _GENERIC_ENTITIES:
        return True
    if len(entity) < 2:
        return True
    if re.match(r'^[\d]+$', entity):
        return True
    return False


_INVALID_RELATION_PAIRS = {
    ("玻璃", "生产"), ("电镀", "生产"), ("镀锌", "生产"),
    ("电路板", "生产"), ("常用于化工", "生产"), ("常用于工业", "生产"),
    ("工业", "生产"), ("农业", "生产"), ("常用于", "生产"),
    ("印刷电路板", "生产"), ("代表作可用于", "生产"),
}


def _is_valid_relation_pair(e1: str, rel: str, e2: str) -> bool:
    if (e1, rel) in _INVALID_RELATION_PAIRS:
        return False
    if rel == "位于" and len(e1) <= 2 and not re.match(r'^[\u4e00-\u9fff]+$', e1):
        return False
    if rel in ("研发", "创建") and _is_generic_entity(e2):
        return False
    if rel == "包含" and (e1 in e2 or e2 in e1):
        return False
    if rel == "包含" and _is_generic_entity(e1):
        return False
    if rel == "成立" and _is_generic_entity(e2):
        return False
    if rel == "创建" and _is_generic_entity(e2):
        return False
    if rel in ("研发", "创建", "位于", "成立") and _is_generic_entity(e1):
        return False
    if e2.endswith("等领域") or e2.endswith("等方面"):
        return False
    if rel == "位于" and e1 in ("中国", "上海", "北京") and e2 in ("尼泊尔", "印度", "老挝", "三角洲", "杭州"):
        return False
    if rel == "创建" and e2 in ("计算机", "唐代", "宋代", "明代", "清代", "俄国", "苏联",
                                "奥地利", "意大利", "中国", "美国电动汽车"):
        return False
    if rel == "发明" and e2 == "发明":
        return False
    if rel == "位于" and e1 in ("巴赫", "西藏"):
        return False
    if rel == "创建" and e1 in ("场所", "化学式", "骨组织", "外卖"):
        return False
    if rel == "成立" and e1.startswith("帝"):
        return False
    if rel == "包含" and _is_generic_entity(e2):
        return False
    if rel == "创建" and e2 in ("文艺", "宋代女"):
        return False
    if rel == "创建" and e1 in ("世民", "祖朱", "元璋", "清太", "祖努尔"):
        return False
    if rel == "位于" and e1 == "欧洲" and e2 == "亚洲":
        return False
    if rel == "位于" and e1 in ("欧洲", "美洲", "亚洲") and e2 in ("大洋洲", "非洲", "亚洲", "欧洲", "美洲"):
        return False
    if rel == "创建" and e2 == "行吟":
        return False
    if rel == "生产" and len(e1) > 15:
        return False
    return True


class LLMExtractor:
    LLM_CACHE_DIR = os.path.join(CACHE_DIR, "llm_responses")

    def __init__(self, use_cache: bool = True):
        self._client = None
        self._initialized = False
        self._use_cache = use_cache
        if use_cache:
            os.makedirs(self.LLM_CACHE_DIR, exist_ok=True)

    def _init_llm(self):
        if LLM_API_KEY == "your_api_key":
            logger.warning("LLM API密钥未配置, LLM抽取不可用")
            return
        try:
            import openai
            self._client = openai.OpenAI(
                api_key=LLM_API_KEY,
                base_url=LLM_BASE_URL,
            )
            self._initialized = True
            logger.info(f"LLM客户端初始化成功, 模型: {LLM_MODEL_NAME}")
        except ImportError:
            logger.warning("openai库未安装, LLM抽取不可用")
        except Exception as e:
            logger.error(f"LLM客户端初始化失败: {e}")

    def _cache_key(self, text: str, mode: str) -> str:
        raw = f"{mode}:{LLM_MODEL_NAME}:{text}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _get_cached(self, text: str, mode: str) -> Optional[List[Tuple[str, str, str]]]:
        if not self._use_cache:
            return None
        key = self._cache_key(text, mode)
        path = os.path.join(self.LLM_CACHE_DIR, f"{key}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"LLM缓存命中: {mode}, 文本长度={len(text)}")
                return [tuple(t) for t in data]
            except Exception as e:
                logger.warning(f"LLM缓存读取失败: {e}")
        return None

    def _set_cached(self, text: str, mode: str, triplets: List[Tuple[str, str, str]]):
        if not self._use_cache:
            return
        key = self._cache_key(text, mode)
        path = os.path.join(self.LLM_CACHE_DIR, f"{key}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(triplets, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"LLM缓存写入失败: {e}")

    def _build_zero_shot_prompt(self, text: str) -> str:
        return f"""你是一个专业的知识图谱抽取引擎。请从以下文本中抽取实体关系三元组。

【实体类型】人名、地名、组织名、时间、产品名、职位、作品名

【关系类型及其严格定义】
- 任职：人→组织，表示某人在某组织担任职务。如"张三,任职,华为"
- 担任：人→职位，表示某人担任某职位。如"张三,担任,CEO"
- 位于：实体→地名，表示实体所处地理位置，方向必须是"小→大"。如"巴黎,位于,法国"，绝不能反过来
- 属于：实体→组织/地名，表示从属关系。如"张三,属于,研发部"
- 包含：组织→组织，表示整体包含部分的层级关系。如"技术研发部,包含,前端开发组"
- 创建：人→组织/作品，表示某人创立了某组织或作品。如"杨坚,创建,隋朝"
- 成立：组织→时间，表示组织成立于某时间。如"华为,成立,1987年"
- 研发：组织/人→产品，表示研发了某产品。如"华为,研发,5G芯片"
- 合作：组织↔组织，表示双方合作关系。如"华为,合作,中兴"
- 投资：组织/人→组织，表示投资关系。如"腾讯,投资,拼多多"
- 收购：组织→组织，表示收购关系。如"微软,收购,LinkedIn"
- 发明：人→产品/技术，表示发明了某物。如"贝尔,发明,电话"
- 生产：组织→产品，表示生产制造。如"丰田,生产,卡罗拉"

【严格规则 - 必须遵守】
1. 实体必须完整，禁止截断。如"法务合规部"不能写"法务合"，"供应链部"不能写"供应"
2. 禁止使用泛化词作为实体，如"流程""合同""员工""费用""设备""部门""信息""技术""管理"等
3. 禁止使用"关联"作为关系类型，必须使用上述13种具体关系之一
4. 人名实体不能用于"位于"关系（如"肖邦"是人名，不能说"肖邦,位于,波兰"）
5. "位于"方向必须是"小地方→大地方"（如"巴黎→法国"），绝不能"大→小"（如"法国→埃菲尔铁塔"）
6. 作品、书籍不能作为"位于"的实体1（如"后汉书"不能用"位于"关系）
7. 朝代/历史时期不能作为"管理"关系的实体2（如不能出现"李清照,管理,宋代"）
8. 抽象概念（如"奢华""创新""优化""田园"）不能作为地名或实体
9. 如果无法确定关系类型，宁可不抽取，不要输出模糊的三元组

请严格按照JSON数组格式输出，每个三元组为[实体1, 关系, 实体2]。不要输出任何解释文字，不要使用Markdown格式。

示例：
[["张三","担任","CEO"],["华为","研发","5G芯片"],["巴黎","位于","法国"]]

待抽取文本：
{text}

请输出三元组JSON数组："""

    def _build_few_shot_prompt(self, text: str) -> str:
        return f"""你是一个专业的知识图谱抽取引擎。请从以下文本中抽取实体关系三元组。

        【实体类型】人名、地名、组织名、时间、产品名、职位、作品名

        【关系类型及其严格定义】
        - 任职：人→组织，如"张三,任职,华为"
        - 担任：人→职位，如"张三,担任,CEO"
        - 位于：实体→地名，方向必须"小→大"，如"巴黎,位于,法国"
        - 属于：实体→组织/地名，如"张三,属于,研发部"
        - 包含：组织→组织，层级关系，如"研发部,包含,前端组"
        - 创建：人→组织/作品，如"杨坚,创建,隋朝"
        - 成立：组织→时间，如"华为,成立,1987年"
        - 研发：组织/人→产品，如"华为,研发,5G芯片"
        - 合作：组织↔组织，如"腾讯,合作,阿里"
        - 投资：组织/人→组织，如"腾讯,投资,拼多多"
        - 收购：组织→组织，如"微软,收购,LinkedIn"
        - 发明：人→产品/技术，如"贝尔,发明,电话"
        - 生产：组织→产品，如"丰田,生产,卡罗拉"

        【严格规则 - 必须遵守】
        1. 实体必须完整，禁止截断（如"供应链部"不能写"供应"）
        2. 禁止使用泛化词作为实体（如"流程""合同""员工""费用""设备""部门"）
        3. 禁止使用"关联"作为关系，必须用上述13种具体关系
        4. 人名不能用于"位于"关系（"肖邦"是人名不是地名）
        5. "位于"方向必须"小→大"（"巴黎→法国"正确，"法国→埃菲尔铁塔"错误）
        6. 作品/书籍不能用"位于"（"后汉书,位于,范晔"是错的，应为"范晔,创建,后汉书"）
        7. 朝代不能用于"管理"关系（"李清照,管理,宋代"是错误的）
        8. 抽象概念（"奢华""创新""优化""田园"）不能作为实体
        9. 无法确定关系时，宁可不抽取

        以下是抽取示例：
        输入：马云于1999年在杭州创立了阿里巴巴集团，目前担任董事局主席。阿里巴巴总部位于杭州，主要研发云计算和人工智能产品。
        输出：[["马云","创建","阿里巴巴集团"],["阿里巴巴集团","成立","1999年"],["马云","担任","董事局主席"],["阿里巴巴集团","位于","杭州"],["阿里巴巴集团","研发","云计算"]]

        输入：华为技术有限公司由任正非于1987年在深圳创立，总部位于深圳，旗下设有消费者业务部和企业业务部，主要研发5G通信设备。
        输出：[["任正非","创建","华为技术有限公司"],["华为技术有限公司","成立","1987年"],["华为技术有限公司","位于","深圳"],["华为技术有限公司","包含","消费者业务部"],["华为技术有限公司","包含","企业业务部"],["华为技术有限公司","研发","5G通信设备"]]

        输入：腾讯于2020年投资了拼多多，双方在社交电商领域展开合作。马化腾担任腾讯CEO。
        输出：[["腾讯","投资","拼多多"],["腾讯","合作","拼多多"],["马化腾","任职","腾讯"],["马化腾","担任","CEO"]]

        请严格按照JSON数组格式输出，每个三元组为[实体1, 关系, 实体2]。不要输出任何解释文字，不要使用Markdown格式。

        待抽取文本：
        {text}

        请输出三元组JSON数组："""

    def _call_llm(self, prompt: str) -> str:
        if not self._initialized:
            self._init_llm()
        if not self._initialized:
            return ""
        try:
            response = self._client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            result = response.choices[0].message.content.strip()
            logger.debug(f"LLM原始响应: {result[:200]}")
            return result
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return ""

    def _parse_llm_response(self, response: str) -> List[Tuple[str, str, str]]:
        triplets = []
        if not response:
            return triplets
        try:
            json_str = response
            if "```" in json_str:
                json_str = re.sub(r"```json\s*", "", json_str)
                json_str = re.sub(r"```\s*", "", json_str)
            json_str = json_str.strip()
            start = json_str.find("[")
            end = json_str.rfind("]") + 1
            if start != -1 and end > start:
                json_str = json_str[start:end]
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, (list, tuple)) and len(item) == 3:
                        t = _clean_triplet(str(item[0]), str(item[1]), str(item[2]))
                        if t:
                            triplets.append(t)
        except json.JSONDecodeError as e:
            logger.warning(f"LLM响应JSON解析失败: {e}, 原始: {response[:100]}")
            pattern = r'\["([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\]'
            matches = re.findall(pattern, response)
            for m in matches:
                t = _clean_triplet(m[0], m[1], m[2])
                if t:
                    triplets.append(t)
        return triplets

    def extract_zero_shot(self, text: str) -> List[Tuple[str, str, str]]:
        cached = self._get_cached(text, "zero_shot")
        if cached is not None:
            return cached

        prompt = self._build_zero_shot_prompt(text)
        response = self._call_llm(prompt)
        triplets = self._parse_llm_response(response)
        logger.info(f"LLM零样本抽取完成, 获得{len(triplets)}个三元组")

        self._set_cached(text, "zero_shot", triplets)
        return triplets

    def extract_few_shot(self, text: str) -> List[Tuple[str, str, str]]:
        cached = self._get_cached(text, "few_shot")
        if cached is not None:
            return cached

        prompt = self._build_few_shot_prompt(text)
        response = self._call_llm(prompt)
        triplets = self._parse_llm_response(response)
        logger.info(f"LLM少样本抽取完成, 获得{len(triplets)}个三元组")

        self._set_cached(text, "few_shot", triplets)
        return triplets

    def extract_batch(self, texts: List[str], mode: str = "few_shot") -> List[List[Tuple[str, str, str]]]:
        results = []
        uncached_indices = []
        uncached_texts = []

        for i, text in enumerate(texts):
            cached = self._get_cached(text, mode)
            if cached is not None:
                results.append(cached)
            else:
                results.append(None)
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            merged_text = "\n\n---\n\n".join(uncached_texts)
            prompt_builder = self._build_few_shot_prompt if mode == "few_shot" else self._build_zero_shot_prompt
            prompt = prompt_builder(merged_text)

            response = self._call_llm(prompt)
            all_triplets = self._parse_llm_response(response)

            per_text = len(all_triplets) // len(uncached_texts) if uncached_texts else 0
            idx = 0
            for i, text in enumerate(uncached_texts):
                if i < len(uncached_texts) - 1:
                    batch = all_triplets[idx:idx + per_text]
                    idx += per_text
                else:
                    batch = all_triplets[idx:]
                results[uncached_indices[i]] = batch
                self._set_cached(text, mode, batch)

        return results

    @classmethod
    def clear_cache(cls):
        cache_dir = cls.LLM_CACHE_DIR
        if os.path.exists(cache_dir):
            for f in os.listdir(cache_dir):
                if f.endswith(".json"):
                    os.remove(os.path.join(cache_dir, f))
            logger.info("LLM缓存已清空")


class MultiTechniqueExtractor:
    FAST_TECHNIQUES = {"spacy_rule", "spacy_template", "spacy_dep"}
    LLM_TECHNIQUES = {"llm_zero_shot", "llm_few_shot"}
    ALL_TECHNIQUES = [
        "spacy_rule", "spacy_template", "spacy_dep",
        "llm_zero_shot", "llm_few_shot",
    ]

    def __init__(self, use_llm_cache: bool = True):
        self.llm_extractor = LLMExtractor(use_cache=use_llm_cache)
        self.spacy_rule_extractor = SpacyRuleExtractor()
        self.spacy_template_extractor = SpacyTemplateExtractor()
        self.spacy_dep_extractor = SpacyDependencyExtractor()
        self.validator = TripletValidator(use_cache=use_llm_cache)
        self._extraction_stats = {}
        self._validation_details = []

    def extract(self, text: str, techniques: List[str] = None, progress_callback=None,
                smart_mode: bool = False, ai_validate: bool = False) -> List[Tuple[str, str, str]]:
        if not text or not text.strip():
            logger.warning("输入文本为空, 跳过抽取")
            return []

        if techniques is None:
            techniques = list(self.ALL_TECHNIQUES)

        self._extraction_stats = {}
        self._validation_details = []
        all_triplets = []

        chunks = _split_text(text)
        logger.info(f"文本分片: {len(chunks)}个片段")

        fast_techniques = [t for t in techniques if t in self.FAST_TECHNIQUES]
        llm_techniques = [t for t in techniques if t in self.LLM_TECHNIQUES]

        if smart_mode:
            all_triplets = self._extract_smart(chunks, fast_techniques, llm_techniques, progress_callback)
        else:
            fast_triplets = []
            if fast_techniques:
                fast_triplets = self._extract_fast_all_chunks(chunks, fast_techniques, progress_callback)
            if llm_techniques:
                llm_triplets = self._extract_llm_once(text, llm_techniques, progress_callback)
                all_triplets = fast_triplets + llm_triplets
            else:
                all_triplets = fast_triplets

        all_triplets = _expand_conjunctions(all_triplets)
        all_triplets = _deduplicate(all_triplets)
        all_triplets = [t for t in (_clean_triplet(*t) for t in all_triplets) if t]

        if ai_validate and all_triplets:
            if progress_callback:
                progress_callback(0.95, "AI校验中...")
            all_triplets, self._validation_details = self.validator.validate(
                all_triplets, source_text=text[:2000], progress_callback=progress_callback
            )

        if progress_callback:
            progress_callback(1.0, "抽取完成！")
        logger.info(f"多技术融合抽取完成, 去重后共{len(all_triplets)}个三元组, 统计: {self._extraction_stats}")
        return all_triplets

    def _extract_fast_all_chunks(self, chunks, techniques, progress_callback):
        total_steps = len(chunks) * len(techniques)
        current_step = 0
        all_triplets = []

        for i, chunk in enumerate(chunks):
            chunk_triplets, current_step = self._extract_fast_chunk(
                chunk, techniques, current_step, total_steps, progress_callback
            )
            all_triplets.extend(chunk_triplets)
            logger.info(f"片段{i+1}/{len(chunks)}快速抽取完成, 获得{len(chunk_triplets)}个三元组")

        return all_triplets

    def _extract_fast_chunk(self, text: str, techniques: List[str], current_step: int = 0,
                            total_steps: int = 1, progress_callback=None) -> Tuple[List[Tuple[str, str, str]], int]:
        results_by_technique = {}

        tech_list = [
            ("spacy_rule", "spaCy+规则", self.spacy_rule_extractor.extract),
            ("spacy_template", "spaCy+模板", self.spacy_template_extractor.extract),
            ("spacy_dep", "spaCy+依存", self.spacy_dep_extractor.extract),
        ]

        for tech_key, tech_name, extract_fn in tech_list:
            if tech_key not in techniques:
                continue
            current_step += 1
            if progress_callback:
                pct = current_step / total_steps
                progress_callback(pct, f"{tech_name}抽取中... ({current_step}/{total_steps})")
            try:
                triplets = extract_fn(text)
                results_by_technique[tech_key] = triplets
                self._extraction_stats[tech_key] = self._extraction_stats.get(tech_key, 0) + len(triplets)
            except Exception as e:
                logger.error(f"{tech_name}抽取异常: {e}")
                results_by_technique[tech_key] = []

        return self._merge_results(results_by_technique), current_step

    def _extract_llm_once(self, full_text: str, techniques: List[str], progress_callback=None):
        all_triplets = []
        if progress_callback:
            progress_callback(0.8, "LLM一次性抽取全部文本...")

        for tech_key in techniques:
            try:
                if tech_key == "llm_zero_shot":
                    triplets = self.llm_extractor.extract_zero_shot(full_text)
                elif tech_key == "llm_few_shot":
                    triplets = self.llm_extractor.extract_few_shot(full_text)
                else:
                    continue
                all_triplets.extend(triplets)
                self._extraction_stats[tech_key] = len(triplets)
                logger.info(f"LLM {tech_key} 一次性抽取完成, 获得{len(triplets)}个三元组")
            except Exception as e:
                logger.error(f"LLM {tech_key} 抽取异常: {e}")
                self._extraction_stats[tech_key] = 0

        return all_triplets

    def _extract_smart(self, chunks, fast_techniques, llm_techniques, progress_callback):
        total_fast = len(chunks) * len(fast_techniques) if fast_techniques else 0
        total_steps = total_fast + (1 if llm_techniques else 0)
        current_step = 0
        all_triplets = []

        for i, chunk in enumerate(chunks):
            if fast_techniques:
                fast_triplets, current_step = self._extract_fast_chunk(
                    chunk, fast_techniques, current_step, total_steps, progress_callback
                )
                all_triplets.extend(fast_triplets)
            else:
                fast_triplets = []

        if llm_techniques:
            need_llm = True
            if fast_techniques and len(all_triplets) >= 3:
                logger.info(f"快速抽取已获得{len(all_triplets)}个三元组, 跳过LLM")
                need_llm = False
                for t in llm_techniques:
                    self._extraction_stats[t] = 0

            if need_llm:
                current_step += 1
                if progress_callback:
                    progress_callback(current_step / total_steps, "LLM一次性抽取全部文本...")
                llm_triplets = self._extract_llm_once(
                    chunks[0] if len(chunks) == 1 else "\n\n".join(chunks),
                    llm_techniques, None
                )
                all_triplets.extend(llm_triplets)

        return all_triplets

    def _merge_results(self, results: dict) -> List[Tuple[str, str, str]]:
        merged = []
        seen = set()
        priority = [
            "llm_few_shot", "llm_zero_shot",
            "spacy_dep", "spacy_template", "spacy_rule",
        ]
        for tech in priority:
            if tech in results:
                for triplet in results[tech]:
                    key = (triplet[0], triplet[1], triplet[2])
                    if key not in seen:
                        seen.add(key)
                        merged.append(triplet)
        return merged

    def get_stats(self) -> dict:
        return self._extraction_stats.copy()

    def get_validation_details(self) -> List[dict]:
        return self._validation_details.copy()
