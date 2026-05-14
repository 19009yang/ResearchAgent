# import requests
# import pymupdf

# def download_pdf(url, save_path):
#     r = requests.get(url, timeout=30)
#     r.raise_for_status()

#     with open(save_path, "wb") as f:
#         f.write(r.content)


# def extract_text(pdf_path):
#     text = ""

#     with pymupdf.open(pdf_path) as doc:
#         for page in doc:
#             text += page.get_text("text") # type: ignore

#     return text

import io
import logging
from typing import Dict, List
from urllib.parse import urlparse, urlunparse
from langchain_text_splitters import RecursiveCharacterTextSplitter
from services.paper_chunker import AcademicChunker

import pymupdf
import requests
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------
# 配置
# ---------------------------------------------------
MAX_PDF_SIZE_MB = 50
MAX_PAGES = 50

# 每个 chunk 最大字符数
CHUNK_SIZE = 1000

# chunk overlap
CHUNK_OVERLAP = 200

# requests timeout
REQUEST_TIMEOUT = (10, 60)

# 最大返回字符
MAX_TOTAL_CHARS = 100000


# ---------------------------------------------------
# Session 连接池
# ---------------------------------------------------
session = requests.Session()


# ---------------------------------------------------
# 文本 chunk
# ---------------------------------------------------
# def split_text(
#     text: str,
#     chunk_size: int = CHUNK_SIZE,
#     overlap: int = CHUNK_OVERLAP,
# ) -> List[str]:
#     """
#     文本切块

#     用于:
#     - RAG
#     - embedding
#     - 长上下文控制
#     """

#     if not text:
#         return []

#     chunks = []

#     start = 0

#     while start < len(text):

#         end = start + chunk_size

#         chunk = text[start:end]

#         chunks.append(chunk)

#         start += chunk_size - overlap

#     return chunks



def split_text(     
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,)-> List[str]:
    """
    智能递归切分
    """
    text_splitter = RecursiveCharacterTextSplitter(
        separators=[
            "\nAbstract",
            "\nIntroduction",
            "\nRelated Work",
            "\nMethod",
            "\nMethods",
            "\nExperiment",
            "\nExperiments",
            "\nResults",
            "\nDiscussion",
            "\nConclusion",
            "\nReferences",
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ],
    chunk_size=chunk_size,
    overlap=overlap
    )
    return text_splitter.split_text(text)



# ---------------------------------------------------
# 提取 section
# ---------------------------------------------------
def detect_sections(text: str) -> Dict[str, str]:
    """
    简单论文 section 提取

    可后续升级:
    - GROBID
    - Science Parse
    """

    sections = {}

    keywords = [
        "abstract",
        "introduction",
        "method",
        "methods",
        "experiment",
        "results",
        "discussion",
        "conclusion",
        "references",
    ]

    lower_text = text.lower()

    for keyword in keywords:

        idx = lower_text.find(keyword)

        if idx != -1:

            sections[keyword] = text[
                idx: idx + 3000
            ]

    return sections


@tool
def read_pdf(url: str) -> dict:
    """
    读取 PDF 并提取文本

    参数:
        url: PDF URL (http/https) 或本地文件路径

    返回:
        {
            "success": True,
            "title": "...",
            "num_pages": 12,
            "chunks": [...],
            "sections": {...},
            "metadata": {...}
        }

    功能:
    1. 下载 PDF（远程）或直接读取（本地）
    2. 安全检查
    3. 提取文本
    4. Chunking
    5. Section 检测
    6. Agent/RAG 友好
    """

    try:

        # ---------------------------------------------------
        # 1. 判断本地路径 or URL
        # ---------------------------------------------------
        parsed = urlparse(url)

        if parsed.scheme in ("http", "https"):

            # -------------------------------------------
            # 远程 URL：下载
            # -------------------------------------------
            safe_url = urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    "",
                    "",
                    "",
                )
            )

            logger.info(f"Downloading PDF: {safe_url}")

            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                stream=True,
            )
            response.raise_for_status()

            # Content-Type 检查
            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower():
                return {
                    "success": False,
                    "error": "URL is not a PDF",
                }

            # 文件大小检查
            content_length = response.headers.get("Content-Length")
            if content_length:
                size_mb = int(content_length) / 1024 / 1024
                if size_mb > MAX_PDF_SIZE_MB:
                    return {
                        "success": False,
                        "error": f"PDF too large ({size_mb:.1f} MB)",
                    }

            logger.info("PDF downloaded successfully")

            pdf_bytes = io.BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    pdf_bytes.write(chunk)
            pdf_bytes.seek(0)

            doc = pymupdf.open(
                stream=pdf_bytes.read(),
                filetype="pdf",
            )

        else:
            # -------------------------------------------
            # 本地文件：直接读取
            # -------------------------------------------
            import os

            if not os.path.isfile(url):
                return {
                    "success": False,
                    "error": f"File not found: {url}",
                }

            # 文件大小检查
            size_mb = os.path.getsize(url) / 1024 / 1024
            if size_mb > MAX_PDF_SIZE_MB:
                return {
                    "success": False,
                    "error": f"PDF too large ({size_mb:.1f} MB)",
                }

            logger.info(f"Reading local PDF: {url}")
            doc = pymupdf.open(url)

        num_pages = len(doc)

        logger.info(
            f"PDF pages: {num_pages}"
        )

        # ---------------------------------------------------
        # 7. 页数限制
        # ---------------------------------------------------
        if num_pages > MAX_PAGES:

            logger.warning(
                f"Large PDF: {num_pages} pages"
            )

        # ---------------------------------------------------
        # 8. metadata
        # ---------------------------------------------------
        metadata = doc.metadata or {}

        title = metadata.get("title", "")

        # ---------------------------------------------------
        # 9. 提取文本
        # ---------------------------------------------------
        page_texts = []

        total_chars = 0

        for page_num, page in enumerate(
            doc,
            start=1,
        ):

            # 避免超长
            if total_chars > MAX_TOTAL_CHARS:

                logger.warning(
                    "PDF text truncated "
                    "due to size limit"
                )

                break

            logger.debug(
                f"Extracting page "
                f"{page_num}/{num_pages}"
            )

            try:

                blocks = page.get_text(
                    "blocks"
                )

                page_text = "\n".join(
                    block[4].strip()
                    for block in blocks
                    if (
                        len(block) > 4
                        and block[4].strip()
                    )
                )

                if page_text:

                    page_texts.append(
                        {
                            "page": page_num,
                            "text": page_text,
                        }
                    )

                    total_chars += len(
                        page_text
                    )

            except Exception as e:

                logger.warning(
                    f"Failed extracting "
                    f"page {page_num}: {e}"
                )

        # ---------------------------------------------------
        # 10. 合并全文
        # ---------------------------------------------------
        full_text = "\n\n".join(
            p["text"]
            for p in page_texts
        )

        if not full_text.strip():

            return {
                "success": False,
                "error": (
                    "No text extracted. "
                    "Possibly scanned PDF."
                ),
            }

        logger.info(
            f"Extracted "
            f"{len(full_text)} chars"
        )

        # ---------------------------------------------------
        # 11. chunking
        # ---------------------------------------------------
        # text_chunks = split_text(
        #     full_text
        # )

        chunker = AcademicChunker()

        text_chunks = chunker.chunk(full_text)

        chunks = []

        for i, chunk in enumerate(
            text_chunks
        ):

            chunks.append(
                {
                    "chunk_id": i,
                    "text": chunk,
                }
            )

        # ---------------------------------------------------
        # 12. section 检测
        # ---------------------------------------------------
        sections = detect_sections(
            full_text
        )

        # ---------------------------------------------------
        # 13. 返回结构化结果
        # ---------------------------------------------------
        return {

            "success": True,

            "title": title,

            "num_pages": num_pages,

            "num_chunks": len(chunks),

            "chunks": chunks,

            "sections": sections,

            "metadata": metadata,
        }

    # ---------------------------------------------------
    # 14. 网络错误
    # ---------------------------------------------------
    except requests.RequestException as e:

        logger.exception(
            "PDF download failed"
        )

        return {
            "success": False,
            "error": str(e),
        }

    # ---------------------------------------------------
    # 15. PDF 解析错误
    # ---------------------------------------------------
    except Exception as e:

        logger.exception(
            "PDF parsing failed"
        )

        return {
            "success": False,
            "error": str(e),
        }