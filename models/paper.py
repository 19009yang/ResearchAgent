from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Paper:

    # 基础信息
    title: str = ""
    abstract: str = ""
    year: Optional[int] = None

    # 标识符
    doi: str = ""
    arxiv_id: str = ""

    # 作者
    authors: List[str] = field(default_factory=list)

    # 统计信息
    citation_count: int = 0

    # 期刊/会议
    venue: str = ""

    # 链接
    paper_url: str = ""
    pdf_url: str = ""

    # 数据来源
    source: List[str] = field(default_factory=list)