import requests

from typing import List

from models.paper import Paper


BASE_URL = (
    "https://api.openalex.org/works"
)

HEADERS = {
    "User-Agent": "ResearchAgent/1.0"
}

session = requests.Session()


def search_openalex(
    query: str,
    limit: int = 10,
) -> List[Paper]:

    params = {
        "search": query,
        "per-page": limit,
    }

    response = session.get(
        BASE_URL,
        params=params,
        headers=HEADERS,
        timeout=(10, 30),
    )

    response.raise_for_status()

    data = response.json()

    papers = []

    for item in data.get(
        "results",
        []
    ):

        # -----------------------------------
        # authors
        # -----------------------------------
        authors = []

        for authorship in item.get(
            "authorships",
            []
        ):

            author = authorship.get(
                "author",
                {}
            )

            name = author.get(
                "display_name",
                ""
            )

            if name:
                authors.append(name)

        # -----------------------------------
        # venue
        # -----------------------------------
        venue = ""

        primary_location = item.get(
            "primary_location"
        )

        if primary_location:

            source = primary_location.get(
                "source"
            )

            if source:

                venue = source.get(
                    "display_name",
                    ""
                )

        # -----------------------------------
        # DOI
        # -----------------------------------
        doi = item.get("doi", "")

        if doi.startswith(
            "https://doi.org/"
        ):

            doi = doi.replace(
                "https://doi.org/",
                ""
            )

        # -----------------------------------
        # abstract
        # -----------------------------------
        abstract = ""

        inverted_index = item.get(
            "abstract_inverted_index"
        )

        if inverted_index:

            word_positions = {}

            for word, positions in (
                inverted_index.items()
            ):

                for pos in positions:
                    word_positions[pos] = word

            abstract = " ".join(
                word_positions[pos]
                for pos in sorted(
                    word_positions.keys()
                )
            )

        # -----------------------------------
        # paper
        # -----------------------------------
        paper = Paper(

            title=item.get(
                "title",
                ""
            ),

            abstract=abstract,

            year=item.get(
                "publication_year"
            ),

            authors=authors,

            citation_count=item.get(
                "cited_by_count",
                0
            ),

            venue=venue,

            doi=doi,

            paper_url=item.get(
                "id",
                ""
            ),

            source=["OpenAlex"],
        )

        papers.append(paper)

    return papers