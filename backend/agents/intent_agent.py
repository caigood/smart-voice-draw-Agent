"""
IntentAgent - 意图识别智能体
使用 CrewAI 判断用户语音指令的意图类型
"""

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from crewai import Agent, Task, LLM
import asyncio
import json


class IntentAgent:
    """意图识别智能体 - CrewAI 实现"""

    def __init__(self):
        self.llm = LLM(
            model=f"openai/{LLM_MODEL}",
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            temperature=0.3
        )
        self.agent = Agent(
            role="语音绘图意图识别专家",
            goal="准确判断用户的语音指令属于哪种绘图操作意图",
            backstory=(
                "你是语音绘图系统中的意图识别智能体。用户会用中文语音描述绘图需求，"
                "你需要判断用户是想创建新图、修改当前图、重新生成、回退版本、清空画布、"
                "回答系统反问，还是无法识别。你的输出必须稳定、简洁，并且只能返回合法 JSON。"
            ),
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )

    async def recognize(
        self,
        user_text: str,
        current_prompt: str = "",
        pending_question: str = "",
        history_summary: str = ""
    ) -> dict:
        """识别用户语音指令意图。"""
        task = Task(
            description=f"""
用户语音文本：{user_text}
当前已有图片提示词：{current_prompt or '无'}
当前待澄清问题：{pending_question or '无'}
最近历史操作：{history_summary or '无'}

请判断用户意图：
- create_image：用户想创建一张全新的图片
- edit_image：用户想在当前已有图片基础上修改，例如换背景、加元素、改风格、改颜色、保留主体等
- regenerate：用户想用当前提示词重新生成一张
- undo：用户想回退到上一版本
- clear：用户想清空画布重新开始
- clarify_answer：用户正在回答系统之前的反问
- unknown：无法识别意图

关键规则：
1. 如果当前已有图片，且用户说的是修改类指令，例如“把/改成/换成/加/去掉/调整/变/背景/风格/颜色”，优先判定为 edit_image。
2. edit_image 只用于意图识别，prompt 必须为空字符串，不要扩写或美化用户的编辑指令。
3. 如果用户说要画、生成、创作一个全新主题，判定为 create_image。
4. 如果用户描述过短或主体不明确，可以设置 needClarification=true，并提出一个简短澄清问题。
5. 所有文本字段必须使用中文。
6. 只返回合法 JSON，不要 Markdown，不要代码块。

输出格式：
{{
  "intent": "create_image/edit_image/regenerate/undo/clear/clarify_answer/unknown",
  "needClarification": true/false,
  "clarificationQuestion": "反问问题（如果有）",
  "agentReply": "中文智能体回复",
  "prompt": "create_image 时的初步绘图提示词，edit_image 时为空",
  "negativePrompt": "负面提示词",
  "operations": ["操作步骤1", "操作步骤2"]
}}
""",
            expected_output="只包含合法 JSON 的意图识别结果",
            agent=self.agent
        )

        try:
            result = await asyncio.to_thread(task.execute_sync)
            content = str(result).strip()
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                parsed = json.loads(content[start:end])
                return self._normalize_result(parsed)
        except Exception as e:
            print(f"IntentAgent error: {e}")

        return {
            "intent": "unknown",
            "needClarification": False,
            "clarificationQuestion": "",
            "agentReply": "我没有理解这个指令，请换一种说法。",
            "prompt": "",
            "negativePrompt": "",
            "operations": ["意图识别失败"]
        }

    def _normalize_result(self, result: dict) -> dict:
        """统一意图字段和编辑指令输出。"""
        if result.get("intent") == "modify_image":
            result["intent"] = "edit_image"
        if result.get("intent") == "edit_image":
            result["prompt"] = ""
            result["negativePrompt"] = ""
        result.setdefault("needClarification", False)
        result.setdefault("clarificationQuestion", "")
        result.setdefault("agentReply", "我已理解你的指令。")
        result.setdefault("prompt", "")
        result.setdefault("negativePrompt", "")
        result.setdefault("operations", [])
        return result
