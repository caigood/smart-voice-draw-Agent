from typing import List, Optional
from agents import IntentAgent, PromptAgent, ConfirmAgent


class VoiceDrawOrchestrator:
    """语音绘图流程编排器，负责调度各个 CrewAI 智能体。"""

    def __init__(self):
        self.intent_agent = IntentAgent()
        self.prompt_agent = PromptAgent()
        self.confirm_agent = ConfirmAgent()

    async def parse(
        self,
        text: str,
        current_prompt: str = "",
        pending_question: Optional[str] = None,
        history: List[dict] = None
    ) -> dict:
        """解析用户输入并生成结构化响应。"""
        try:
            history_summary = self._summarize_history(history)
            result = await self.intent_agent.recognize(
                user_text=text,
                current_prompt=current_prompt,
                pending_question=pending_question or "",
                history_summary=history_summary
            )

            if result.get("intent") == "edit_image":
                result["prompt"] = ""
                result["negativePrompt"] = ""
                result["agentReply"] = f"好的，我会严格按照你的指令编辑当前图片：{text}"
                result["operations"] = ["IntentAgent 识别为图片编辑", "使用用户原始指令", "不扩写编辑提示词"]
                return result

            if result.get("intent") == "create_image" and result.get("prompt"):
                prompt_result = await self.prompt_agent.optimize_prompt(
                    user_text=text,
                    context=f"当前图片 Prompt：{current_prompt}\n历史操作摘要：{history_summary}"
                )
                result["prompt"] = prompt_result.get("prompt", result.get("prompt", ""))
                result["negativePrompt"] = prompt_result.get("negative_prompt", result.get("negativePrompt", ""))
                result["agentReply"] = prompt_result.get("agent_reply", result.get("agentReply", ""))
                result["operations"] = prompt_result.get("operations", result.get("operations", []))

            return result

        except Exception as e:
            raise Exception(f"IntentAgent 调用失败: {str(e)}")

    async def confirm(
        self,
        text: str,
        pending_prompt: str,
        context: str = ""
    ) -> dict:
        """处理用户对提示词的确认反馈。"""
        try:
            return await self.confirm_agent.resolve_feedback(
                user_text=text,
                pending_prompt=pending_prompt,
                context=context
            )
        except Exception as e:
            raise Exception(f"ConfirmAgent 调用失败: {str(e)}")

    def _summarize_history(self, history: List[dict]) -> str:
        """总结历史记录。"""
        if not history:
            return "无历史记录"
        summaries = [f"{i + 1}. {item.get('userText', '')}" for i, item in enumerate(history[-3:])]
        return "\n".join(summaries)
