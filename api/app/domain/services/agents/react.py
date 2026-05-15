import logging
from typing import AsyncGenerator

from app.domain.models.event import Event, StepEventStatus, StepEvent, ToolEvent, MessageEvent, ErrorEvent, \
    ToolEventStatus, WaitEvent
from app.domain.models.file import File
from app.domain.models.message import Message
from app.domain.models.plan import Step, Plan, ExecutionStatus
from app.domain.services.agents.base import BaseAgent
from app.domain.services.prompts.react import REACT_SYSTEM_PROMPT, EXECUTION_PROMPT
from app.domain.services.prompts.system import SYSTEM_PROMPT

logger = logging.getLogger()


class ReActAgent(BaseAgent):
    """基于 ReAct 架构的执行 Agent"""
    name: str = "react"
    _system_prompt = str = SYSTEM_PROMPT + REACT_SYSTEM_PROMPT
    _format: str = "json_object"  # format 控制的是 content、工具调用控制的是 tool_calls，两者不冲突

    async def execute_step(self, plan: Plan, step: Step, message: Message) -> AsyncGenerator[Event, None]:
        """根据传递的消息+规划+子步骤，执行响应的子步骤"""
        # 1. 根据传递的内容生成执行消息
        query = EXECUTION_PROMPT.format(
            messages=message.message,
            attachments="\n".join(message.attachments),
            language=plan.language,
            step=step.description,
        )

        # 2. 更新步骤的执行状态为运行中并返回 Step 事件
        step.status = ExecutionStatus.RUNNING
        yield StepEvent(step=step, status=StepEventStatus.STARTED)

        # 3. 调用 invoke 获取 agent 返回的事件内容
        async for event in self.invoke(query):
            # 4. 判断事件类型执行不同操作
            if isinstance(event, ToolEvent):
                # 5. 工具事件需要判断工具的名称是否为 message_ask_user
                if event.function_name == "message_ask_user":
                    if event.status == ToolEventStatus.CALLING:
                        # 6. 工具如果在调用中，我们需要返回一条消息告知用户需要让用户处理什么
                        yield MessageEvent(
                            role="assistant",
                            # todo: 由于 message_ask_user 工具还没实现，所以参数未定，暂时定为 text
                            message=event.function_args.get("text", "")
                        )
                    elif event.status == ToolEventStatus.CALLED:
                        # 7. 如果工具事件为已调用，则需要返回等待事件并中断程序
                        yield WaitEvent()
                        return
                    continue
            elif isinstance(event, MessageEvent):
                # 8. 返回消息事件，意味着 content 中有内容，content 有内容则代表 Agent 已运行完毕
                step.status = ExecutionStatus.COMPLETED

                # 9. message 中输出的数据结构为 json，需要提取并解析
                parsed_obj = await self._json_parser.invoke(event.message)
                new_step = Step.model_validate(parsed_obj)

                # 10. 更新子步骤的数据
                step.success = new_step.success
                step.result = new_step.result
                step.attachments = new_step.attachments

                # 11 返回步骤完成事件
                yield StepEvent(step=step, status=StepEventStatus.COMPLETED)

                # 12. 如果子步骤拿到了结果，还需要返回一段消息给用户（将结果返回给用户）
                if step.result:
                    yield MessageEvent(role="assistant", message=step.result)
                continue
            elif isinstance(event, ErrorEvent):
                # 13. 错误事件需要更新步骤的状态
                step.status = ExecutionStatus.FAILED
                step.error = event.error

                # 14. 返回子步骤对应事件
                yield StepEvent(step=step, status=StepEventStatus.FAILED)

            # 15. 其他场景将事件直接返回
            yield event

        # 16. 循环迭代完成后代表子步骤已实现，需要更新状态
        step.status = ExecutionStatus.COMPLETED

    async def summarize(self) -> AsyncGenerator[Event, None]:
        """调用 Agent 汇总历史的消息并生成最终回复+附件"""
        # 1. 构建请求 query
        query = SYSTEM_PROMPT

        # 2. 调用 invoke 方法获取 Agent 生成的事件
        async for event in self.invoke(query):
            # 3. 判断事件类型是否为消息事件，如果是则表示 Agent 结构化生成汇总内容
            if isinstance(event, MessageEvent):
                # 4. 记录日志并解析输出内容
                logger.info(f"执行 Agent 生成汇总内容：{event.message}")
                parsed_obj = await self._json_parser.invoke(event.message)

                # 5. 将解析数据转换为 Message 对象
                message = Message.model_validate(parsed_obj)

                # 6. 提取消息中的附件信息
                attachments = [File(filepath=filepath) for filepath in message.attachments]

                # 7. 返回消息事件并将消息+附件进行响应
                yield MessageEvent(
                    role="assistant",
                    message=message.message,
                    attachments=attachments
                )
            else:
                # 8. 其他事件直接返回
                yield event
