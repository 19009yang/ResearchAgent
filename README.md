# ResearchAgent

一个基于 LangGraph + LLM 的科研文献智能研究 Agent。

该项目旨在构建一个能够：

- 自动检索论文
- 阅读与解析论文
- 提取关键信息
- 生成研究综述
- 多步推理与工具调用
- 自动迭代研究流程

的 Agent 系统。

项目目前重点关注：

- arXiv / OpenAlex / Semantic Scholar 文献检索
- PDF 下载与解析
- 多 Agent Workflow
- ReAct Agent
- LangGraph 状态机
- DeepSeek / OpenAI LLM 接入
- 科研自动化流程

---

# Features

## 文献检索

支持：

- arXiv API
- OpenAlex API
- Semantic Scholar API

支持：

- 关键词检索
- 多源融合
- Retry 重试机制
- API Rate Limit 处理

---

## Agent Workflow

基于 LangGraph 构建：

- 状态机 Workflow
- Tool Calling
- 多轮推理
- 流式输出
- ReAct Agent

---

## PDF 处理

支持：

- PDF 下载
- PDF 文本提取
- 文献内容解析
- Metadata 提取

---

## LLM 支持

目前支持：

- DeepSeek
- OpenAI

后续计划：

- Claude
- Gemini
- 本地模型

---

# Installation

## Clone Repository

```bash
git clone https://github.com/19009yang/ResearchAgent.git

cd ResearchAgent
```

---

## Create Virtual Environment

推荐使用 uv：

```bash
uv venv
```

激活环境：

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

---

## Install Dependencies

```bash
uv sync
```

---

# Environment Variables

创建：

```text
.env
```

示例：

```env
OPENAI_API_KEY=your_key
DEEPSEEK_API_KEY=your_key
SEMANTIC_SCHOLAR_API_KEY=your_key
```

---

# Usage

运行 Agent：

```bash
python main.py
```

或者：

```bash
uv run main.py
```

---

# Example Workflow

```text
User Query
    ↓
LLM Planning
    ↓
Paper Search
    ↓
PDF Download
    ↓
PDF Parsing
    ↓
Information Extraction
    ↓
LLM Reasoning
    ↓
Research Summary
```

---

# Current Progress

- [x] arXiv Search
- [x] OpenAlex Search
- [x] Semantic Scholar Search
- [x] PDF Parsing
- [x] LangGraph Workflow
- [x] ReAct Agent
- [x] Streaming Output
- [ ] Multi-Agent Collaboration
- [ ] RAG Knowledge Base
- [ ] Vector Database
- [ ] Research Report Generation
- [ ] Web UI

---

# Roadmap

未来计划：

- Deep Research Agent
- 自动文献综述生成
- 多论文交叉分析
- Citation Graph
- Knowledge Graph
- Local RAG
- Agent Memory
- Autonomous Research Pipeline

---

# Tech Stack

- Python
- LangGraph
- LangChain
- DeepSeek
- OpenAI
- arXiv API
- OpenAlex API
- Semantic Scholar API
- PyMuPDF
- pypdf

---

# Inspiration

本项目参考了：  

- [zazencodes-season-2](https://github.com/zazencodes/zazencodes-season-2/blob/main/src/ai-scientific-research-agent/sci_research_agent/arxiv.py)

---

# License

MIT License

---

# Author

GitHub: [19009yang](https://github.com/19009yang?utm_source=chatgpt.com)