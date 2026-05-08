from langchain_core.tools import tool

from pipeline.search_pipeline import (
    search_papers,
)
import logging
logger = logging.getLogger(__name__)
@tool
def paper_search(
    topic: str,
) -> dict:
    """
    学术论文搜索工具
    """

    try:
        logger.info(f"Searching papers: {topic}")
        papers = search_papers(
            query=topic,
            limit=5,
        )

        entries = []

        for paper in papers:

            entries.append({

                "title":
                    paper.title,

                "summary":
                    paper.abstract,

                "authors":
                    paper.authors,

                "year":
                    paper.year,

                "venue":
                    paper.venue,

                "citation_count":
                    paper.citation_count,

                "doi":
                    paper.doi,

                "arxiv_id":
                    paper.arxiv_id,

                "paper_url":
                    paper.paper_url,

                "pdf_url":
                    paper.pdf_url,

                "source":
                    paper.source,
            })

        return {

            "success": True,

            "entries": entries,
        }

    except Exception as e:

        return {

            "success": False,

            "error": str(e),
        }