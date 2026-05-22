import os
from dotenv import load_dotenv
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ENV_PATH = os.path.join(BASE_DIR,".env")
load_dotenv(ENV_PATH)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://192.168.100.128:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

LLM_API_KEY = os.getenv("OPENAI_API_KEY", "your_api_key")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "qwen3.5-plus-2026-04-20")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

CSV_FILE_PATH = os.path.join(DATA_DIR, "triplets.csv")
CQL_FILE_PATH = os.path.join(DATA_DIR, "import_cypher.cql")
LOG_FILE_PATH = os.path.join(DATA_DIR, "app.log")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "5000"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "2000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

SUPPORTED_FILE_TYPES = ["txt", "pdf", "docx"]

ENTITY_TYPES = ["人名", "地名", "组织名", "时间", "产品名", "职位", "事件", "作品名", "化学式"]
RELATION_TYPES = [
    "任职", "位于", "研发", "合作", "成立", "属于", "投资",
    "收购", "生产", "担任", "创建", "包含", "关联", "竞争",
    "发明", "著有", "发现", "组成", "代表作",
]

# 基于规则的知识匹配
RULE_PATTERNS = {
    "任职": [
        r"([\u4e00-\u9fff\w]{2,8})担任([\u4e00-\u9fff\w]{2,10})的([\u4e00-\u9fff\w]{2,10})",
        r"([\u4e00-\u9fff\w]{2,8})出任([\u4e00-\u9fff\w]{2,10})的([\u4e00-\u9fff\w]{2,10})",
        r"([\u4e00-\u9fff\w]{2,8})担任([\u4e00-\u9fff\w]{2,10})",
    ],
    "位于": [
        r"([\u4e00-\u9fff\w]{2,15}?)总部位于([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,15}?)坐落于([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,8}?)是([\u4e00-\u9fff\w]{2,8}?)的首都",
        r"([\u4e00-\u9fff\w]{2,8}?)是([\u4e00-\u9fff\w]{2,8}?)的省会",
    ],
    "研发": [
        r"([\u4e00-\u9fff\w]{2,15}?)研发了([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,15}?)开发了([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,15}?)推出了([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
    ],
    "合作": [
        r"([\u4e00-\u9fff\w]{2,15}?)与([\u4e00-\u9fff\w]{2,15}?)合作",
        r"([\u4e00-\u9fff\w]{2,15}?)和([\u4e00-\u9fff\w]{2,15}?)联合",
    ],
    "成立": [
        r"([\u4e00-\u9fff\w]{2,15}?)成立于([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,15}?)创立于([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
    ],
    "属于": [
        r"([\u4e00-\u9fff\w]{2,15}?)属于([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,15}?)隶属于([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
    ],
    "投资": [
        r"([\u4e00-\u9fff\w]{2,15}?)投资了([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
    ],
    "创建": [
        r"([\u4e00-\u9fff\w]{2,8}?)创立了([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,8}?)创办了([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,8}?)创建了([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,8}?)建立([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
    ],
    "创建_reverse": [
        r"([\u4e00-\u9fff\w]{2,15}?)由([\u4e00-\u9fff\w]{2,8}?)创立(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,15}?)由([\u4e00-\u9fff\w]{2,8}?)创办(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,15}?)由([\u4e00-\u9fff\w]{2,8}?)创建(?=[，。；\n,;]|$)",
    ],
    "发明": [
        r"([\u4e00-\u9fff\w]{2,8}?)发明了([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
    ],
    "著有": [
        r"([\u4e00-\u9fff\w]{2,8}?)著有《([\u4e00-\u9fff\w]{2,20}?)》",
        r"([\u4e00-\u9fff\w]{2,8}?)撰写了《([\u4e00-\u9fff\w]{2,20}?)》",
        r"([\u4e00-\u9fff\w]{2,8}?)编纂了《([\u4e00-\u9fff\w]{2,20}?)》",
    ],
    "发现": [
        r"([\u4e00-\u9fff\w]{2,8}?)发现了([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
    ],
    "组成": [
        r"([\u4e00-\u9fff\w]{2,15}?)由([\u4e00-\u9fff\w]{2,15}?)组成",
    ],
    "生产": [
        r"([\u4e00-\u9fff\w]{2,15}?)生产([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,15}?)制造([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
    ],
    "收购": [
        r"([\u4e00-\u9fff\w]{2,15}?)收购了([\u4e00-\u9fff\w]{2,15}?)(?=[，。；\n,;]|$)",
    ],
}

TEMPLATE_PATTERNS = [
    {"pattern": "{entity1}是{entity2}的创始人", "relation": "创建"},
    {"pattern": "{entity1}总部位于{entity2}", "relation": "位于"},
    {"pattern": "{entity1}研发了{entity2}", "relation": "研发"},
    {"pattern": "{entity1}开发了{entity2}", "relation": "研发"},
    {"pattern": "{entity1}推出了{entity2}", "relation": "研发"},
    {"pattern": "{entity1}与{entity2}合作", "relation": "合作"},
    {"pattern": "{entity1}成立于{entity2}", "relation": "成立"},
    {"pattern": "{entity1}属于{entity2}", "relation": "属于"},
    {"pattern": "{entity1}投资了{entity2}", "relation": "投资"},
    {"pattern": "{entity1}收购了{entity2}", "relation": "收购"},
    {"pattern": "{entity1}生产{entity2}", "relation": "生产"},
    {"pattern": "{entity1}担任{entity2}", "relation": "任职"},
    {"pattern": "{entity1}创立了{entity2}", "relation": "创建"},
    {"pattern": "{entity1}创办了{entity2}", "relation": "创建"},
    {"pattern": "{entity1}创建了{entity2}", "relation": "创建"},
    {"pattern": "{entity1}由{entity2}创立", "relation": "创建", "reverse": True},
    {"pattern": "{entity1}由{entity2}创办", "relation": "创建", "reverse": True},
    {"pattern": "{entity1}由{entity2}创建", "relation": "创建", "reverse": True},
    {"pattern": "{entity1}发明了{entity2}", "relation": "发明"},
    {"pattern": "{entity1}发现了{entity2}", "relation": "发现"},
    {"pattern": "{entity1}著有《{entity2}》", "relation": "著有"},
    {"pattern": "{entity1}是{entity2}的首都", "relation": "位于"},
    {"pattern": "{entity1}是{entity2}的省会", "relation": "位于"},
    {"pattern": "{entity1}是{entity2}的代表人物", "relation": "关联"},
    {"pattern": "{entity1}是{entity2}的代表作", "relation": "代表作"},
]

EXTRACTION_PRIORITY = [
    "llm_few_shot",
    "llm_zero_shot",
    "spacy_dep",
    "spacy_template",
    "spacy_rule",
    "template",
    "rule",
]

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
