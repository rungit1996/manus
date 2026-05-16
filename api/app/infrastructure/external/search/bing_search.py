import logging
import re
import time
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.domain.external.search import SearchEngine
from app.domain.models.search import SearchResult, SearchResultItem
from app.domain.models.tool_result import ToolResult

logger = logging.getLogger()


class BingSearchEngine(SearchEngine):
    """bing 搜索引擎"""

    def __init__(self) -> None:
        """构造函数，初始化 bing 搜索引擎的相关信息"""
        self.base_url = "https://www.bing.com/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "upgrade-insecure-requests": "1",
        }
        self.cookies = httpx.Cookies()

    async def invoke(self, query: str, date_range: Optional[str] = None) -> ToolResult[SearchResult]:
        """根据传递的 query+date_range 调用 bing 搜索获取搜索内容"""
        # 1. 构建请求参数
        params = {"q": query}

        # 2. 判断 date_range 是否存在并提取真实数据
        if date_range and date_range != "all":
            # 3. 获取当前日期距离 1970-01-01 的天数
            days_since_epoch = int(time.time() / (60 * 60 * 24))

            # 4. 创建日期检索数据类型映射
            date_mapping = {
                "past_hour": "ex1%3a\"ez1\"",  # ex1:"ez1"
                "past_day": "ex1%3a\"ez1\"",
                "past_week": "ex1%3a\"ez2\"",
                "past_month": "ex1%3a\"ez3\"",
                "past_year": f"ex1%3a\"ez5_{days_since_epoch - 365}_{days_since_epoch}\"",
            }

            # 5. 判断是否传递了 date_range 并在 date_mapping 中可以查找到
            if date_range in date_mapping:
                params["filters"] = date_mapping[date_range]

        try:
            # 6. 使用 httpx 创建一个异步客户端上下文
            async with httpx.AsyncClient(
                    headers=self.headers,
                    cookies=self.cookies,
                    timeout=60,
                    follow_redirects=True,
            ) as client:
                # 7. 调用客户端发起请求
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()

                # print(f"返回结果的前2000: {response.text[:2000]}")
                # logger.info(f"返回结果的前2000: {response.text[:2000]}")

                # 8. 更新 Cookie 信息
                self.cookies.update(response.cookies)

                # 9. 使用 bs4 解析 html 内容
                soup = BeautifulSoup(response.text, "html.parser")

                # 10. 定义搜索结果并解析 li.b_algo 对应的 dom 元素
                search_results = []
                result_items = soup.find_all("li", class_="b_algo")

                # 11. 循环遍历所有匹配的元素
                for item in result_items:
                    try:
                        # 12. 定义变量存储标题和 url 链接
                        title, url = ("", "")

                        # 13. 解析搜索结果中的 h2 并提取 title 和 url
                        title_tag = item.find("h2")
                        if title_tag:
                            a_tag = title_tag.find("a")
                            if a_tag:
                                title = a_tag.get_text(strip=True)
                                url = a_tag.get("href", "")

                        # 14. 判断标题是否存在，如果不存在则提取 dom 下的 a 标签中的 href 和 text 作为标题和链接
                        if not title:
                            a_tags = item.find_all("a")
                            for a_tag in a_tags:
                                # 15. 提取标签中的文本并判断长度是否大于10
                                text = a_tag.get_text(strip=True)
                                if len(text) > 10 and not text.startswith("http"):
                                    title = text
                                    url = a_tag.get("href", "")
                                    break
                        # 16. 如果上面两种方式还是没有标题则舍弃此条目
                        if not title:
                            continue

                        # 17. 提取检索条目的摘要信息
                        snippet = ""
                        snippet_items = item.find_all(
                            ["p", "div"],
                            class_=re.compile(r'b_lineclamp|b_descript|b_caption')
                        )
                        if snippet_items:
                            snippet = snippet_items[0].get_text(strip=True)

                            # 去掉 1 day ago / 1 hour ago 这类时间前缀
                            snippet = re.sub(r'^\w+ \w+ ago[\u2000-\u200f·\s]+', '', snippet)
                            # 去掉所有 \u2002 这类特殊空白字符
                            snippet = re.sub(r'[\u2000-\u200f]', ' ', snippet).strip()

                        # 18. 如果这个情况还找不到摘要，则查询所有的 p 标签，同时获取文本内容，并判断内容长度是否大于 20
                        if not snippet:
                            p_tags = item.find_all("p")
                            for p in p_tags:
                                text = p.get_text(strip=True)
                                if len(text) > 20:
                                    snippet = text
                                    break

                        # 19. 如果还找不到摘要信息，可以提取元素下所有文本，并使用常见的分割符进行分割
                        if not snippet:
                            all_text = item.get_text(strip=True)

                            # 20. 将所有文本按常见的句子结尾标识进行拆分
                            sentences = re.split(r'[.!?\n。！]', all_text)
                            for sentence in sentences:
                                clean_sentence = sentence.strip()
                                if len(clean_sentence) > 20 and clean_sentence != title:
                                    snippet = clean_sentence

                        # 21. 补全相对路径的 url 链接或者是缺失的协议
                        if url and not url.startswith("http"):
                            if url.startswith("//"):
                                url = "https:" + url
                            elif url.startswith("/"):
                                url = "https://www.bing.com" + url

                        # 22. 如果标题和链接都存在则添加数据
                        search_results.append(SearchResultItem(
                            url=url,
                            title=title,
                            snippet=snippet,
                        ))

                    except Exception as e:
                        # 23. 记录单条搜索信息出错同时跳过该条数据
                        logger.warning(f"Bing 搜索结果解析失败：{str(e)}")
                        continue

                # 24. 提取整个页面的内容并查找 `results` 对应的文本，即搜索的条目数
                total_results = 0
                result_stats = soup.find_all(string=re.compile(r"\d+[,\d+]\s*results"))
                if result_stats:
                    for stat in result_stats:
                        # 25. 匹配出对应的数字分组
                        match = re.search(r"([\d,]+)\s*results", stat)
                        if match:
                            try:
                                # 26. 取出匹配的分组内容，去除逗号后转换为整型
                                total_results = int(match.group(1).replace(",", ""))
                                break
                            except Exception:
                                continue

                # 27. 如果使用正则匹配找不到 results，可能是页面不一致导致的，则使用新逻辑
                if total_results == 0:
                    # 28. 使用类元素查找器
                    count_elements = soup.find_all(
                        ["span", "p", "div"],
                        class_=re.compile(r"sb_count|b_focusTextMedium")
                    )
                    for element in count_elements:
                        # 29. 提取 dom 的文本并获取数字
                        text = element.get_text(strip=True)
                        match = re.search(r"([\d,]+)\s*results", text)
                        if match:
                            try:
                                total_results = int(match.group(1).replace(',', ''))
                                break
                            except Exception:
                                continue

                # 30. 已经有对应结果则直接返回 ToolResult
                results = SearchResult(
                    query=query,
                    date_range=date_range,
                    total_results=total_results,
                    results=search_results,
                )

                return ToolResult(success=True, data=results)
        except Exception as e:
            # 31. 记录异常日志信息
            logger.error(f"bing 搜索出错：{str(e)}")
            error_results = SearchResult(
                query=query,
                date_range=date_range,
                total_results=0,
                results=[],
            )
            return ToolResult(
                success=False,
                message=f"bing 搜索出错：{str(e)}",
                data=error_results,
            )


if __name__ == "__main__":
    import asyncio


    async def demo():
        search_engine = BingSearchEngine()
        result = await search_engine.invoke("特朗普访华", "past_day")

        print(result)
        for item in result.data.results:
            print(item)


    asyncio.run(demo())
