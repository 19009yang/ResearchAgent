import requests
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def build_arxiv_pdf_url(
    arxiv_id: str,
) -> str:

    return (
        f"https://arxiv.org/pdf/"
        f"{arxiv_id}.pdf"
    )


def download_arxiv_pdf(
    arxiv_id: str,
    save_dir: str = "output/papers",
) -> str:

    pdf_url = build_arxiv_pdf_url(
        arxiv_id
    )

    Path(save_dir).mkdir(
        parents=True,
        exist_ok=True,
    )

    save_path = (
        Path(save_dir)
        / f"{arxiv_id}.pdf"
    )

    resp = requests.get(
        pdf_url,
        timeout=(10, 60),
        stream=True,
    )

    resp.raise_for_status()

    with open(save_path, "wb") as f:

        for chunk in resp.iter_content(
            chunk_size=8192
        ):
            if chunk:
                f.write(chunk)

    return str(save_path)