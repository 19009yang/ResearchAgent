# ResearchAgent

基于 LangGraph 的 ReAct Agent，用于科研文献检索、阅读与论文生成。

## 工作流

Agent 通过与用户对话，逐步完成以下流程：

1. 确定研究主题
2. 检索相关论文（OpenAlex + Semantic Scholar）
3. 下载论文 PDF
4. 阅读解析论文内容
5. 提取研究思路并提出新方向
6. 撰写论文并渲染为 PDF

## 项目结构

```
.
├── main.py                    # 入口
├── agent/
│   └── ReAct_Agent.py         # LangGraph ReAct Agent（状态机 + 工具调用）
├── tools/
│   ├── search_arxiv_v2.py     # paper_search 工具（调用 search pipeline）
│   ├── download_arxiv_pdf.py  # arXiv PDF 下载工具
│   ├── pdf_parser.py          # PDF 读取/解析/chunking/section 检测
│   └── Latex.py               # LaTeX → PDF 编译工具
├── pipeline/
│   └── search_pipeline.py     # 多源搜索编排（OpenAlex → Semantic Scholar → arXiv）
├── services/
│   ├── openalex_search.py     # OpenAlex API 客户端
│   ├── semantic_scholar_enrich.py  # Semantic Scholar 富化
│   ├── arxiv.py               # arXiv PDF URL 构建与下载
│   └── paper_chunker.py       # 学术论文语义分块（含 embedding）
├── models/
│   └── paper.py               # Paper 数据模型
└── logs/                      # 日志输出
```

## 工具

Agent 注册了 4 个工具：

| 工具 | 功能 |
|------|------|
| `paper_search` | 多源论文检索，返回论文元数据 |
| `read_pdf` | 下载/读取 PDF，提取文本、分块、检测 sections |
| `download_arxiv_pdf_tool` | 下载 arXiv PDF 到本地 |
| `render_latex_pdf` | 编译 LaTeX 并生成 PDF（latexmk） |

## 快速开始

### 环境要求

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip
- LaTeX 发行版（如需 PDF 渲染：`latexmk` + `pdflatex`）

### 安装

```bash
git clone https://github.com/19009yang/ResearchAgent.git
cd ResearchAgent
uv sync
```

### 配置

创建 `.env` 文件：

```env
LLM_PROVIDER=deepseek          # deepseek | openai | ollama | anthropic
LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
SEMANTIC_SCHOLAR_API_KEY=your_key   # 可选，用于论文检索富化
```

### 运行

```bash
uv run main.py
```

启动后 Agent 会以中文与你对话，引导你完成从选题到生成论文的全流程。

## 技术栈

- **LangGraph** — 状态机驱动的 Agent 工作流（ReAct 循环）
- **LangChain** — 工具定义与 LLM 抽象
- **OpenAlex / Semantic Scholar / arXiv** — 多源论文检索
- **PyMuPDF** — PDF 文本提取
- **sentence-transformers** — 语义分块（BGE embedding）
- **latexmk** — LaTeX 编译

## 约束

- 工具串行调用（禁止并行）
- PDF 限制：50MB / 50 页 / 100K 字符
- LaTeX 编译：60s 超时，禁用 shell-escape
- 日志仅输出到 `logs/sci_research_agent.log`

## License

MIT