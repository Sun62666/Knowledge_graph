import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

LLM_API_KEY = os.getenv("LLM_API_KEY", "your_api_key")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "qwen-turbo")
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

ENTITY_TYPES = ["人名", "地名", "组织名", "时间", "产品名", "职位", "事件"]
RELATION_TYPES = [
    "任职", "位于", "研发", "合作", "成立", "属于", "投资",
    "收购", "生产", "担任", "创建", "包含", "关联", "竞争"
]

RULE_PATTERNS = {
    "任职": [
        r"([\u4e00-\u9fff\w]+)担任([\u4e00-\u9fff\w]+)的([\u4e00-\u9fff\w]+)",
        r"([\u4e00-\u9fff\w]+)出任([\u4e00-\u9fff\w]+)的([\u4e00-\u9fff\w]+)",
    ],
    "位于": [
        r"([\u4e00-\u9fff\w]{2,}?)总部位于([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{3,}?)(?:总部)?位于([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,}?)总部在([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]{2,}?)坐落于([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
    ],
    "研发": [
        r"([\u4e00-\u9fff\w]+?)研发了([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]+?)开发了([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]+?)推出([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
    ],
    "合作": [
        r"([\u4e00-\u9fff\w]+?)与([\u4e00-\u9fff\w]+?)合作",
        r"([\u4e00-\u9fff\w]+?)和([\u4e00-\u9fff\w]+?)联合",
    ],
    "成立": [
        r"([\u4e00-\u9fff\w]+?)成立于([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]+?)创立于([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]+?)创办于([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
    ],
    "属于": [
        r"([\u4e00-\u9fff\w]+?)属于([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]+?)隶属于([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
    ],
    "投资": [
        r"([\u4e00-\u9fff\w]+?)投资了([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]+?)向([\u4e00-\u9fff\w]+?)投资",
    ],
    "创建": [
        r"([\u4e00-\u9fff\w]+?)创立了([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]+?)创办了([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
        r"([\u4e00-\u9fff\w]+?)创建了([\u4e00-\u9fff\w]+?)(?=[，。；\n,;]|$)",
    ],
}

TEMPLATE_PATTERNS = [
    {"pattern": "{entity1}是{entity2}的创始人", "relation": "创建"},
    {"pattern": "{entity1}总部位于{entity2}", "relation": "位于"},
    {"pattern": "{entity1}研发了{entity2}", "relation": "研发"},
    {"pattern": "{entity1}与{entity2}合作", "relation": "合作"},
    {"pattern": "{entity1}成立于{entity2}", "relation": "成立"},
    {"pattern": "{entity1}属于{entity2}", "relation": "属于"},
    {"pattern": "{entity1}投资了{entity2}", "relation": "投资"},
    {"pattern": "{entity1}收购了{entity2}", "relation": "收购"},
    {"pattern": "{entity1}生产{entity2}", "relation": "生产"},
    {"pattern": "{entity1}担任{entity2}", "relation": "任职"},
    {"pattern": "{entity1}创立了{entity2}", "relation": "创建"},
    {"pattern": "{entity1}创办了{entity2}", "relation": "创建"},
    {"pattern": "{entity1}开发了{entity2}", "relation": "研发"},
    {"pattern": "{entity1}由{entity2}创立", "relation": "创建"},
]

EXTRACTION_PRIORITY = [
    "llm_zero_shot",
    "llm_few_shot",
    "pretrained_model",
    "deep_learning",
    "traditional_ml",
    "template",
    "rule",
    "remote_supervision",
    "knowledge_distillation",
    "joint_extraction",
]

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
