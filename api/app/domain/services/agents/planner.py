import logging
from typing import Optional, AsyncGenerator

from .base import BaseAgent
from ..prompts.planner import PLANNER_SYSTEM_PROMPT, CREATE_PLAN_PROMPT, UPDATE_PLAN_PROMPT
from ..prompts.system import SYSTEM_PROMPT
from ...models.event import Event, MessageEvent, PlanEvent, PlanEventStatus
from ...models.message import Message
from ...models.plan import Plan, Step

"""
多 Agent 系统/flow = PlannerAgent + ReActAgent

顺序：
1. PlannerAgent 生成规划；
2. 循环取出规划中的子步骤，让 ReActAgent 执行，依次迭代；
3. ReActAgent 执行完每一个子步骤之后，需要将子步骤结果 + Plan 传递给 PlannerAgent 让其更新计划/Plan；
4. 循环取出规划中的子步骤，让 ReActAgent 执行，依次迭代；
5. ...
6. 直到所有子任务/步骤都完成。这时候将子步骤的所有结果汇总进行总结（ReActAgent）

PlannerAgent:
- 功能：将用户的需求拆解成多个子任务+根据已完成的子任务更新规划
- 提示词：创建规划的 prompt、更新规划的 prompt

ReActAgent：
- 功能：迭代执行完每一个子任务、汇总所有的子任务
- 提示词：执行任务的 prompt、汇总总结 prompt
"""

logger = logging.getLogger()


class PlannerAgent(BaseAgent):
    """规划 Agent，用于将用户的任务/需求拆解成多个子步骤"""
    name: str = "planner"
    _system_prompt: str = SYSTEM_PROMPT + PLANNER_SYSTEM_PROMPT
    _format: Optional[str] = "json_object"
    _tool_choice: Optional[str] = ""

    async def create_plan(self, message: Message) -> AsyncGenerator[Event, None]:
        """根据用户传递的消息创建计划/规划，迭代返回对应的事件"""
        # 1. 根据用户传递的消息生成创建 plan 的提示词
        query = CREATE_PLAN_PROMPT.format(
            message=message.message,
            attachments="\n".join(message.attachments),
        )

        # 2. 调用 invoke 函数返回迭代事件
        async for event in self.invoke(query):
            # 3. 规划智能体因为使用 json_object，正常情况下会返回 MessageEvent
            if isinstance(event, MessageEvent):
                # 4. 记录日志并使用 json 解析器得到对应的数据
                logger.info(f"PlannerAgent 生成消息：{event.message}")
                parsed_obj = await self._json_parser.invoke(event.message)

                # 5. 将解析对象转换成 Plan 计划
                plan = Plan.model_validate(parsed_obj)

                # 6. 返回 PlanEvent 表示规划创建成功
                yield PlanEvent(plan=plan, status=PlanEventStatus.CREATED)
            else:
                # 返回不是消息事件
                yield event

    async def update_plan(self, plan: Plan, step: Step) -> AsyncGenerator[Event, None]:
        """根据传递的原始规划 + 子步骤更新事件"""
        # 1. 使用 plan+step 创建更新 Plan 提示词
        query = UPDATE_PLAN_PROMPT.format(
            plan=plan.model_dump_json(),
            step=step.model_dump_json(),
        )

        # 2. 调用 invoke 获取对应的事件
        async for event in self.invoke(query):
            # 3. 判断规划 Agent 生成的事件不是消息事件
            if isinstance(event, MessageEvent):
                # 4. 记录日志并解析 json
                logger.info(f"PlannerAgent 生成消息：{event.message}")
                parsed_obj = await self._json_parser.invoke(event.message)

                # 5. 将解析对象转换成 Plan
                updated_plan = Plan.model_validate(parsed_obj)

                # 6. 拷贝更新计划中的 steps，避免造成数据污染
                new_steps = [Step.model_validate(step) for step in updated_plan.steps]

                # 7. 查询旧计划中第一个未完成的计划
                first_pending_index = None
                for idx, step in enumerate(Plan.steps):
                    if not step.done:
                        first_pending_index = idx
                        break

                # 8. 判断是否有未完成的步骤
                if first_pending_index is not None:
                    # 9. 获取历史已完成的子步骤并更新
                    updated_steps = plan.steps[:first_pending_index]
                    updated_steps.extend(new_steps)

                    # 10. 更新 plan 规划
                    plan.steps = updated_steps

                # 11. 返回规划更新事件
                yield PlanEvent(plan=plan, status=PlanEventStatus.UPDATED)
            else:
                # 其他事件则直接返回
                yield event
