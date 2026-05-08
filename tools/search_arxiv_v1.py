import requests
from langchain_core.tools import tool
import logging
import xml.etree.ElementTree as ET
import time
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any, List

#从arxiv中获取论文信息
# def search_arxiv(query, max_results=5):
#     search = arxiv.Search(
#         query=query,
#         max_results=max_results,
#         sort_by=arxiv.SortCriterion.Relevance
#     )

#     results = []

#     #从arxiv下载查询结果
#     for paper in search.results():
#         results.append({
#             "title": paper.title,
#             "authors": [a.name for a in paper.authors],
#             "summary": paper.summary,
#             "pdf_url": paper.pdf_url
#         })

#     return results

#为当前模块创建一个独立的日志记录器
logger = logging.getLogger(__name__)

# arXiv API 基础 URL
BASE_URL = "http://export.arxiv.org/api/query"

# 请求头
# arXiv 官方建议设置明确的 User-Agent
# 否则容易被限流（429）
HEADERS = {
    "User-Agent": "ResearchAgent/1.0"
}


def sanitize_query(query: str) -> str:
    """
    清洗用户输入的查询字符串

    参数:
        query: 用户输入的论文主题

    返回:
        清洗后的 query

    作用:
    1. 去除危险字符
    2. 压缩多余空格
    3. 防止 URL 构造异常
    """

    # 去除危险字符
    # < > 可能影响 URL 或 XML
    query = re.sub(r"[<>]", "", query)

    # 将多个连续空格压缩成一个空格
    # 例如:
    # "deep     learning" -> "deep learning"
    query = re.sub(r"\s+", " ", query)

    # 去除首尾空格
    return query.strip()

# -----------------------------------
# 全局 Session（连接复用）
# -----------------------------------
session = requests.Session()

retry_strategy = Retry(
    total=3,

    # connect retry
    connect=3,

    # read retry
    read=3,

    # 状态码 retry
    status=3,

    # 指数退避
    backoff_factor=2,

    # 需要 retry 的 HTTP 状态码
    status_forcelist=[
        429,
        500,
        502,
        503,
        504,
    ],

    allowed_methods=["GET"],
)

adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,
    pool_maxsize=10,
)

session.mount("https://", adapter)
session.mount("http://", adapter)

# -----------------------------------
# 全局限速器
# -----------------------------------
_LAST_REQUEST_TIME = 0


def rate_limit(min_interval: float = 3.0):
    """
    arXiv API 限速

    官方建议:
    不超过 1 request / 3 seconds
    """

    global _LAST_REQUEST_TIME

    now = time.time()

    elapsed = now - _LAST_REQUEST_TIME

    if elapsed < min_interval:
        sleep_time = min_interval - elapsed

        logger.info(
            f"Rate limiting: sleep {sleep_time:.2f}s"
        )

        time.sleep(sleep_time)

    _LAST_REQUEST_TIME = time.time()


def search_arxiv_papers(
    topic: str,
    max_results: int = 10,
) -> dict:
    """
    搜索 arXiv 论文（增强版）

    功能:
    1. Query 清洗
    2. Session 连接复用
    3. 自动 retry
    4. 指数退避
    5. arXiv 限速
    6. ReadTimeout 处理
    7. XML 解析
    """

    # -----------------------------------
    # 1. query 清洗
    # -----------------------------------
    query = sanitize_query(topic)

    logger.info(f"Searching arXiv: {query}")

    # -----------------------------------
    # 2. 限制 max_results
    # -----------------------------------
    max_results = min(max_results, 20)

    # -----------------------------------
    # 3. 请求参数
    # -----------------------------------
    params = {
        "search_query": f"all:{query}",
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    # -----------------------------------
    # 4. arXiv API 限速
    # -----------------------------------
    rate_limit()

    # -----------------------------------
    # 5. retry 主循环
    # -----------------------------------
    max_attempts = 5

    for attempt in range(max_attempts):

        try:

            logger.info(
                f"arXiv request attempt "
                f"{attempt + 1}/{max_attempts}"
            )

            # -----------------------------------
            # 6. HTTP 请求
            # -----------------------------------
            resp = session.get(
                BASE_URL,
                params=params,
                headers=HEADERS,

                # connect timeout, read timeout
                timeout=(10, 90),

                allow_redirects=True,
            )

            # -----------------------------------
            # 7. HTTP 错误检查
            # -----------------------------------
            resp.raise_for_status()

            # -----------------------------------
            # 8. 内容检查
            # -----------------------------------
            if not resp.text.strip():

                raise ValueError(
                    "Empty response from arXiv API"
                )

            logger.info(
                "Successfully retrieved "
                "response from arXiv API"
            )

            # -----------------------------------
            # 9. XML 解析
            # -----------------------------------
            data = parse_arxiv_xml(resp.text)

            return {
                "success": True,
                "data": data,
            }

        # -----------------------------------
        # 10. Read timeout
        # -----------------------------------
        except requests.exceptions.ReadTimeout as e:

            wait = 2 ** attempt

            logger.warning(
                f"Read timeout from arXiv API. "
                f"Retry in {wait}s"
            )

            if attempt == max_attempts - 1:

                return {
                    "success": False,
                    "error": (
                        "arXiv API read timeout"
                    ),
                }

            time.sleep(wait)

        # -----------------------------------
        # 11. Connection timeout
        # -----------------------------------
        except requests.exceptions.ConnectTimeout as e:

            wait = 2 ** attempt

            logger.warning(
                f"Connect timeout. "
                f"Retry in {wait}s"
            )

            if attempt == max_attempts - 1:

                return {
                    "success": False,
                    "error": (
                        "arXiv API connect timeout"
                    ),
                }

            time.sleep(wait)

        # -----------------------------------
        # 12. HTTP 错误
        # -----------------------------------
        except requests.exceptions.HTTPError as e:

            status_code = e.response.status_code

            logger.warning(
                f"HTTP error from arXiv API: "
                f"{status_code}"
            )

            # arXiv 限流
            if status_code == 429:

                wait = 2 ** attempt

                logger.warning(
                    f"Rate limited by arXiv API. "
                    f"Retry in {wait}s"
                )

                time.sleep(wait)

                continue

            return {
                "success": False,
                "error": (
                    f"HTTP error: {status_code}"
                ),
            }

        # -----------------------------------
        # 13. XML 解析失败
        # -----------------------------------
        except Exception as e:

            logger.exception(
                "Arxiv search failed"
            )

            return {
                "success": False,
                "error": str(e),
            }

    # -----------------------------------
    # 14. retry 全部失败
    # -----------------------------------
    return {
        "success": False,
        "error": (
            "arXiv API retry exhausted"
        ),
    }



def parse_arxiv_xml(xml_string: str) -> Dict[str, Any]:
    """
    解析 arXiv API 返回的 XML 数据

    功能:
    1. 解析 Atom XML
    2. 提取 feed 元信息
    3. 提取论文 entry 信息
    4. 安全处理缺失字段
    5. 防止 XML 解析异常
    6. 返回结构化 dict
    """

    # ---------------------------------------------------
    # 1. XML Namespace
    # ---------------------------------------------------
    namespaces = {
        "atom": "http://www.w3.org/2005/Atom",
        "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    # ---------------------------------------------------
    # 2. 安全获取 text
    # ---------------------------------------------------
    def safe_text(element) -> str:
        """
        安全获取 XML 节点文本

        防止:
        - NoneType.text
        - 空字符串
        - 多余换行
        """

        if element is None:
            return ""

        if element.text is None:
            return ""

        return element.text.strip()

    # ---------------------------------------------------
    # 3. 安全获取属性
    # ---------------------------------------------------
    def safe_attrib(element, key: str) -> str:
        """
        安全获取 XML attribute
        """

        if element is None:
            return ""

        return element.attrib.get(key, "")

    # ---------------------------------------------------
    # 4. 解析 XML
    # ---------------------------------------------------
    try:

        root = ET.fromstring(xml_string)

    except ET.ParseError as e:

        raise ValueError(
            f"Invalid arXiv XML response: {str(e)}"
        )

    # ---------------------------------------------------
    # 5. Feed 元信息
    # ---------------------------------------------------
    feed = {
        "title": safe_text(
            root.find("atom:title", namespaces)
        ),

        "id": safe_text(
            root.find("atom:id", namespaces)
        ),

        "updated": safe_text(
            root.find("atom:updated", namespaces)
        ),

        "total_results": safe_text(
            root.find(
                "opensearch:totalResults",
                namespaces,
            )
        ),

        "start_index": safe_text(
            root.find(
                "opensearch:startIndex",
                namespaces,
            )
        ),

        "items_per_page": safe_text(
            root.find(
                "opensearch:itemsPerPage",
                namespaces,
            )
        ),

        "entries": [],
    }

    # ---------------------------------------------------
    # 6. 遍历论文 entries
    # ---------------------------------------------------
    entries = root.findall(
        "atom:entry",
        namespaces,
    )

    for entry in entries:

        # ---------------------------------------------------
        # 7. 作者列表
        # ---------------------------------------------------
        authors: List[str] = []

        for author in entry.findall(
            "atom:author",
            namespaces,
        ):

            name = safe_text(
                author.find(
                    "atom:name",
                    namespaces,
                )
            )

            if name:
                authors.append(name)

        # ---------------------------------------------------
        # 8. 分类列表
        # ---------------------------------------------------
        categories: List[str] = []

        for category in entry.findall(
            "atom:category",
            namespaces,
        ):

            term = safe_attrib(
                category,
                "term",
            )

            if term:
                categories.append(term)

        # ---------------------------------------------------
        # 9. 链接信息
        # ---------------------------------------------------
        links = {}

        for link in entry.findall(
            "atom:link",
            namespaces,
        ):

            href = safe_attrib(link, "href")

            if not href:
                continue

            # pdf / abstract / default
            title = (
                safe_attrib(link, "title")
                or safe_attrib(link, "rel")
                or "default"
            )

            links[title] = href

        # ---------------------------------------------------
        # 10. PDF 链接快捷字段
        # ---------------------------------------------------
        pdf_url = ""

        for value in links.values():

            if "pdf" in value:
                pdf_url = value
                break

        # ---------------------------------------------------
        # 11. 单篇论文数据
        # ---------------------------------------------------
        entry_data = {

            # 基础信息
            "id": safe_text(
                entry.find(
                    "atom:id",
                    namespaces,
                )
            ),

            "title": safe_text(
                entry.find(
                    "atom:title",
                    namespaces,
                )
            ),

            "summary": safe_text(
                entry.find(
                    "atom:summary",
                    namespaces,
                )
            ),

            # 时间
            "published": safe_text(
                entry.find(
                    "atom:published",
                    namespaces,
                )
            ),

            "updated": safe_text(
                entry.find(
                    "atom:updated",
                    namespaces,
                )
            ),

            # 作者
            "authors": authors,

            # arXiv 元信息
            "comment": safe_text(
                entry.find(
                    "arxiv:comment",
                    namespaces,
                )
            ),

            "journal_ref": safe_text(
                entry.find(
                    "arxiv:journal_ref",
                    namespaces,
                )
            ),

            "doi": safe_text(
                entry.find(
                    "arxiv:doi",
                    namespaces,
                )
            ),

            # 分类
            "primary_category": safe_attrib(
                entry.find(
                    "arxiv:primary_category",
                    namespaces,
                ),
                "term",
            ),

            "categories": categories,

            # 链接
            "links": links,

            # 常用快捷字段
            "pdf_url": pdf_url,
        }

        # ---------------------------------------------------
        # 12. 加入 feed
        # ---------------------------------------------------
        feed["entries"].append(entry_data)

    # ---------------------------------------------------
    # 13. 返回结果
    # ---------------------------------------------------
    return feed



@tool
def arxiv_search(topic: str) -> dict:
    """
    arXiv 搜索工具

    参数:
        topic:
            用户输入的论文主题

    返回:
        统一格式的字典

    成功:
        {
            "success": True,
            "entries": [...]
        }

    失败:
        {
            "success": False,
            "error": "错误信息"
        }

    功能:
    1. 调用 arXiv API 搜索论文
    2. 检查搜索是否成功
    3. 防止 KeyError
    4. 返回统一结构给 Agent
    """

    # -----------------------------------------
    # 1. 调用 arXiv 搜索函数
    # -----------------------------------------
    # search_arxiv_papers() 内部会:
    # - 清洗 query
    # - 发送 HTTP 请求
    # - retry/backoff
    # - 解析 XML
    # - 返回统一格式
    papers = search_arxiv_papers(topic)

    # -----------------------------------------
    # 2. 检查 API 是否调用成功
    # -----------------------------------------
    # 如果:
    # {
    #     "success": False,
    #     "error": "..."
    # }
    #
    # 则不继续处理
    if not papers["success"]:

        logger.error(
            f"Arxiv search failed: {papers['error']}"
        )

        # 直接返回错误
        # 不 raise exception
        # 防止整个 LangGraph workflow 崩掉
        return papers

    # -----------------------------------------
    # 3. 获取论文列表
    # -----------------------------------------
    # papers 结构:
    #
    # {
    #     "success": True,
    #     "data": {
    #         "entries": [...]
    #     }
    # }
    #
    # 使用 .get() 防止 KeyError
    entries = papers["data"].get("entries", [])

    # -----------------------------------------
    # 4. 打印日志
    # -----------------------------------------
    logger.info(
        f"Found {len(entries)} papers about {topic}"
    )

    # -----------------------------------------
    # 5. 返回统一格式
    # -----------------------------------------
    # Agent 后续节点只需要:
    #
    # result["entries"]
    #
    # 不需要关心底层 arXiv API 结构
    return {
        "success": True,

        # 论文列表
        "entries": entries
    }