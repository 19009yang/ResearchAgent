# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (uses uv)
uv sync

# Run the agent
uv run main.py
# or
python main.py
```

## Environment Setup

Create a `.env` file with:
```
LLM_PROVIDER=deepseek|openai|ollama|anthropic
LLM_MODEL=<model_name>
OPENAI_API_KEY=<key>        # for openai provider
DEEPSEEK_API_KEY=<key>      # for deepseek provider
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
SEMANTIC_SCHOLAR_API_KEY=<key>  # optional, for enrichment
```

## Architecture

This is a LangGraph-based ReAct agent for scientific literature research.

### Core Workflow (agent/ReAct_Agent.py)

- StateGraph with agent → tools → agent loop
- `parallel_tool_calls=False` enforced to prevent concurrent arxiv_search calls
- MemorySaver checkpointer for conversation state persistence
- Interactive chat loop after initial system prompt

### Tool Chain (tools/)

Three LangChain tools registered with the agent:
1. `paper_search` - searches papers via OpenAlex + Semantic Scholar enrichment
2. `read_pdf` - downloads and extracts text from PDF URLs (chunking + section detection)
3. `render_latex_pdf` - compiles LaTeX to PDF using latexmk (no shell-escape for security)

### Search Pipeline (pipeline/search_pipeline.py)

Multi-source orchestration:
1. OpenAlex primary search (gets title, abstract, authors, venue, citation count)
2. Semantic Scholar enrichment (adds arxiv_id, updates citations)
3. arXiv PDF URL construction when arxiv_id present

### Data Model (models/paper.py)

Single `Paper` dataclass with: title, abstract, year, doi, arxiv_id, authors, citation_count, venue, paper_url, pdf_url, source list.

### Services Layer (services/)

- `openalex_search.py` - OpenAlex API client with inverted index abstract reconstruction
- `semantic_scholar_enrich.py` - enrichment with retry/rate-limit handling
- `arxiv.py` - PDF URL builder and downloader

## Key Constraints

- Tools must be called sequentially (no parallel tool calls)
- PDF parsing limits: 50MB max, 50 pages max, 100K chars max
- LaTeX compilation: 60s timeout, no shell-escape, 50MB output limit
- System prompt requires responses in Chinese
- Logging outputs to `logs/sci_research_agent.log` only (no console)