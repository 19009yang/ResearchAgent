from langchain_core.tools import tool
from services.arxiv import download_arxiv_pdf
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

@tool
def download_arxiv_pdf_tool(
    arxiv_id: str,
    save_dir: str = "output/papers",
) -> dict:
    """
    下载 arXiv PDF 论文到本地

    参数:
        arxiv_id: arXiv ID，例如 "2301.07041"
        save_dir: 保存目录，默认为 output/papers

    返回:
        {
            "success": True,
            "saved_path": "...",
            "arxiv_id": "..."
        }
    """

    try:
        saved_path = download_arxiv_pdf(arxiv_id, save_dir)
        logger.info(f"Downloaded arXiv PDF: {arxiv_id} -> {saved_path}")
        return {
            "success": True,
            "saved_path": saved_path,
            "arxiv_id": arxiv_id,
        }
    except Exception as e:
        logger.exception(f"Failed to download arXiv PDF: {arxiv_id}")
        return {
            "success": False,
            "error": str(e),
        }