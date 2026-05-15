# 规划 Agent 系统预设 prompt
PLANNER_SYSTEM_PROMPT = ""

# 创建 Plan 规划提示词模板，内部有 message + attachments 占位符
CREATE_PLANNER_PROMPT = "{message}\n{attachments}"

# 更新 Plan 规划提示词模版，内部有 plan 和 step 占位符
UPDATE_PLANNER_PROMPT = "{plan}\n{step}"
