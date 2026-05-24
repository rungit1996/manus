import asyncio
import logging
from typing import Optional

from playwright.async_api import Playwright, Page, Browser, async_playwright

from app.domain.external.browser import Browser as BrowserProtocol
from app.domain.external.llm import LLM

logger = logging.getLogger(__name__)


class PlaywrightBrowser(BrowserProtocol):
    """基础 Playwright 管理的浏览器扩展"""

    def __init__(
            self,
            cdp_url: str,  # CDP 连接地址
            llm: Optional[LLM],  # 可选参数，传递 LLM，如果传递了则会使用 LLM 对页面内容进行整理变成 markdown 格式
    ) -> None:
        """构造函数，完成 Playwright 浏览器的初始化"""
        # LLM 相关
        self.llm: Optional[LLM] = llm

        # 浏览器相关
        self.cdp_url: str = cdp_url
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def initialize(self) -> bool:
        """初始化并确保资源是可用的"""
        # 1. 定义重试次数+重试延迟确保资源存在
        max_retries = 5
        retry_interval = 1

        # 2. 循环开始资源构建
        for attempt in range(max_retries):
            try:
                # 3. 创建 playwright 上下文
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)

                # 4. 获取浏览器的所有上下文
                contexts = self.browser.contexts

                # 5. 如果上下文存在，并且第一个上下文只有一个页面则执行如下逻辑
                if contexts and (len(contexts[0].pages) == 1):
                    # 6. 获取当前上下文的第一个页面
                    page = contexts[0].pages[0]

                    # 7. 判断当前页面是不是空页面，如果是则直接使用 page，否则新建一个
                    if (
                            page.url == "about:blank" or
                            page.url == "chrome://newtab/" or
                            page.url == "chrome://new-tab-page/" or
                            not page.url
                    ):
                        self.page = page
                    else:
                        # 8. 当前页面已经有数据则新建一个页面
                        self.page = await contexts[0].new_page()

                else:
                    # 9. 上下文不存在或者页面不唯一则表示数据被污染，新建一个页面
                    context = contexts[0] if contexts else await self.browser.new_context()
                    self.page = await context.new_page()
                return True
            except Exception as e:
                # 10. 清除所有资源
                await self.cleanup()

                # 11. 判断重试次数是否等于最大重试次数
                if attempt == max_retries - 1:
                    logger.error(f"初始化 Playwright 浏览器失败（已重试 {max_retries} 次）：{str(e)}")
                    return False
                # 12. 使用指数级增长进行休眠，最大休眠时间为 10 秒
                retry_interval = min(retry_interval * 2, 10)
                logger.warning(f"初始化 Playwright 浏览器失败，即将进行第 {attempt + 1} 次重试：{str(e)}")
                await asyncio.sleep(retry_interval)

    async def cleanup(self) -> None:
        """清除 Playwright 资源"""
        try:
            # 1. 检测浏览器是否存在，如果存在则删除该浏览器下的所有 tabs 页面
            if self.browser:
                # 2. 获取该浏览器的所有上下文
                contexts = self.browser.contexts
                if contexts:
                    # 3. 循环遍历所有上下文逐个处理
                    for context in contexts:
                        # 4. 获取每个上下文的所有页面
                        pages = context.pages
                        for page in pages:
                            # 5. 循环遍历清除所有页面
                            if not page.is_closed():
                                await page.close()

            # 6. 判读 self.page 是否关闭
            if self.page and not self.page.is_closed():
                await self.page.close()

            # 7. 关闭浏览器
            if self.browser:
                await self.browser.close()

                # 8. 停止 playwright:
                if self.playwright:
                    await self.playwright.stop()
        except Exception as e:
            # 9. 记录错误日志
            logger.error(f"清除 Playwright 浏览器资源出错：{str(e)}")
        finally:
            # 10. 重置所有资源
            self.page = None
            self.browser = None
            self.playwright = None
