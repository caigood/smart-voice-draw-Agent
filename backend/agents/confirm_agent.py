"""
ConfirmAgent - 用户反馈理解智能体
使用 CrewAI 处理用户对提示词的确认、修改或拒绝反馈
"""

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from crewai import Agent, Task, LLM
import asyncio
import json


class ConfirmAgent:
    """用户反馈理解智能体 - CrewAI 实现"""

    def __init__(self):
        self.llm = LLM(
            model=f"openai/{LLM_MODEL}",
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            temperature=0.5
        )
        self.agent = Agent(
            role="用户反馈理解专家",
            goal="判断用户对待确认提示词的确认、修改或拒绝意图，并生成下一步结果",
            backstory=(
                "你擅长理解语音交互中的真实意图。用户可能只表达确认，也可能在确认的同时"
                "继续补充新增元素、修改风格、指定名称或删除内容。如果一句话同时包含确认词和修改要求，"
                "你必须优先判定为修改提示词，而不是直接确认生成。"
            ),
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )

    async def resolve_feedback(self, user_text: str, pending_prompt: str, context: str = "") -> dict:
        """处理用户对提示词的确认反馈。"""
        task = Task(
            description=f"""
用户反馈：{user_text}

当前待确认提示词：{pending_prompt}

上下文信息：{context}

请判断用户意图：
1. confirm：用户明确同意直接生成，没有新增或修改要求
2. revise：用户提出新增、删除、替换、改风格、改名字等修改要求
3. reject：用户拒绝当前提示词，要求重新来或暂不生成

重要规则：
- 当前阶段是“图片尚未生成前的提示词确认阶段”，用户说的修改都应该作用到 pending_prompt 上
- 你必须基于用户完整语义判断，而不是只看是否出现确认词
- 如果用户明确表达“直接生成 / 可以生成 / 就用这个 / 没问题”，且没有新增、删除、替换、改颜色、改风格、改主体等要求，返回 confirm
- 如果用户要求把原提示词中的某个元素、颜色、风格、主体、背景或文字信息改成另一种，返回 revise
- 如果用户同时表达确认和修改，优先返回 revise
- revise 时必须把当前提示词和用户修改要求融合成完整 new_prompt，不要只把用户原话追加到末尾
- confirm 时 should_generate 为 true
- revise / reject 时 should_generate 为 false

只返回合法 JSON，不要 Markdown，不要代码块：
{{
  "confirm_intent": "confirm/revise/reject",
  "should_generate": true,
  "new_prompt": "确认时为原提示词，修改时为合并后的新提示词，拒绝时为空",
  "agent_reply": "中文智能体回复"
}}
""",
            expected_output="只包含合法 JSON 的用户反馈处理结果",
            agent=self.agent
        )

        try:
            result = await asyncio.to_thread(task.execute_sync)
            content = str(result).strip()
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
        except Exception as e:
            print(f"ConfirmAgent error: {e}")

        return {
            "confirm_intent": "revise",
            "should_generate": False,
            "new_prompt": f"{pending_prompt}，{user_text}",
            "agent_reply": "我已根据你的反馈更新提示词。"
        }
