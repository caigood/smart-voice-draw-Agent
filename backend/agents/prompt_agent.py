"""
PromptAgent - 提示词优化智能体
使用 CrewAI 将用户的自然语言绘图需求转化为高质量绘图提示词
"""

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from crewai import Agent, Task, LLM
import asyncio
import json


class PromptAgent:
    """提示词优化智能体 - CrewAI 实现"""

    def __init__(self):
        self.llm = LLM(
            model=f"openai/{LLM_MODEL}",
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            temperature=0.7
        )
        self.agent = Agent(
            role="绘图提示词优化专家",
            goal="将用户的自然语言绘图需求转化为适合图像生成模型的高质量中文提示词",
            backstory=(
                "你是一位专业的 AI 绘图提示词工程师，精通主体刻画、场景设计、"
                "构图、色彩、风格和画面氛围。你会把用户的口语化需求整理成清晰、"
                "完整、适合图像生成模型理解的中文提示词。"
            ),
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )

    async def optimize_prompt(self, user_text: str, context: str = "") -> dict:
        """优化用户绘图需求。"""
        task = Task(
            description=f"""
用户绘图需求：{user_text}

上下文信息：{context}

请完成：
1. 提取主题、场景、风格、色彩、构图、氛围等要素
2. 生成一段中文高质量绘图提示词
3. 生成中文负面提示词
4. 给出简短中文智能体回复

只返回合法 JSON，不要 Markdown，不要代码块：
{{
  "prompt": "优化后的中文绘图提示词",
  "negative_prompt": "中文负面提示词",
  "agent_reply": "中文智能体回复",
  "operations": ["操作步骤1", "操作步骤2"]
}}
""",
            expected_output="只包含合法 JSON 的提示词优化结果",
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
            print(f"PromptAgent error: {e}")

        return {
            "prompt": f"{user_text}，高质量，细节丰富，构图完整，色彩和谐",
            "negative_prompt": "低清晰度，模糊，变形，文字水印，多余肢体",
            "agent_reply": "好的，我已为你优化绘图提示词。",
            "operations": ["CrewAI 优化失败", "使用兜底提示词"]
        }