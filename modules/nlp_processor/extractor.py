import re
import json
import hashlib
from typing import List, Tuple, Optional
from utils.logger import get_logger
from utils.config import (
    RULE_PATTERNS,
    TEMPLATE_PATTERNS,
    ENTITY_TYPES,
    RELATION_TYPES,
    LLM_API_KEY,
    LLM_MODEL_NAME,
    LLM_BASE_URL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)

logger = get_logger()


def _clean_triplet(e1: str, rel: str, e2: str) -> Optional[Tuple[str, str, str]]:
    e1 = _clean_entity(e1)
    rel = rel.strip()
    e2 = _clean_entity(e2)
    if not e1 or not rel or not e2:
        return None
    if len(e1) > 50 or len(e2) > 50:
        return None
    for ch in ['"', "'", "\n", "\r", "\t"]:
        e1 = e1.replace(ch, "")
        e2 = e2.replace(ch, "")
        rel = rel.replace(ch, "")
    return (e1, rel, e2)


def _deduplicate(triplets: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    seen = set()
    result = []
    for t in triplets:
        key = (t[0], t[1], t[2])
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
    return [p.strip() for p in parts if p.strip()]


_ENTITY_PREFIX_NOISE = re.compile(r'^[由被将从在对于以和与及跟向从到往经过通过按照根据]')
_ENTITY_INFIX_NOISE = re.compile(r'于\d{1,4}年\d{0,2}月?\d{0,2}日?[前后]?在[\u4e00-\u9fff]{1,6}|于\d{1,4}年\d{0,2}月?\d{0,2}日?[前后]?')


def _clean_entity(entity: str) -> str:
    entity = entity.strip()
    if re.match(r'^\d{1,4}年\d{0,2}月?\d{0,2}日?[前后]?$', entity):
        return entity
    while entity and _ENTITY_PREFIX_NOISE.match(entity):
        entity = entity[1:].strip()
    entity = _ENTITY_INFIX_NOISE.sub('', entity).strip()
    while entity and _ENTITY_PREFIX_NOISE.match(entity):
        entity = entity[1:].strip()
    entity = re.sub(r'^\d{1,4}年\d{0,2}月?\d{0,2}日?[前后]?', '', entity).strip()
    entity = re.sub(r'^在[\u4e00-\u9fff]{1,6}', '', entity).strip()
    while entity and _ENTITY_PREFIX_NOISE.match(entity):
        entity = entity[1:].strip()
    return entity


class RuleBasedExtractor:
    def __init__(self):
        self.patterns = RULE_PATTERNS

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        triplets = []
        sentences = _split_sentences(text)
        for sentence in sentences:
            for rel, pattern_list in self.patterns.items():
                for pattern in pattern_list:
                    try:
                        matches = re.findall(pattern, sentence)
                        for match in matches:
                            if isinstance(match, tuple):
                                if len(match) == 3:
                                    t = _clean_triplet(match[0], rel, match[2])
                                    if t:
                                        triplets.append(t)
                                elif len(match) == 2:
                                    t = _clean_triplet(match[0], rel, match[1])
                                    if t:
                                        triplets.append(t)
                            elif isinstance(match, str):
                                t = _clean_triplet(match, rel, "")
                                if t and t[2]:
                                    triplets.append(t)
                    except Exception as e:
                        logger.debug(f"规则匹配异常: {pattern}, 错误: {e}")
        logger.info(f"规则抽取完成, 获得{len(triplets)}个三元组")
        return triplets


class TemplateBasedExtractor:
    def __init__(self):
        self.templates = TEMPLATE_PATTERNS

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        triplets = []
        sentences = _split_sentences(text)
        for sentence in sentences:
            for tmpl in self.templates:
                pattern = tmpl["pattern"]
                rel = tmpl["relation"]
                if "总部" in pattern:
                    e1_pattern = r"([\u4e00-\u9fff\w]{3,}?)"
                else:
                    e1_pattern = r"([\u4e00-\u9fff\w]+?)"
                e2_pattern = r"([\u4e00-\u9fff\w]+?)"
                regex = pattern.replace("{entity1}", e1_pattern).replace("{entity2}", e2_pattern)
                regex = regex + r"(?=[，。；\n,;]|$)"
                try:
                    matches = re.findall(regex, sentence)
                    for match in matches:
                        if isinstance(match, tuple) and len(match) >= 2:
                            t = _clean_triplet(match[0], rel, match[1])
                            if t:
                                triplets.append(t)
                except Exception as e:
                    logger.debug(f"模板匹配异常: {pattern}, 错误: {e}")
        logger.info(f"模板抽取完成, 获得{len(triplets)}个三元组")
        return triplets


class TraditionalMLExtractor:
    def __init__(self):
        self._model = None
        self._vectorizer = None
        self._trained = False

    def _init_model(self):
        try:
            from sklearn.svm import SVC
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(max_features=5000)
            self._model = SVC(kernel="linear", probability=True)
            self._trained = False
            logger.info("传统ML模型(SVM)初始化成功")
        except ImportError:
            logger.warning("sklearn未安装, 传统ML抽取不可用")

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        if self._vectorizer is None:
            self._init_model()
        if not self._trained:
            logger.info("传统ML模型未训练, 跳过ML抽取")
            return []
        triplets = []
        logger.info(f"传统ML抽取完成, 获得{len(triplets)}个三元组")
        return triplets

    def train(self, texts: List[str], labels: List[str]):
        if self._vectorizer is None:
            self._init_model()
        try:
            X = self._vectorizer.fit_transform(texts)
            self._model.fit(X, labels)
            self._trained = True
            logger.info("传统ML模型训练完成")
        except Exception as e:
            logger.error(f"传统ML模型训练失败: {e}")


class DeepLearningExtractor:
    def __init__(self):
        self._bilstm_model = None
        self._cnn_model = None
        self._bilstm_crf_model = None
        self._trained = False

    def _init_models(self):
        try:
            import torch
            import torch.nn as nn
            logger.info("深度学习框架(PyTorch)可用")
        except ImportError:
            logger.warning("PyTorch未安装, 深度学习抽取不可用")

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        if not self._trained:
            logger.info("深度学习模型未训练, 跳过DL抽取")
            return []
        triplets = []
        logger.info(f"深度学习抽取完成, 获得{len(triplets)}个三元组")
        return triplets


class PretrainedModelExtractor:
    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._loaded = False

    def _load_model(self):
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification
            model_name = "bert-base-chinese"
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForTokenClassification.from_pretrained(model_name)
            self._loaded = True
            logger.info(f"预训练模型({model_name})加载成功")
        except ImportError:
            logger.warning("transformers未安装, 预训练模型抽取不可用")
        except Exception as e:
            logger.warning(f"预训练模型加载失败: {e}")

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        if not self._loaded:
            logger.info("预训练模型未加载, 跳过预训练模型抽取")
            return []
        triplets = []
        logger.info(f"预训练模型抽取完成, 获得{len(triplets)}个三元组")
        return triplets


class LLMExtractor:
    def __init__(self):
        self._client = None
        self._initialized = False

    def _init_client(self):
        if LLM_API_KEY == "your_api_key":
            logger.warning("LLM API密钥未配置, LLM抽取不可用")
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=LLM_API_KEY,
                base_url=LLM_BASE_URL,
            )
            self._initialized = True
            logger.info(f"LLM客户端初始化成功, 模型: {LLM_MODEL_NAME}")
        except ImportError:
            logger.warning("openai库未安装, LLM抽取不可用")
        except Exception as e:
            logger.error(f"LLM客户端初始化失败: {e}")

    def _build_zero_shot_prompt(self, text: str) -> str:
        return f"""你是一个专业的企业知识图谱抽取引擎。请从以下企业文档文本中抽取实体关系三元组。

实体类型包括：人名、地名、组织名、时间、产品名、职位、事件
关系类型包括：任职、位于、研发、合作、成立、属于、投资、收购、生产、担任、创建、包含、关联、竞争

请严格按照JSON数组格式输出三元组，每个三元组为[实体1, 关系, 实体2]。不要输出任何解释文字、不要使用Markdown格式。

示例输出：
[["张三","担任","CEO"],["华为","研发","5G芯片"]]

待抽取文本：
{text}

请输出三元组JSON数组："""

    def _build_few_shot_prompt(self, text: str) -> str:
        return f"""你是一个专业的企业知识图谱抽取引擎。请从以下企业文档文本中抽取实体关系三元组。

实体类型包括：人名、地名、组织名、时间、产品名、职位、事件
关系类型包括：任职、位于、研发、合作、成立、属于、投资、收购、生产、担任、创建、包含、关联、竞争

以下是几个抽取示例：
输入：马云于1999年在杭州创立了阿里巴巴集团，目前担任董事局主席。
输出：[["马云","创建","阿里巴巴集团"],["阿里巴巴集团","位于","杭州"],["马云","担任","董事局主席"]]

输入：华为技术有限公司总部位于深圳，由任正非于1987年创立，主要研发5G通信设备。
输出：[["华为技术有限公司","位于","深圳"],["任正非","创建","华为技术有限公司"],["华为技术有限公司","研发","5G通信设备"]]

输入：腾讯于2020年投资了字节跳动，双方在云计算领域展开合作。
输出：[["腾讯","投资","字节跳动"],["腾讯","合作","字节跳动"]]

请严格按照JSON数组格式输出三元组，每个三元组为[实体1, 关系, 实体2]。不要输出任何解释文字、不要使用Markdown格式。

待抽取文本：
{text}

请输出三元组JSON数组："""

    def _call_llm(self, prompt: str) -> str:
        if not self._initialized:
            self._init_client()
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
        prompt = self._build_zero_shot_prompt(text)
        response = self._call_llm(prompt)
        triplets = self._parse_llm_response(response)
        logger.info(f"LLM零样本抽取完成, 获得{len(triplets)}个三元组")
        return triplets

    def extract_few_shot(self, text: str) -> List[Tuple[str, str, str]]:
        prompt = self._build_few_shot_prompt(text)
        response = self._call_llm(prompt)
        triplets = self._parse_llm_response(response)
        logger.info(f"LLM少样本抽取完成, 获得{len(triplets)}个三元组")
        return triplets


class RemoteSupervisionExtractor:
    def __init__(self):
        self._knowledge_base = {}

    def load_knowledge_base(self, kb_data: dict):
        self._knowledge_base = kb_data
        logger.info(f"远程监督知识库加载完成, 共{len(kb_data)}条记录")

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        triplets = []
        for entity, relations in self._knowledge_base.items():
            if entity in text:
                for rel, target in relations:
                    if target in text:
                        t = _clean_triplet(entity, rel, target)
                        if t:
                            triplets.append(t)
        logger.info(f"远程监督抽取完成, 获得{len(triplets)}个三元组")
        return triplets


class KnowledgeDistillationExtractor:
    def __init__(self):
        self._teacher_model = None
        self._student_model = None
        self._trained = False

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        if not self._trained:
            logger.info("知识蒸馏模型未训练, 跳过知识蒸馏抽取")
            return []
        triplets = []
        logger.info(f"知识蒸馏抽取完成, 获得{len(triplets)}个三元组")
        return triplets


class JointEntityRelationExtractor:
    def __init__(self):
        self._model = None
        self._trained = False

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        if not self._trained:
            logger.info("联合抽取模型未训练, 跳过联合实体关系抽取")
            return []
        triplets = []
        logger.info(f"联合实体关系抽取完成, 获得{len(triplets)}个三元组")
        return triplets


class MultiTechniqueExtractor:
    def __init__(self):
        self.rule_extractor = RuleBasedExtractor()
        self.template_extractor = TemplateBasedExtractor()
        self.ml_extractor = TraditionalMLExtractor()
        self.dl_extractor = DeepLearningExtractor()
        self.pretrained_extractor = PretrainedModelExtractor()
        self.llm_extractor = LLMExtractor()
        self.remote_supervision_extractor = RemoteSupervisionExtractor()
        self.distillation_extractor = KnowledgeDistillationExtractor()
        self.joint_extractor = JointEntityRelationExtractor()
        self._extraction_stats = {}

    def extract(self, text: str, techniques: List[str] = None) -> List[Tuple[str, str, str]]:
        if not text or not text.strip():
            logger.warning("输入文本为空, 跳过抽取")
            return []

        all_techniques = [
            "rule", "template", "traditional_ml", "deep_learning",
            "pretrained_model", "llm_zero_shot", "llm_few_shot",
            "remote_supervision", "knowledge_distillation", "joint_extraction",
        ]
        if techniques is None:
            techniques = all_techniques

        self._extraction_stats = {}
        all_triplets = []

        chunks = _split_text(text)
        logger.info(f"文本分片: {len(chunks)}个片段")

        for i, chunk in enumerate(chunks):
            chunk_triplets = self._extract_chunk(chunk, techniques)
            all_triplets.extend(chunk_triplets)
            logger.info(f"片段{i+1}/{len(chunks)}抽取完成, 获得{len(chunk_triplets)}个三元组")

        all_triplets = _deduplicate(all_triplets)
        logger.info(f"多技术融合抽取完成, 去重后共{len(all_triplets)}个三元组, 统计: {self._extraction_stats}")
        return all_triplets

    def _extract_chunk(self, text: str, techniques: List[str]) -> List[Tuple[str, str, str]]:
        results_by_technique = {}

        if "rule" in techniques:
            try:
                triplets = self.rule_extractor.extract(text)
                results_by_technique["rule"] = triplets
                self._extraction_stats["rule"] = len(triplets)
            except Exception as e:
                logger.error(f"规则抽取异常: {e}")
                results_by_technique["rule"] = []

        if "template" in techniques:
            try:
                triplets = self.template_extractor.extract(text)
                results_by_technique["template"] = triplets
                self._extraction_stats["template"] = len(triplets)
            except Exception as e:
                logger.error(f"模板抽取异常: {e}")
                results_by_technique["template"] = []

        if "traditional_ml" in techniques:
            try:
                triplets = self.ml_extractor.extract(text)
                results_by_technique["traditional_ml"] = triplets
                self._extraction_stats["traditional_ml"] = len(triplets)
            except Exception as e:
                logger.error(f"传统ML抽取异常: {e}")
                results_by_technique["traditional_ml"] = []

        if "deep_learning" in techniques:
            try:
                triplets = self.dl_extractor.extract(text)
                results_by_technique["deep_learning"] = triplets
                self._extraction_stats["deep_learning"] = len(triplets)
            except Exception as e:
                logger.error(f"深度学习抽取异常: {e}")
                results_by_technique["deep_learning"] = []

        if "pretrained_model" in techniques:
            try:
                triplets = self.pretrained_extractor.extract(text)
                results_by_technique["pretrained_model"] = triplets
                self._extraction_stats["pretrained_model"] = len(triplets)
            except Exception as e:
                logger.error(f"预训练模型抽取异常: {e}")
                results_by_technique["pretrained_model"] = []

        if "llm_zero_shot" in techniques:
            try:
                triplets = self.llm_extractor.extract_zero_shot(text)
                results_by_technique["llm_zero_shot"] = triplets
                self._extraction_stats["llm_zero_shot"] = len(triplets)
            except Exception as e:
                logger.error(f"LLM零样本抽取异常: {e}")
                results_by_technique["llm_zero_shot"] = []

        if "llm_few_shot" in techniques:
            try:
                triplets = self.llm_extractor.extract_few_shot(text)
                results_by_technique["llm_few_shot"] = triplets
                self._extraction_stats["llm_few_shot"] = len(triplets)
            except Exception as e:
                logger.error(f"LLM少样本抽取异常: {e}")
                results_by_technique["llm_few_shot"] = []

        if "remote_supervision" in techniques:
            try:
                triplets = self.remote_supervision_extractor.extract(text)
                results_by_technique["remote_supervision"] = triplets
                self._extraction_stats["remote_supervision"] = len(triplets)
            except Exception as e:
                logger.error(f"远程监督抽取异常: {e}")
                results_by_technique["remote_supervision"] = []

        if "knowledge_distillation" in techniques:
            try:
                triplets = self.distillation_extractor.extract(text)
                results_by_technique["knowledge_distillation"] = triplets
                self._extraction_stats["knowledge_distillation"] = len(triplets)
            except Exception as e:
                logger.error(f"知识蒸馏抽取异常: {e}")
                results_by_technique["knowledge_distillation"] = []

        if "joint_extraction" in techniques:
            try:
                triplets = self.joint_extractor.extract(text)
                results_by_technique["joint_extraction"] = triplets
                self._extraction_stats["joint_extraction"] = len(triplets)
            except Exception as e:
                logger.error(f"联合抽取异常: {e}")
                results_by_technique["joint_extraction"] = []

        return self._merge_results(results_by_technique)

    def _merge_results(self, results: dict) -> List[Tuple[str, str, str]]:
        merged = []
        seen = set()
        priority = [
            "llm_zero_shot", "llm_few_shot", "pretrained_model",
            "deep_learning", "traditional_ml", "template", "rule",
            "remote_supervision", "knowledge_distillation", "joint_extraction",
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
