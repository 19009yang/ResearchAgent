from typing import List

from models.paper import Paper

from services.openalex_search import (
    search_openalex,
)

from services.semantic_scholar_enrich import (
    enrich_with_semantic_scholar,
)

from services.arxiv import (
    build_arxiv_pdf_url,
)


def search_papers(
    query: str,
    limit: int = 5,
) -> List[Paper]:

    # -----------------------------------
    # 1. OpenAlex 主搜索
    # -----------------------------------
    papers = search_openalex(
        query=query,
        limit=limit,
    )

    enriched_papers = []

    # -----------------------------------
    # 2. Semantic Scholar enrich
    # -----------------------------------
    for paper in papers:

        try:

            paper = (
                enrich_with_semantic_scholar(
                    paper
                )
            )

        except Exception as e:

            print(
                "Semantic Scholar enrich failed:"
            )

            print(e)

        # -----------------------------------
        # 3. arXiv PDF URL
        # -----------------------------------
        if paper.arxiv_id:

            paper.pdf_url = (
                build_arxiv_pdf_url(
                    paper.arxiv_id
                )
            )

        enriched_papers.append(
            paper
        )

    return enriched_papers