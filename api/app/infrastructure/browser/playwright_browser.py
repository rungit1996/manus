import asyncio
import logging
from typing import Optional, List, Any

from markdownify import markdownify
from playwright.async_api import Playwright, Page, Browser, async_playwright

from app.domain.external.browser import Browser as BrowserProtocol
from app.domain.external.llm import LLM
from app.domain.models.tool_result import ToolResult
from app.infrastructure.browser.playwright_browser_fun import GET_VISIBLE_CONTENT_FUNC, GET_INTERACTIVE_ELEMENTS_FUNC

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

    async def _ensure_browser(self) -> None:
        """确保浏览器存在，如果不存在则初始化"""
        if not self.browser or not self.page:
            if not await self.initialize():
                raise Exception("初始化 Playwright 浏览器失败")

    async def _ensure_page(self) -> None:
        """确保浏览器页面存在，如果不存在则新建"""
        # 1. 先保证浏览器存在
        await self._ensure_browser()

        # 2. 如果页面不存在则创建新的上下文+页面
        if not self.page:
            self.page = await self.browser.new_page()  # 等同于 self.browser.new_context().new_page()
        else:
            # 3. 如果页面存在则同步切换到浏览器最新打开的标签页，先提取所有上下文
            contexts = self.browser.contexts
            if contexts:
                # 4. 获取默认上下文和页面
                default_context = contexts[0]
                pages = default_context.pages

                # 5. 判断页面是否存在
                if pages:
                    # 6. 获取当前最新页面（chrome浏览器新增页面时，会默认往右侧添加，相当于 pages 序号较大的页面）
                    latest_page = pages[-1]

                    # 7. 判断当前页面是否为最新页面，如果不是则切换绑定为最新标签页
                    if self.page != latest_page:
                        self.page = latest_page

    async def _extract_content(self) -> str:
        """提取当前页面内容"""
        # 1. 使用 js 代码获取当前页面可视元素内容
        visible_content = await self.page.evaluate(GET_VISIBLE_CONTENT_FUNC)

        # 2. 使用 markdownify 这个库将 html 文档转换为 markdown
        markdown_content = markdownify(visible_content)

        # 3. 模型上下文长度有限，提取最大不超过 50k 个字符
        max_content_length = min(len(markdown_content), 50000)

        # 4. 判断是否传递了 llm，如果传递了，还可以使用 llm 对 markdown_content 进行整理
        if self.llm:
            # 5. 调用 llm 对 markdown_content 内容进行二次整理
            response = await self.llm.invoke([
                {
                    "role": "system",
                    "content": "您是一名专业的网页信息提取助手，请从当前页面内容中提取所有信息并将其转换为 markdown 格式",
                },
                {
                    "role": "user",
                    "content": markdown_content[:max_content_length],
                },
            ])
            return response.get("content", "")
        else:
            return markdown_content[:max_content_length]

    async def _extract_interactive_elements(self) -> List[str]:
        """提取当前页面上的可交互元素"""
        # 1. 确保页面存在
        await self._ensure_page()

        # 2. 清除当前页面上的缓存可交互元素列表
        self.page.interactive_element_cache = []

        # 3. 执行 js 脚本获取可交互元素列表
        interactive_elements = await self.page.evaluate(GET_INTERACTIVE_ELEMENTS_FUNC)

        # 4. 更新缓存的可交互元素列表
        self.page.interactive_element_cache = interactive_elements

        # 5. 格式化可交互元素为字符串
        formatted_elements = []
        for element in interactive_elements:
            formatted_elements.append(f"{element['index']}:<{element['tag']}>{element['text']}</{element['tag']}>")

        return formatted_elements

    async def _get_element_by_id(self, index: int) -> Optional[Any]:
        """根据传递的索引/ID获取对应的元素"""
        # 1. 判断当前页面是否存在可交互元素
        if (
                not hasattr(self.page, "interactive_element_cache") or
                not self.page.interactive_element_cache or
                index >= len(self.page.interactive_element_cache)
        ):
            return None

        # 2. 构建选择器
        selector = f'[data-manus-id="manus-element-{index}"]'
        return await self.page.query_selector(selector)

    async def click(
            self,
            index: Optional[int] = None,
            coordinate_x: Optional[float] = None,
            coordinate_y: Optional[float] = None,
    ) -> ToolResult:
        """根据传递的索引位置+xy坐标实现点击"""
        # 1. 确保页面存在
        await self._ensure_page()

        # 2. 判断传递的是 xy 坐标还是 index
        if coordinate_x is not None and coordinate_y is not None:
            await self.page.mouse.click(coordinate_x, coordinate_y)
        elif index is not None:
            try:
                # 3. 根据 index 获取元素
                element = await self._get_element_by_id(index)
                if not element:
                    return ToolResult(success=False, message=f"使用索引{index}未找到对应元素")

                # 4. 检查元素是否是可见的
                is_visible = await self.page.evaluate("""(element) => {
                    if (!element) return false;
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    return !(
                        rect.width === 0 ||
                        rect.height === 0 ||
                        style.display === 'none' ||
                        style.visibility === 'hidden' ||
                        style.opacity === '0'
                    );
                }""", element)

                # 5. 如果元素不可见，则执行以下代码
                if not is_visible:
                    # 6. 尝试将页面滚动到该元素的位置
                    await self.page.evaluate("""(element) => {
                        if (element) {
                            element.scrollIntoView({behavior: 'smooth', block: 'center'})
                        }
                    }""", element)
                    await asyncio.sleep(1)

                # 7. 点击元素
                await element.click(timeout=5000)

            except Exception as e:
                return ToolResult(success=False, message=f"点击元素出错：{str(e)}")

        return ToolResult(success=True)

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

    async def wait_for_page_load(self, timeout: int = 15) -> bool:
        """传递超时时间，等待当前页面是否加载完毕"""
        # 1. 确保当前页面存在
        await self._ensure_page()

        # 2. 使用异步任务事件循环的时间来作为开始时间（只和异步任务相关）
        start_time = asyncio.get_event_loop().time()
        check_interval = 5

        # 3. 循环检测网页是否加载成功
        while asyncio.get_event_loop().time() - start_time < timeout:
            # 4. 使用 js 代码判断网页是否加载成功
            is_completed = await self.page.evaluate("""() => document.readyState === 'complete'""")
            if is_completed:
                return True

            # 5. 未加载成功则休眠对应时间
            await asyncio.sleep(check_interval)

        return False

    async def navigate(self, url: str) -> ToolResult:
        """根据传递的 url 跳转到指定页面"""
        # 1. 确保页面存在
        await self._ensure_page()

        try:
            # 2. 在跳转之前先将可交互元素的缓存清空
            self.page.interactive_element_cache = []

            # 3. 使用 goto 进行跳转
            await self.page.goto(url)

            return ToolResult(
                success=True,
                data={"interactive_elements": await self._extract_interactive_elements()}
            )
        except Exception as e:
            # 返回错误的工具结果
            return ToolResult(success=False, message=f"浏览器导航到[{url}]失败：{str(e)}")

    async def view_page(self) -> ToolResult:
        """获取当前网页的内容（内容+可交互元素）"""
        # 1. 确保页面存在
        await self._ensure_page()

        # 2. 等待页面加载完成
        await self.wait_for_page_load()

        # 3. 更新页面的可交互元素
        interactive_elements = await self._extract_interactive_elements()

        # 4. 返回工具结果
        return ToolResult(
            success=True,
            data={
                "content": await self._extract_content(),
                "interactive_elements": interactive_elements,
            }
        )

    async def restart(self, url: str) -> ToolResult:
        """重启并跳转到指定 url"""
        await self.cleanup()
        return await self.navigate(url)

    async def scroll_up(self, to_top: Optional[bool] = None) -> ToolResult:
        """向上滚动浏览器一页或一屏或整个页面"""
        # 1. 确保页面存在
        await self._ensure_page()

        # 2. 判断是否滚到最顶部
        if to_top:
            await self.page.evaluate("window.scrollTo(0, 0)")
        else:
            await self.page.evaluate("window.scrollBy(0, -window.innerHeight)")

        return ToolResult(success=True)

    async def scroll_down(self, to_down: Optional[bool] = None) -> ToolResult:
        """向下滚动浏览器一页或一屏幕或整个页面"""
        # 1. 确保页面存在
        await self._ensure_page()

        # 2. 判断是否滚到最底部
        if to_down:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        else:
            await self.page.evaluate("window.scrollBy(0, window.innerHeight)")

        return ToolResult(success=True)

    async def screenshot(self, full_page: Optional[bool] = None) -> bytes:
        """传递 full_page 完成网页截图"""
        # 1. 确保页面存在
        await self._ensure_page()

        # 2. 创建一个截图配置
        screenshot_options = {
            "full_page": full_page,
            "type": "png"
        }

        return await self.page.screenshot(**screenshot_options)

    async def console_exec(self, javascript: str) -> ToolResult:
        """传递 js 代码在当前页面控制台执行"""
        await self._ensure_page()
        result = await self.page.evaluate(javascript)
        return ToolResult(success=True, data={"result": result})

    async def console_view(self, max_lines: Optional[int] = None) -> ToolResult:
        """根据传递的行数查看控制台日志"""
        # 1. 确保页面存在
        await self._ensure_page()

        # 2. 可以指定另外一段 js 代码查看控制台的内容
        logs = await self.page.evaluate("""() => {
            return window.console.logs || [];
        }""")

        if max_lines is not None:
            logs = logs[-max_lines:]

        return ToolResult(success=True, data={"logs": logs})
