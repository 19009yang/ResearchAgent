import time
import requests

from models.paper import Paper


BASE_URL = (
    "https://api.semanticscholar.org/"
    "graph/v1/paper/search"
)

HEADERS = {
    "User-Agent": "ResearchAgent/1.0"
}

session = requests.Session()


def enrich_with_semantic_scholar(
    paper: Paper,
) -> Paper:

    if not paper.title:
        return paper

    params = {
        "query": paper.title,

        "limit": 1,

        "fields": (
            "citationCount,"
            "externalIds,"
            "url"
        )
    }

    # -----------------------------------
    # retry
    # -----------------------------------
    for attempt in range(3):
        
        
        try:

            response = session.get(
                BASE_URL,
                params=params,
                headers=HEADERS,
                timeout=(10, 30),
            )

            # success
            if response.status_code == 200:
                break

            # rate limit
            elif response.status_code == 429:

                wait = 2 ** attempt

                print(
                    f"Semantic Scholar "
                    f"rate limited. "
                    f"Retry in {wait}s"
                )

                time.sleep(wait)

            else:

                response.raise_for_status()

        except Exception:

            if attempt == 2:
                return paper

            time.sleep(2 ** attempt)

    else:

        return paper

    data = response.json()

    results = data.get("data", [])

    if not results:
        return paper

    item = results[0]

    # -----------------------------------
    # enrich citation
    # -----------------------------------
    paper.citation_count = max(
        paper.citation_count,
        item.get(
            "citationCount",
            0
        )
    )

    # -----------------------------------
    # enrich URL
    # -----------------------------------
    paper.paper_url = item.get(
        "url",
        paper.paper_url,
    )

    # -----------------------------------
    # enrich arxiv_id
    # -----------------------------------
    external_ids = item.get(
        "externalIds",
        {}
    )

    if not paper.arxiv_id:

        paper.arxiv_id = (
            external_ids.get(
                "ArXiv",
                ""
            )
        )

    paper.source.append(
        "SemanticScholar"
    )

    return paper