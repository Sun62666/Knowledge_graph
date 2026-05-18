# 🏢 企业知识图谱平台

基于 **Python + LLM + Neo4j + CSV** 的企业知识图谱平台，整合全品类关系抽取技术，实现从文档解析、多技术关系抽取、CSV中间层存储、Neo4j图数据库构建到交互式可视化检索的全流程自动化。

---

## 📋 目录

- [功能特性](#功能特性)
- [技术架构](#技术架构)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [项目结构](#项目结构)
- [功能模块详解](#功能模块详解)
- [关系抽取技术](#关系抽取技术)
- [使用流程](#使用流程)
- [常见问题](#常见问题)

---

## ✨ 功能特性

- 📄 **多格式文档解析**：支持 PDF、DOCX、TXT 三种格式上传与解析，自动识别文件类型
- 🧠 **9种关系抽取技术融合**：规则、模板、传统ML、深度学习、预训练模型、LLM零/少样本、远程监督、知识蒸馏、联合抽取
- 💾 **CSV中间层管理**：三元组数据可预览、编辑、新增、删除、导出，数据可追溯
- 🔗 **Neo4j图谱构建**：一键导入图数据库，支持 MERGE 幂等性操作，中文关系兼容
- 🔍 **知识检索**：关键词模糊检索实体关系，检索结果缓存加速
- 🌐 **交互式可视化**：基于 Pyvis 的图谱展示，支持拖拽、缩放、高亮、关系筛选
- ⚙️ **灵活配置**：所有参数通过环境变量或配置文件管理，API密钥安全存储
- 📝 **完善日志**：统一日志格式，避免 Streamlit 热重载日志重复

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit Web 界面                   │
│  首页 │ 文档抽取 │ CSV管理 │ Neo4j导入 │ 检索 │ 可视化 │
└──────────┬──────────┬──────────┬──────────┬──────────┘
           │          │          │          │
     ┌─────▼─────┐ ┌──▼───┐ ┌───▼────┐ ┌──▼──────┐
     │ 文档解析   │ │NLP抽取│ │CSV管理 │ │Neo4j操作│
     │PDF/DOCX/TXT│ │9种技术│ │三元组  │ │CQL/查询 │
     └───────────┘ └──┬───┘ └───┬────┘ └───┬─────┘
                      │         │          │
                 ┌────▼────┐ ┌──▼──┐ ┌─────▼─────┐
                 │  LLM    │ │ CSV │ │   Neo4j   │
                 │Qwen/GPT │ │中间层│ │  图数据库  │
                 └─────────┘ └─────┘ └───────────┘
```

---

## 💻 环境要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.9 - 3.11 |
| Neo4j | 5.0+（本地部署，Bolt协议） |
| 操作系统 | Windows / macOS |

---

## 🚀 快速开始

### 1. 克隆项目

```bash
cd your_workspace
git clone <repository_url> Knowledge_graph
cd Knowledge_graph
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

> **核心依赖**（必须安装）：streamlit、pandas、PyPDF2、python-docx、neo4j、networkx、pyvis、openai
>
> **可选依赖**（高级抽取功能）：scikit-learn、torch、transformers、langchain

### 3. 配置参数

编辑 `utils/config.py` 或设置环境变量：

```bash
# Neo4j 连接配置
set NEO4J_URI=bolt://localhost:7687
set NEO4J_USER=neo4j
set NEO4J_PASSWORD=your_password

# LLM API 配置（通义千问）
set LLM_API_KEY=sk-xxxxxxxx
set LLM_MODEL_NAME=qwen-turbo
set LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 4. 启动 Neo4j

确保 Neo4j 服务已启动并运行在 `bolt://localhost:7687`：

```bash
# Windows: 启动 Neo4j Desktop 或命令行
neo4j console
```

### 5. 启动平台

```bash
streamlit run main.py
```

浏览器自动打开 `http://localhost:8501`，即可使用平台。

---

## ⚙️ 配置说明

所有配置项均支持 **环境变量覆盖**，优先级：环境变量 > config.py 默认值。

### Neo4j 配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| URI | `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt协议地址 |
| 用户名 | `NEO4J_USER` | `neo4j` | 数据库用户名 |
| 密码 | `NEO4J_PASSWORD` | `your_password` | 数据库密码 |

### LLM 配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| API密钥 | `LLM_API_KEY` | `your_api_key` | 通义千问/OpenAI API Key |
| 模型名 | `LLM_MODEL_NAME` | `qwen-turbo` | 模型名称 |
| Base URL | `LLM_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | API地址 |
| 温度 | `LLM_TEMPERATURE` | `0.1` | 生成温度（越低越确定） |
| 最大Token | `LLM_MAX_TOKENS` | `2048` | 单次最大输出长度 |

### 文本处理配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 最大文本长度 | `MAX_TEXT_LENGTH` | `5000` | 单次处理最大字符数 |
| 分片大小 | `CHUNK_SIZE` | `2000` | 文本分片字符数 |
| 分片重叠 | `CHUNK_OVERLAP` | `200` | 分片间重叠字符数 |

---

## 📁 项目结构

```
Knowledge_graph/
├── main.py                          # Streamlit 主入口
├── requirements.txt                 # 依赖清单
├── data/                            # 数据目录（自动创建）
│   ├── triplets.csv                 # 三元组CSV中间层
│   ├── import_cypher.cql            # 生成的CQL导入脚本
│   ├── app.log                      # 运行日志
│   └── cache/                       # 可视化缓存
├── utils/                           # 工具模块
│   ├── config.py                    # 集中配置管理
│   ├── logger.py                    # 统一日志工具
│   └── visualizer.py                # 图谱可视化与检索
├── modules/                         # 核心功能模块
│   ├── file_parser/
│   │   └── parser.py                # 文档解析（PDF/DOCX/TXT）
│   ├── nlp_processor/
│   │   └── extractor.py             # 多技术融合关系抽取
│   ├── csv_manager/
│   │   └── manager.py               # CSV中间层管理
│   └── neo4j_ops/
│       └── operations.py            # Neo4j数据库操作
└── main/                            # Web界面模块
    └── pages/
        ├── home.py                  # 首页
        ├── doc_extract.py           # 文档抽取页
        ├── csv_manage.py            # CSV管理页
        ├── neo4j_import.py          # Neo4j导入页
        ├── knowledge_search.py      # 知识检索页
        ├── graph_visual.py          # 图谱可视化页
        └── system_admin.py          # 系统管理页
```

---

## 📖 功能模块详解

### 模块1：文档解析

支持三种文档格式，统一解析接口：

| 格式 | 库 | 特点 |
|------|-----|------|
| TXT | 内置 open | 多编码自动识别（UTF-8/GBK/GB2312/GB18030） |
| PDF | PyPDF2 | 逐页提取文本，兼容加密文档 |
| DOCX | python-docx | 按段落提取，保留文本结构 |

### 模块2：多技术融合关系抽取

9种抽取技术分层融合，按优先级合并结果：

```
优先级：LLM零样本 > LLM少样本 > 预训练模型 > 深度学习 > 传统ML > 模板 > 规则 > 远程监督 > 知识蒸馏 > 联合抽取
```

输出统一为三元组格式：`[实体1, 关系, 实体2]`

### 模块3：CSV中间层

- **写入模式**：覆盖写入 / 增量追加（自动去重）
- **数据操作**：修改、新增、删除、清空、导出
- **CQL生成**：自动将三元组转换为 Neo4j CQL 脚本，中文关系用反引号包裹
- **编码格式**：UTF-8-SIG（兼容 Excel 直接打开）

### 模块4：Neo4j图数据库

- **连接管理**：单例模式，初始化验证连通性
- **数据导入**：支持三元组直接导入和CQL脚本导入
- **幂等操作**：使用 `MERGE` 替代 `CREATE`，避免重复创建
- **查询检索**：全量查询、关键词模糊检索（CONTAINS）
- **数据清空**：一键清空所有节点和关系

### 模块5：知识检索与可视化

- **检索缓存**：基于关键词哈希的 JSON 缓存，避免重复查询
- **图谱缓存**：基于数据哈希的 HTML 缓存，数据不变时复用渲染
- **交互式图谱**：拖拽、缩放、高亮、物理引擎模拟

---

## 🧠 关系抽取技术

### 已实现（开箱即用）

| 技术 | 说明 | 适用场景 |
|------|------|----------|
| 规则抽取 | 基于正则模式匹配 | 简单明确的实体关系（位于、研发、成立等） |
| 模板抽取 | 基于高频句式模板 | 固定句式（"A是B的创始人"、"A总部位于B"） |
| LLM零样本 | 通过Prompt指令直接抽取 | 复杂文本、通用领域 |
| LLM少样本 | 提供标注示例后抽取 | 企业特定领域、提升精度 |
| 远程监督 | 基于外部知识库弱标注 | 标注数据稀缺场景 |

### 框架已搭建（需训练数据/模型）

| 技术 | 说明 | 所需依赖 |
|------|------|----------|
| 传统ML | SVM + TF-IDF特征工程 | scikit-learn |
| 深度学习 | CNN/RNN/BiLSTM/BiLSTM-CRF | PyTorch |
| 预训练模型 | BERT/RoBERTa微调 | transformers + PyTorch |
| 知识蒸馏 | 大模型指导小模型 | PyTorch |
| 联合抽取 | 实体识别与关系抽取联合 | PyTorch + transformers |

### 支持的关系类型

任职、位于、研发、合作、成立、属于、投资、收购、生产、担任、创建、包含、关联、竞争

### 支持的实体类型

人名、地名、组织名、时间、产品名、职位、事件

---

## 🔄 使用流程

### 典型工作流

```
1. 上传文档 ──→ 2. 文档解析 ──→ 3. 关系抽取 ──→ 4. 查看三元组
                                                    │
5. 图谱可视化 ←── 6. 导入Neo4j ←── 5. 编辑CSV ←──┘
                                                    │
                              7. 知识检索 ←─────────┘
```

### 详细步骤

1. **首页**：查看系统连接状态（Neo4j / CSV / LLM）
2. **文档抽取**：
   - 上传 PDF/DOCX/TXT 文件
   - 选择抽取技术（推荐：规则 + 模板 + LLM零样本）
   - 点击"开始抽取"，查看三元组预览
3. **CSV管理**：
   - 查看分页数据表格
   - 修改/新增/删除三元组，修正AI抽取误差
   - 生成CQL导入脚本
4. **导入Neo4j**：
   - 预览CQL脚本
   - 执行导入，查看导入结果
5. **知识检索**：
   - 输入关键词（如"华为"、"5G"）
   - 查看检索结果和检索图谱
6. **图谱可视化**：
   - 加载全量图谱
   - 拖拽、缩放、高亮交互

---

## ❓ 常见问题

### Q: 启动后 Neo4j 连接失败？

确保 Neo4j 服务已启动，检查 `utils/config.py` 中的连接信息：
- URI：`bolt://localhost:7687`
- 用户名/密码与 Neo4j 设置一致
- 如未安装 Neo4j，平台其他功能（文档解析、CSV管理）仍可正常使用

### Q: LLM 抽取不可用？

需要配置有效的 API 密钥：
- 通义千问：在 [阿里云控制台](https://dashscope.console.aliyun.com/) 获取 API Key
- OpenAI：修改 `LLM_BASE_URL` 为 `https://api.openai.com/v1`
- 不配置 API Key 时，规则和模板抽取仍可正常工作

### Q: 如何添加自定义关系类型？

编辑 `utils/config.py`：
1. 在 `RULE_PATTERNS` 中添加新的正则模式
2. 在 `TEMPLATE_PATTERNS` 中添加新的句式模板
3. 在 `RELATION_TYPES` 列表中添加关系名称

### Q: CSV 文件用 Excel 打开乱码？

CSV 文件使用 `utf-8-sig` 编码，Excel 可直接打开。如仍有问题，可使用"导出CSV"功能下载后用记事本打开另存为 ANSI 编码。

### Q: 如何清空所有数据重新开始？

在"系统管理"页面点击"全部重置"，或手动操作：
- 删除 `data/triplets.csv`
- 在 Neo4j Browser 中执行 `MATCH (n) DETACH DELETE n`
- 删除 `data/cache/` 目录下的缓存文件

---

## 📄 许可证

本项目仅供学习和研究使用。
