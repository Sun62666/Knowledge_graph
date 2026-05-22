import os
import json
import hashlib
from typing import List, Tuple, Optional
from utils.logger import get_logger
from utils.config import (
    LLM_API_KEY,
    LLM_MODEL_NAME,
    LLM_BASE_URL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    CACHE_DIR,
)

logger = get_logger()


class TripletValidator:
    VALIDATOR_CACHE_DIR = os.path.join(CACHE_DIR, "validator_responses")

    def __init__(self, use_cache: bool = True):
        self._client = None
        self._initialized = False
        self._use_cache = use_cache
        if use_cache:
            os.makedirs(self.VALIDATOR_CACHE_DIR, exist_ok=True)

    def _init_llm(self):
        if self._initialized:
            return
        if LLM_API_KEY == "your_api_key":
            logger.warning("LLM API密钥未配置, AI校验不可用")
            return
        try:
            import openai
            self._client = openai.OpenAI(
                api_key=LLM_API_KEY,
                base_url=LLM_BASE_URL,
            )
            self._initialized = True
            logger.info(f"AI校验LLM初始化成功, 模型: {LLM_MODEL_NAME}")
        except ImportError:
            logger.warning("openai库未安装, AI校验不可用")
        except Exception as e:
            logger.error(f"AI校验LLM初始化失败: {e}")

    def _cache_key(self, triplets_hash: str) -> str:
        raw = f"validator:{LLM_MODEL_NAME}:{triplets_hash}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _get_cached(self, triplets_hash: str) -> Optional[List[dict]]:
        if not self._use_cache:
            return None
        key = self._cache_key(triplets_hash)
        path = os.path.join(self.VALIDATOR_CACHE_DIR, f"{key}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"AI校验缓存命中")
                return data
            except Exception as e:
                logger.warning(f"AI校验缓存读取失败: {e}")
        return None

    def _set_cached(self, triplets_hash: str, results: List[dict]):
        if not self._use_cache:
            return
        key = self._cache_key(triplets_hash)
        path = os.path.join(self.VALIDATOR_CACHE_DIR, f"{key}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"AI校验缓存写入失败: {e}")

    def _build_prompt(self, triplets: List[Tuple[str, str, str]], source_text: str = "") -> str:
        triplet_lines = []
        for i, (e1, rel, e2) in enumerate(triplets):
            triplet_lines.append(f"{i+1}. [{e1}, {rel}, {e2}]")

        source_section = ""
        if source_text:
            source_section = f"\n原始文本片段：\n{source_text[:1000]}\n"

        return f"""你是一个知识图谱质量校验专家。请对以下抽取出的三元组逐一严格校验。

        【校验标准 - 必须逐条检查】

        1. 实体完整性：
           - 实体不能是截断的片段。如"法务合"应为"法务合规部"，"供应"应为"供应链部"，"张三隶"应为"张三"
           - 实体不能包含关系动词或介词前缀。如"张三隶"中的"隶"属于"隶属"的截断

        2. 实体有效性：
           - 泛化词不能作为实体："流程""合同""员工""费用""设备""部门""信息""技术""管理""平台""系统"等
           - 抽象概念不能作为地名或组织名："奢华""创新""优化""田园""效率""效益"等
           - 人名实体不能出现在"位于"关系的实体1位置（如"肖邦,位于,波兰"错误，肖邦是人名）

        3. 关系合理性：
           - 禁止使用"关联"关系，必须用具体关系（任职/位于/属于/创建/包含等）
           - "位于"方向必须是"小→大"（如"巴黎→法国"正确，"法国→埃菲尔铁塔"错误）
           - "创建"方向必须是"人→组织/作品"（如"杨坚→隋朝"正确，"史记→西汉史学家"方向错误）
           - "管理"不能用于人与朝代/流派的关系（如"李清照,管理,宋代"错误）
           - "成立"的实体1必须是组织，不能是人名（如"贝尔德,成立,1925年"错误）
           - 作品/书籍不能用"位于"（如"后汉书,位于,南朝宋范晔"错误，应为"范晔,创建,后汉书"）

        4. 方向正确性：
           - "位于"：小地方→大地名，不能反过来
           - "创建"：人→组织/作品，不能反过来
           - "包含"：整体→部分，不能反过来
           - "属于"：部分→整体，不能反过来
        {source_section}
        待校验三元组：
        {chr(10).join(triplet_lines)}

        请对每个三元组给出校验结果，格式为JSON数组，每个元素包含：
        - "index": 序号（从1开始）
        - "valid": true或false
        - "reason": 如果不通过，给出具体违反的规则编号和原因（简短，如"规则3：位于方向错误，应为小→大"）
        - "correction": 如果valid为false但可以修正，给出修正后的[实体1, 关系, 实体2]；无法修正则为null

        请严格输出JSON数组，不要输出其他内容："""

    def _call_llm(self, prompt: str) -> str:
        if not self._initialized:
            self._init_llm()
        if not self._initialized:
            return ""
        try:
            response = self._client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=LLM_MAX_TOKENS,
            )
            result = response.choices[0].message.content.strip()
            return result
        except Exception as e:
            logger.error(f"AI校验LLM调用失败: {e}")
            return ""

    def _parse_response(self, response: str) -> List[dict]:
        if not response:
            return []
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
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"AI校验响应解析失败: {e}")
            return []

    def validate(
        self,
        triplets: List[Tuple[str, str, str]],
        source_text: str = "",
        progress_callback=None,
    ) -> Tuple[List[Tuple[str, str, str]], List[dict]]:
        if not triplets:
            return [], []

        if not self._initialized:
            self._init_llm()
        if not self._initialized:
            logger.warning("AI校验不可用, 返回原始数据")
            return triplets, []

        triplets_str = json.dumps(triplets, ensure_ascii=False)
        triplets_hash = hashlib.md5(triplets_str.encode("utf-8")).hexdigest()

        cached = self._get_cached(triplets_hash)
        if cached is not None:
            results = cached
        else:
            if progress_callback:
                progress_callback(0.5, "AI校验中（一次性校验全部数据）...")
            prompt = self._build_prompt(triplets, source_text)
            response = self._call_llm(prompt)
            results = self._parse_response(response)
            if results:
                self._set_cached(triplets_hash, results)

        all_validated = []
        all_details = []
        validated_indices = set()

        for item in results:
            idx = item.get("index", 0) - 1
            if 0 <= idx < len(triplets):
                validated_indices.add(idx)
                detail = {
                    "original": list(triplets[idx]),
                    "valid": item.get("valid", True),
                    "reason": item.get("reason", ""),
                    "correction": item.get("correction"),
                }
                all_details.append(detail)

                if item.get("valid", True):
                    all_validated.append(triplets[idx])
                elif item.get("correction"):
                    corr = item["correction"]
                    if isinstance(corr, list) and len(corr) == 3:
                        all_validated.append(tuple(corr))

        for i, t in enumerate(triplets):
            if i not in validated_indices:
                all_validated.append(t)

        seen = set()
        unique_validated = []
        for t in all_validated:
            key = (t[0], t[1], t[2])
            if key not in seen:
                seen.add(key)
                unique_validated.append(t)

        logger.info(
            f"AI校验完成: 原始{len(triplets)}个, 校验后{len(unique_validated)}个, "
            f"过滤{len(triplets) - len(unique_validated)}个"
        )
        logger.debug(f"校验后数据为： {unique_validated} 所有细节： {all_details}")
        return unique_validated, all_details

    @classmethod
    def clear_cache(cls):
        cache_dir = cls.VALIDATOR_CACHE_DIR
        if os.path.exists(cache_dir):
            for f in os.listdir(cache_dir):
                if f.endswith(".json"):
                    os.remove(os.path.join(cache_dir, f))
            logger.info("AI校验缓存已清空")


import re